"""Independent portal-state monitor; no changes to installed task triggers."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
from http.cookiejar import CookieJar

if not getattr(sys, 'frozen', False):
    root = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(root / 'src'), str(Path(__file__).resolve().parents[1] / 'login-diagnostics')]
import record_login as diag
login = diag.login


def origin(url):
    parsed = urlparse(url)
    return parsed.scheme, parsed.hostname, parsed.port or (80 if parsed.scheme == 'http' else 443)


def route(url):
    try:
        same_origin = origin(url) == origin(login.PORTAL_ORIGIN)
    except ValueError:
        return 'unknown'
    if not same_origin:
        return 'unknown'
    path = urlparse(url).path
    if path == '/homepage/index.html':
        return 'authenticated'
    if path in ('/ac_portal/needauth.html', '/ac_portal/proxy.html') or (
        path.startswith('/ac_portal/') and path.endswith('/pc.html')
    ):
        return 'auth_required'
    return 'unknown'


def info_state(status, payload):
    return login.authentication_state(status, json.dumps(payload).encode("utf-8"))[0]


def root_state(result):
    if result.get('http_status') != 200:
        return 'unknown'
    state = route(result.get('final_url', ''))
    if state != 'unknown':
        return state
    if any(route(hop.get('to_url', '')) == 'auth_required' for hop in result.get('http_redirects', [])):
        return 'auth_required'
    return 'unknown'


def combine(first, second):
    known = {first, second} - {'unknown'}
    return known.pop() if len(known) == 1 else 'unknown'


def query_info():
    started = time.monotonic()
    observation = {'time': diag.stamp(), 'state': 'unknown'}
    try:
        opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
        request = Request(login.PORTAL_ORIGIN + '/homepage/info.php', data=b'opr=list', headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
            'Origin': login.PORTAL_ORIGIN, 'Referer': login.PORTAL_PAGE,
            'X-Requested-With': 'XMLHttpRequest',
        })
        with opener.open(request, timeout=3) as response:
            payload = json.loads(response.read())
            observation.update(http_status=response.status, state=info_state(response.status, payload))
            if isinstance(payload, dict):
                observation['success'] = payload.get('success')
                if observation['state'] == 'authenticated':
                    observation['lastonline'] = payload['data']['basic'].get('lastonline')
                elif observation['state'] == 'auth_required':
                    observation['needauth_path'] = urlparse(payload.get('location', '')).path
    except Exception as exc:
        observation['error_type'] = type(exc).__name__
    observation['finished_at'] = diag.stamp()
    observation['duration_seconds'] = round(time.monotonic() - started, 4)
    return observation


def target_wifi(ssid):
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True,
                                timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        # SSIDs are Unicode on Windows; netsh console encoding follows the OEM code page.
        encoding = f'cp{ctypes.windll.kernel32.GetOEMCP()}' if os.name == 'nt' else 'utf-8'
        text = result.stdout.decode(encoding, errors='replace')
        if result.returncode != 0:
            return 'network_unverified'
        names = re.findall(r'^\s*SSID\s*:\s*(.*?)\s*$', text, re.M)
        return 'target_network' if ssid in names else 'wrong_network'
    except Exception:
        return 'network_unverified'


class Tracker:
    def __init__(self):
        self.last_online = None
        self.active = None
        self.events = []

    def observe(self, state, at):
        if state in ('wrong_network', 'network_unverified', 'observation_gap'):
            if self.active:
                self.active['censored_at'] = at
                self.active['censored_reason'] = state
                self.active = None
            self.last_online = None
        elif state == 'auth_required' and self.active is None:
            self.active = {'last_online': self.last_online, 'detected_at': at,
                           'observed_loss': self.last_online is not None,
                           'recovered_at': None, 'censored_at': None, 'attempts': []}
            self.events.append(self.active)
        elif state == 'authenticated':
            if self.active:
                self.active['recovered_at'] = at
                self.active = None
            self.last_online = at


def summary(output):
    counts = {}
    for path in sorted(output.glob('run-*.json')):
        report = json.loads(path.read_text(encoding='utf-8'))
        events = report.get('events', [])
        losses = [event for event in events if event['observed_loss']]
        print(f'\n{path.name}: started={report["started_at"]} observed_losses={len(losses)} finished={report.get("finished", False)}')
        for event in events:
            delay = 'unresolved'
            if event.get('recovered_at'):
                delay = f'{(datetime.fromisoformat(event["recovered_at"]) - datetime.fromisoformat(event["detected_at"])).total_seconds():.3f}s'
            print(f'  last_online={event["last_online"]} detected={event["detected_at"]} recovered={event["recovered_at"]} delay={delay} attempts={len(event["attempts"])} observed_loss={event["observed_loss"]} censored={event["censored_at"]}')
            if event['observed_loss']:
                day = event['detected_at'][:10]
                counts[day] = counts.get(day, 0) + 1
    print('\nObserved loss count by local calendar date (not by night):')
    for day, count in sorted(counts.items()):
        print(f'  {day}: {count}')


class WindowsSession:
    def __enter__(self):
        if os.name != 'nt':
            raise RuntimeError('This monitor requires Windows.')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.CreateMutexW(None, False, 'Local\\SIAS_NightMonitor')
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        if error == 183:
            self.kernel.CloseHandle(self.handle)
            raise RuntimeError('Another SIAS monitor is running. Stop it first.')
        self.kernel.SetThreadExecutionState(0x80000001)
        return self

    def __exit__(self, *args):
        self.kernel.SetThreadExecutionState(0x80000000)
        self.kernel.CloseHandle(self.handle)


def record_login(output, cleaner, event):
    name = 'login-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'
    recorder = diag.Recorder(output / name, cleaner.secrets)
    recorder.phase = 'login'
    factory = login.build_portal_opener
    handler = diag.RecordedLog(recorder)
    level = login.LOGGER.level
    attempt = {'started_at': diag.stamp(), 'detail_file': name, 'exit_code': None}
    event['attempts'].append(attempt)
    started = time.monotonic()
    try:
        login.build_portal_opener = lambda: diag.RecordedOpener(factory(), recorder)
        login.LOGGER.addHandler(handler)
        login.LOGGER.setLevel(logging.INFO)
        attempt['exit_code'] = login.run_login()
        return attempt
    finally:
        login.build_portal_opener = factory
        login.LOGGER.removeHandler(handler)
        login.LOGGER.setLevel(level)
        attempt['finished_at'] = diag.stamp()
        attempt['duration_seconds'] = round(time.monotonic() - started, 4)
        recorder.report['login'] = attempt.copy()
        recorder.save()


def verify_internet(output, cleaner):
    recorder = diag.Recorder(output / ('internet-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'), cleaner.secrets)
    recorder.phase = 'internet'
    result = {'state': 'unknown', 'detail_file': recorder.path.name}
    try:
        opener = diag.RecordedOpener(build_opener(ProxyHandler({})), recorder)
        with opener.open(Request('http://www.msftconnecttest.com/connecttest.txt',
                                 headers={'Cache-Control': 'no-cache'}), timeout=3) as response:
            body = response.read()
            if response.status == 200 and body.strip() == b'Microsoft Connect Test':
                result['state'] = 'online'
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    result['checked_at'] = diag.stamp()
    recorder.report['result'] = result
    recorder.save()
    return result


def main():
    parser = argparse.ArgumentParser(description='Continuously check SIAS portal state; login only when authentication is required.')
    parser.add_argument('--interval', type=float, default=1.0)
    parser.add_argument('--retry', type=float, default=5.0)
    parser.add_argument('--until', default='08:00', help='next local HH:MM; ignored with --continuous')
    parser.add_argument('--continuous', action='store_true')
    parser.add_argument('--ssid', default='UESTC')
    parser.add_argument('--env', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--observe-only', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    output = args.output or base / 'results'
    if args.summary:
        summary(output)
        return 0
    if args.interval < 0.5 or args.retry < 2:
        parser.error('--interval must be >=0.5 seconds; --retry must be >=2 seconds')
    if not args.continuous:
        try:
            end = datetime.combine(datetime.now().date(), datetime.strptime(args.until, '%H:%M').time())
        except ValueError:
            parser.error('--until must be HH:MM')
        if end <= datetime.now():
            end += timedelta(days=1)
    else:
        end = None
    env = args.env or base / '.env'
    if not args.env and not env.is_file():
        env = Path(os.environ.get('LOCALAPPDATA', '')) / 'AutoLogin_SIAS' / '.env'
    try:
        config = login.load_env_file(env)
    except Exception:
        parser.error('Cannot read credential configuration.')
    username = os.getenv('WLAN_USER') or config.get('WLAN_USER', '')
    password = os.getenv('WLAN_PWD') or config.get('WLAN_PWD', '')
    if not args.observe_only and (not username or not password):
        parser.error('Credentials missing. Specify --env with the installed .env file.')
    login.ENV_PATH = env
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run_path = output / ('run-' + run_id + '.json')
    cleaner = diag.Recorder(run_path, (username, password))
    tracker = Tracker()
    report = {'format_version': 1, 'started_at': diag.stamp(), 'finished': False,
              'interval_seconds': args.interval, 'retry_seconds': args.retry,
              'ssid': args.ssid, 'observe_only': args.observe_only,
              'login_version': login.VERSION, 'events': tracker.events, 'unknown_samples': 0}
    def save():
        report['updated_at'] = diag.stamp()
        temporary = run_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(cleaner.clean(report), ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(run_path)
    def append(kind, **fields):
        item = cleaner.clean({'time': diag.stamp(), 'kind': kind, **fields})
        file = output / ('samples-' + datetime.now().strftime('%Y%m%d') + '-' + run_id + '.jsonl')
        with file.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')
    previous = None
    last_tick = time.monotonic()
    next_retry = 0.0
    next_wifi = 0.0
    network = 'network_unverified'
    failures = 0
    unknown_streak = 0
    print(f'Monitor started; stop={end or "Ctrl+C"}; interval={args.interval}s; results={output}', flush=True)
    try:
        with WindowsSession():
            save()
            while end is None or datetime.now() < end:
                tick = time.monotonic()
                if tick - last_tick > max(120, args.interval * 3):
                    tracker.observe('observation_gap', diag.stamp())
                    append('observation_gap', duration_seconds=round(tick-last_tick, 3))
                last_tick = tick
                if tick >= next_wifi:
                    network = target_wifi(args.ssid)
                    next_wifi = time.monotonic() + 5
                observation = query_info() if network == 'target_network' else {'time': diag.stamp(), 'state': network}
                state = observation['state']
                if network == 'target_network' and (state != 'authenticated' or previous != 'authenticated'):
                    proof = diag.Recorder(output / ('proof-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'), cleaner.secrets)
                    root_result = diag.observe_root(proof)
                    root_candidate = root_state(root_result)
                    observation.update(root_state=root_candidate, info_state=state,
                                       root_final_path=root_result.get('final_path'),
                                       proof_file=proof.path.name)
                    proof.report['root_navigation'] = root_result
                    proof.save()
                    state = combine(state, root_candidate)
                    observation['state'] = state
                observed = diag.stamp()
                observation['observed_at'] = observed
                tracker.observe(state, observed)
                append('sample', observation=observation)
                if state != previous:
                    append('state_change', previous=previous, current=state)
                    print(f'{observed} {previous} -> {state}', flush=True)
                    previous = state
                if state == 'unknown':
                    report['unknown_samples'] += 1
                    unknown_streak += 1
                else:
                    unknown_streak = 0
                if state == 'authenticated':
                    failures = 0
                    next_retry = 0
                if state == 'auth_required' and not args.observe_only and time.monotonic() >= next_retry:
                    # Recheck Wi-Fi immediately before submitting credentials.
                    network = target_wifi(args.ssid)
                    if network == 'target_network':
                        save()
                        event = tracker.active
                        attempt = record_login(output, cleaner, event)
                        append('login_attempt', **attempt)
                        after = query_info()
                        after['observed_at'] = diag.stamp()
                        append('post_login_sample', observation=after)
                        tracker.observe(after['state'], after['observed_at'])
                        if after['state'] != previous:
                            append('state_change', previous=previous, current=after['state'])
                            previous = after['state']
                        recovered = after['state'] == 'authenticated'
                        attempt['portal_after'] = after['state']
                        failures = 0 if recovered else min(failures + 1, 5)
                        next_retry = time.monotonic() + min(60, args.retry * 2 ** max(0, failures-1))
                        if recovered:
                            append('portal_recovered', detected_at=event['detected_at'], recovered_at=event['recovered_at'])
                            attempt['internet_after'] = verify_internet(output, cleaner)
                            append('internet_check', result=attempt['internet_after'])
                        print(f'{after["observed_at"]} login_exit={attempt["exit_code"]} portal_after={after["state"]}', flush=True)
                    else:
                        tracker.observe(network, diag.stamp())
                        append('network_changed_before_login', state=network)
                save()
                delay = args.interval
                if state == 'unknown' or network != 'target_network':
                    delay = min(30, 5 * 2 ** min(unknown_streak, 3))
                wait = max(0.1, delay - (time.monotonic() - tick))
                if end:
                    wait = min(wait, max(0, (end - datetime.now()).total_seconds()))
                time.sleep(wait)
    except KeyboardInterrupt:
        report['stop_reason'] = 'keyboard_interrupt'
    except Exception as exc:
        report['stop_reason'] = type(exc).__name__
        report['error'] = cleaner.clean(str(exc))
        raise
    finally:
        report['finished'] = True
        report['finished_at'] = diag.stamp()
        save()
        print(f'Run summary: {run_path}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
