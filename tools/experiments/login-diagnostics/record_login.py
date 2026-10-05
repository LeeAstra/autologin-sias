"""One recorded execution of the existing login implementation."""
from __future__ import annotations

import argparse
from datetime import datetime
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import parse_qsl, quote, quote_plus, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
import auto_login_headless as login

SENSITIVE = {'pwd', 'password', 'wlan_pwd', 'username', 'user', 'wlan_user',
             'auth_tag', 'cookie', 'set-cookie', 'authorization', 'token',
             'authsessid', 'phone', 'mail', 'showname', 'name', 'custom'}


def stamp():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')


class Recorder:
    def __init__(self, path, secrets=()):
        self.path = path
        self.secrets = set(value for value in secrets if value)
        self.phase = 'before'
        self.report = {'format_version': 2, 'started_at': stamp(),
                       'login_version': login.VERSION, 'requests': [], 'messages': []}

    def clean(self, value):
        if isinstance(value, dict):
            return {str(k): '[REDACTED]' if str(k).lower() in SENSITIVE else self.clean(v)
                    for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        if not isinstance(value, str):
            return value
        for secret in sorted(self.secrets, key=len, reverse=True):
            for variant in {secret, quote(secret, safe=''), quote_plus(secret),
                            json.dumps(secret, ensure_ascii=True)[1:-1]}:
                if variant:
                    value = value.replace(variant, '[REDACTED]')
        # Also handles the portal's JavaScript object responses with single quotes.
        keys = '|'.join(re.escape(key) for key in SENSITIVE)
        value = re.sub(r'([\"\'](?:' + keys + r')[\"\']\s*:\s*)([\"\'])(.*?)(\2)',
                       lambda m: m[1] + m[2] + '[REDACTED]' + m[2], value, flags=re.I)
        value = re.sub(r'((?:AUTHSESSID|token|pwd|auth_tag)=)[^;\s&\"\'<>]+',
                       r'\1[REDACTED]', value, flags=re.I)
        return value

    def body(self, data):
        text = data.decode('utf-8', errors='replace')
        try:
            return self.clean(json.loads(text))
        except json.JSONDecodeError:
            return self.clean(text)

    def save(self):
        self.report['updated_at'] = stamp()
        # Never persist unsanitized report values, even on error paths.
        self.path.write_text(json.dumps(self.clean(self.report), ensure_ascii=False, indent=2), encoding='utf-8')


class RecordedResponse:
    def __init__(self, response, entry, recorder):
        self.response, self.entry, self.recorder = response, entry, recorder
        self.status = response.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.response.close()

    def read(self):
        body = self.response.read()
        self.entry['response_bytes'] = len(body)
        self.entry['response_body'] = self.recorder.body(body)
        self.entry['finished_at'] = stamp()
        self.entry['duration_seconds'] = round(time.perf_counter() - self.entry.pop('_timer'), 4)
        self.recorder.save()
        return body


class RecordedOpener:
    def __init__(self, opener, recorder):
        self.opener, self.recorder = opener, recorder

    def open(self, request, timeout=None):
        data = request.data
        fields = dict(parse_qsl(data.decode('utf-8'), keep_blank_values=True)) if data else None
        if fields:
            self.recorder.secrets.update(v for k, v in fields.items() if k.lower() in SENSITIVE and v)
        entry = {'phase': self.recorder.phase, 'started_at': stamp(),
                 'url': request.full_url, 'method': request.get_method(),
                 'request_form': self.recorder.clean(fields), '_timer': time.perf_counter()}
        self.recorder.report['requests'].append(entry)
        try:
            response = self.opener.open(request, timeout=timeout)
            entry.update(status=response.status, final_url=response.geturl(),
                         request_headers=self.recorder.clean(dict(request.header_items())),
                         response_headers=self.recorder.clean(dict(response.headers.items())))
            return RecordedResponse(response, entry, self.recorder)
        except Exception as exc:
            entry['error_type'] = type(exc).__name__
            entry['error'] = self.recorder.clean(str(exc))
            if isinstance(exc, HTTPError):
                entry.update(status=exc.code, response_headers=self.recorder.clean(dict(exc.headers.items())),
                             response_body=self.recorder.body(exc.read()))
            entry['finished_at'] = stamp()
            entry['duration_seconds'] = round(time.perf_counter() - entry.pop('_timer'), 4)
            self.recorder.save()
            raise


class RedirectTrace(HTTPRedirectHandler):
    def __init__(self, recorder, chain):
        self.recorder, self.chain = recorder, chain

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append(self.recorder.clean({
            'time': stamp(), 'from_url': req.full_url, 'status': code,
            'location': headers.get('Location'), 'to_url': newurl,
            'response_headers': dict(headers.items()),
        }))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NavigationHints(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta_targets = []
        self.scripts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag.lower() == 'meta' and (attributes.get('http-equiv') or '').lower() == 'refresh':
            match = re.search(r'\burl\s*=\s*(.+)', attributes.get('content') or '', re.I)
            if match:
                self.meta_targets.append(match[1].strip().strip('\"\''))
        if tag.lower() == 'script':
            self.in_script = True

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)


def route_candidate(url, origin):
    target, portal = urlparse(url), urlparse(origin)
    try:
        same_origin = (target.scheme == portal.scheme and target.hostname == portal.hostname
                       and (target.port or 80) == (portal.port or 80))
    except ValueError:
        return 'unknown'
    if not same_origin:
        return 'unknown'
    if target.path == '/homepage/index.html':
        return 'authenticated'
    if target.path in ('/ac_portal/needauth.html', '/ac_portal/proxy.html') or (
        target.path.startswith('/ac_portal/') and target.path.endswith('/pc.html')
    ):
        return 'auth_required'
    return 'unknown'


def observe_root(recorder):
    chain = []
    result = {'requested_url': login.PORTAL_ORIGIN + '/', 'http_redirects': chain,
              'route_candidate': 'unknown', 'page_navigation_hints': []}
    opener = RecordedOpener(build_opener(HTTPCookieProcessor(CookieJar()),
                                        RedirectTrace(recorder, chain)), recorder)
    try:
        with opener.open(Request(result['requested_url'], headers={
            'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
            'User-Agent': 'Mozilla/5.0 AutoLogin-SIAS-Diagnostic/2',
        }), timeout=8) as response:
            body = response.read()
            final_url = response.response.geturl()
            result.update(final_url=final_url, final_path=urlparse(final_url).path,
                          http_status=response.status)
            if response.status == 200:
                result['route_candidate'] = route_candidate(final_url, login.PORTAL_ORIGIN)
            hints = NavigationHints()
            hints.feed(body.decode('utf-8', errors='replace'))
            targets = [('meta_refresh', target) for target in hints.meta_targets]
            for script in hints.scripts:
                patterns = [r'(?:(?:window|top|self|document)\s*\.\s*)?location(?:\s*\.\s*href)?\s*=\s*([\"\'])(.*?)\1',
                            r'(?:(?:window|top|self|document)\s*\.\s*)?location\s*\.\s*(?:replace|assign)\s*\(\s*([\"\'])(.*?)\1']
                for pattern in patterns:
                    targets.extend(('javascript_literal', match[2]) for match in re.finditer(pattern, script, re.I))
            for source, target in targets:
                resolved = urljoin(final_url, target)
                result['page_navigation_hints'].append({
                    'source': source, 'target_url': resolved,
                    'route_candidate': route_candidate(resolved, login.PORTAL_ORIGIN),
                    'verified': False,
                })
            result['note'] = 'HTTP redirects were followed; page scripts were not executed. Hints may be conditional.'
    except Exception as exc:
        result['error_type'] = type(exc).__name__
        result['error'] = recorder.clean(str(exc))
    return recorder.clean(result)


def observe(recorder, portal_factory):
    result = {}
    # This is a separate session; original login opener/cookie handling is unchanged.
    try:
        status, body = login.request(RecordedOpener(portal_factory(), recorder),
                                     login.PORTAL_ORIGIN + '/homepage/info.php', data={'opr': 'list'})
        result['portal_info_http_status'] = status
        result['portal_info_note'] = 'Portal authentication and external connectivity are separate observations.'
        candidate, _ = login.authentication_state(status, body)
        result['portal_info_state_candidate'] = candidate
    except Exception as exc:
        result['portal_info_error'] = type(exc).__name__
    result['root_navigation'] = observe_root(recorder)
    candidates = {result.get('portal_info_state_candidate', 'unknown'),
                  result['root_navigation']['route_candidate']} - {'unknown'}
    result['portal_state_candidate'] = candidates.pop() if len(candidates) == 1 else 'unknown'
    result['portal_evidence_conflict'] = (
        result.get('portal_info_state_candidate', 'unknown') != 'unknown'
        and result['root_navigation']['route_candidate'] != 'unknown'
        and result.get('portal_info_state_candidate') != result['root_navigation']['route_candidate']
    )
    try:
        opener = RecordedOpener(build_opener(ProxyHandler({})), recorder)
        request = Request('http://www.msftconnecttest.com/connecttest.txt',
                          headers={'Cache-Control': 'no-cache'})
        with opener.open(request, timeout=8) as response:
            body = response.read()
            entry = recorder.report['requests'][-1]
            if response.status == 200 and body.strip() == b'Microsoft Connect Test':
                state = 'online'
            elif '2.2.2.3' in entry.get('final_url', '') or b'2.2.2.3/ac_portal' in body:
                state = 'auth_required'
            else:
                state = 'unknown'
            result['connectivity'] = state
    except Exception as exc:
        result.update(connectivity='unknown', probe_error=type(exc).__name__)
    return result


class RecordedLog(logging.Handler):
    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder

    def emit(self, record):
        self.recorder.report['messages'].append({'time': stamp(), 'level': record.levelname,
                                                'message': self.recorder.clean(record.getMessage())})


def main():
    parser = argparse.ArgumentParser(description='Run the original SIAS login once and save sanitized diagnostics.')
    parser.add_argument('--env', type=Path, help='existing .env path')
    parser.add_argument('--label', default='', help='e.g. offline or already-online')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    candidates = [base / '.env', Path(os.environ.get('LOCALAPPDATA', '')) / 'AutoLogin_SIAS' / '.env', login.ENV_PATH]
    env = args.env or next((path for path in candidates if path.is_file()), candidates[0])
    try:
        config = login.load_env_file(env)
    except Exception:
        parser.error('Cannot read credential configuration.')
    username = os.getenv('WLAN_USER') or config.get('WLAN_USER', '')
    password = os.getenv('WLAN_PWD') or config.get('WLAN_PWD', '')
    if not username or not password:
        parser.error('Credentials missing. Use --env with the installed .env file.')
    output = args.output or base / 'results'
    output.mkdir(parents=True, exist_ok=True)
    path = output / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    recorder = Recorder(path, (username, password))
    recorder.report['label'] = args.label
    recorder.report['notes'] = ['Credentials, encrypted password, auth_tag and session headers are redacted.',
                                'Original login flow is unchanged; before/after observations are additional requests.',
                                'External confirmation uses a direct connection; VPN routing can still affect it.']
    original_factory = login.build_portal_opener
    original_env = login.ENV_PATH
    handler = RecordedLog(recorder)
    old_level = login.LOGGER.level
    code = 9
    try:
        login.ENV_PATH = env
        login.LOGGER.addHandler(handler)
        login.LOGGER.setLevel(logging.INFO)
        print('Checking state before login...', flush=True)
        recorder.report['before'] = observe(recorder, original_factory)
        recorder.phase = 'login'
        login.build_portal_opener = lambda: RecordedOpener(original_factory(), recorder)
        started = time.perf_counter()
        code = login.run_login()
        recorder.report['login'] = {'exit_code': code, 'duration_seconds': round(time.perf_counter() - started, 4)}
        recorder.phase = 'after'
        print('Checking state after login...', flush=True)
        recorder.report['after'] = observe(recorder, original_factory)
        for phase in ('before', 'after'):
            observation = recorder.report[phase]
            print(f'{phase}: portal={observation["portal_state_candidate"]}; '
                  f'root={observation["root_navigation"]["route_candidate"]}; '
                  f'internet={observation["connectivity"]}')
        print(f'Login exit code: {code}')
    finally:
        login.build_portal_opener = original_factory
        login.ENV_PATH = original_env
        login.LOGGER.removeHandler(handler)
        login.LOGGER.setLevel(old_level)
        recorder.report['finished_at'] = stamp()
        recorder.save()
        print(f'Record saved: {path}', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
