"""Exercise the shipped EXE against a loopback proxy using synthetic credentials.

No requests reach the real portal and no system tasks are registered.
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
import install_autologin
from credentials import write_env_file
from auto_login_headless import rc4_hex

requests = []
login_times = []
response = {'body': b'{"success":true}', 'status': 200, 'prior': 'auth_required', 'post': 'authenticated'}


def configure_response(**overrides):
    # Each scenario owns a complete fixture state; never inherit prior failures.
    response.clear()
    response.update(body=b'{"success":true}',status=200,prior='auth_required',
                    post='authenticated',sequence=[])
    response.update(overrides)
    requests.clear()
    login_times.clear()


class PortalProxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        requests.append(('GET', self.path, b'', None))
        self.send_response(200)
        self.send_header('Set-Cookie', 'session=frozen-test; Path=/')
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        requests.append(('POST', self.path, body, self.headers.get('Cookie')))
        is_login = self.path.endswith('/ac_portal/login.php')
        if is_login:
            login_times.append(datetime.now().astimezone())
        is_info = self.path.endswith('/homepage/info.php')
        self.send_response(response['status'] if is_login else 200)
        self.end_headers()
        if is_info:
            state = response['sequence'].pop(0) if response.get('sequence') else response['post'] if any(r[1].endswith('/ac_portal/login.php') for r in requests) else response['prior']
            if state == 'authenticated':
                payload = b'{"success":true,"data":{"basic":{}}}'
            elif state == 'auth_required':
                payload = b'{"success":false,"location":"http://2.2.2.3:80/ac_portal/needauth.html"}'
            else:
                payload = b'unrecognized info'
            self.wfile.write(payload)
        else:
            self.wfile.write(response['body'] if is_login else b'1')


server = ThreadingHTTPServer(('127.0.0.1', 0), PortalProxy)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
proxy = f'http://127.0.0.1:{server.server_port}'
env = {k: v for k, v in os.environ.items()
       if k.upper() not in ('WLAN_USER', 'WLAN_PWD', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')}
env.update(http_proxy=proxy, https_proxy=proxy, no_proxy='')
exe_source = root / 'packaging/dist/AutoLogin_SIAS_Headless.exe'

try:
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        exe = work / exe_source.name
        shutil.copy2(exe_source, exe)
        (work / '.env').write_text('WLAN_USER=synthetic-user\nWLAN_PWD=synthetic-password\n')
        for label, body, status, expected in [
            ('success', b'{"success":true}', 200, 0),
            ('rejected', b'{"success":false}', 200, 5),
            ('javascript-rejected', b"{'success':false,'msg':'denied'}", 200, 5),
            ('boolean-result-rejected', b'{"result":false}', 200, 5),
            ('unrecognized-html', b'<html>portal</html>', 200, 8),
            ('empty-response', b'', 200, 8),
            ('server-error', b'Unavailable', 503, 6),
        ]:
            configure_response(body=body, status=status)
            result = subprocess.run([str(exe), '--check'], cwd=work, env=env, timeout=60)
            assert result.returncode == expected, (label, result.returncode, expected)
            posts = [r for r in requests if r[1].endswith('/ac_portal/login.php')]
            assert posts and posts[0][3] == 'session=frozen-test', label
            assert b'userName=synthetic-user' in posts[0][2], label
            assert b'pwd=synthetic-password' not in posts[0][2], label
            print(f'Frozen EXE: {label} -> {result.returncode} OK')

        # Online state must not rescue explicit credential rejection.
        for body,expected in [(b'{"message":"login success: false"}',8),
                              (b'{"message":"login successful? no"}',8),
                              (b'{"message":"login unsuccessful"}',5),
                              (b'{"msg":"login failed: already online"}',5),
                              (b'{"message":"login not successful"}',5),
                              (b'{"success":false,"message":"login successful"}',5),
                              (b'{"message":"login successful"}',0),
                              (b'{"message":"login successful but error"}',8)]:
            configure_response(body=body,status=200,prior='authenticated',post='authenticated')
            result=subprocess.run([str(exe),'--validate-credentials'],cwd=work,env=env,timeout=60)
            assert result.returncode==expected,(body,result.returncode,expected)
            assert any(r[1].endswith('/ac_portal/login.php') for r in requests)
        print('Frozen EXE: forced online validation rejects failure/ambiguous messages OK')

        for prior, post, expected in [('authenticated', 'unknown', 0), ('unknown', 'authenticated', 0),
                                      ('auth_required', 'auth_required', 8), ('auth_required', 'unknown', 8)]:
            configure_response(body=b'{"success":true}', status=200, prior=prior, post=post)
            result = subprocess.run([str(exe), '--check'], cwd=work, env=env, timeout=60)
            assert result.returncode == expected, (prior, post, result.returncode)
            login_requests = [r for r in requests if r[1].endswith('/ac_portal/login.php')]
            assert bool(login_requests) == (prior != 'authenticated')
            print(f'Frozen EXE: prior={prior} post={post} -> {expected} OK')

        for password in [' spaced-password ', '"quoted-password"', r'back\slash']:
            configure_response()
            write_env_file(work / '.env', 'synthetic-user', password)
            result = subprocess.run([str(exe), '--check'], cwd=work, env=env, timeout=60)
            assert result.returncode == 0
            form = parse_qs(next(r[2] for r in requests if r[1].endswith('/ac_portal/login.php')).decode())
            assert form['pwd'][0] == rc4_hex(password, form['auth_tag'][0])
        print('Frozen EXE: whitespace, quotes and backslashes preserved through encryption OK')

        # Test-only frozen harness substitutes the WLAN observation. Production
        # artifacts never contain this hook or any environment-driven Wi-Fi bypass.
        hook=work/'fixture_wlan.py'
        hook.write_text("from sias_autologin.platforms.windows import runner\nrunner.target_wifi=lambda ssid: 'target_network'\n")
        spec=(root/'packaging/auto_login_headless.spec').read_text()
        spec=spec.replace("'../src/auto_login_headless.py'",repr(str(root/'src/auto_login_headless.py')))
        spec=spec.replace("'../src'",repr(str(root/'src')))
        spec=spec.replace('runtime_hooks=[]','runtime_hooks=['+repr(str(hook))+']')
        spec=spec.replace("name='AutoLogin_SIAS_Headless'","name='WlanPolicyFixture'")
        fixture_spec=work/'fixture.spec'; fixture_spec.write_text(spec)
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(work),
                        '--workpath',str(work/'build'),str(fixture_spec)],check=True,timeout=180)
        maintenance_exe=work/'WlanPolicyFixture.exe'
        for latest,submitted,confirmed in [('unknown',False,False),('authenticated',False,True),('auth_required',True,True)]:
            configure_response(body=b'{"success":true}',status=200,prior=latest,post='authenticated',sequence=['auth_required',latest])
            log=work/'auto_login_headless.log'
            log.unlink(missing_ok=True)
            begin=(datetime.now()-timedelta(minutes=1)).strftime('%H:%M:%S')
            end=(datetime.now()+timedelta(seconds=8)).strftime('%H:%M:%S')
            result=subprocess.run([str(maintenance_exe),'--maintain','night','--window-start',begin,'--window-end',end],cwd=work,env=env,timeout=45)
            assert result.returncode==0,(latest,result.returncode)
            posts=[r for r in requests if r[1].endswith('/ac_portal/login.php')]
            assert bool(posts)==submitted,(latest,requests)
            events=[json.loads(line.split('Maintenance event: ',1)[1]) for line in log.read_text(encoding='utf-8').splitlines() if 'Maintenance event: ' in line]
            login_event=next(e for e in events if e['event']=='login_result')
            assert login_event['submitted'] is submitted and login_event['confirmed'] is confirmed, (latest,events)
            assert events[0]['event']=='start' and events[-1]['event']=='end'
        response.pop('sequence',None)
        print('Test-only frozen maintenance harness: latest unknown/authenticated/required submission policy and per-run evidence OK')

        # Transient latest-state uncertainty must not consume credential cooldown.
        configure_response(body=b'{"success":true}',status=200,prior='authenticated',post='authenticated',
                        sequence=['auth_required','unknown','auth_required','auth_required'])
        log.unlink(missing_ok=True)
        begin=(datetime.now()-timedelta(minutes=1)).strftime('%H:%M:%S')
        end=(datetime.now()+timedelta(seconds=12)).strftime('%H:%M:%S')
        result=subprocess.run([str(maintenance_exe),'--maintain','night','--window-start',begin,
                               '--window-end',end],cwd=work,env=env,timeout=45)
        assert result.returncode==0
        events=[json.loads(line.split('Maintenance event: ',1)[1]) for line in
                log.read_text(encoding='utf-8').splitlines() if 'Maintenance event: ' in line]
        outcomes=[e for e in events if e['event']=='login_result']
        assert [e['submitted'] for e in outcomes]==[False,True],events
        gap=(datetime.fromisoformat(outcomes[1]['timestamp'])-
             datetime.fromisoformat(outcomes[0]['timestamp'])).total_seconds()
        assert 5<=gap<15, gap
        assert len([r for r in requests if r[1].endswith('/ac_portal/login.php')])==1

        # A real rejected submission still waits at least 15 seconds after completion.
        configure_response(body=b'{"success":false}',status=200,prior='auth_required',
                        post='auth_required',sequence=[])
        log.unlink(missing_ok=True)
        begin=(datetime.now()-timedelta(minutes=1)).strftime('%H:%M:%S')
        end=(datetime.now()+timedelta(seconds=23)).strftime('%H:%M:%S')
        result=subprocess.run([str(maintenance_exe),'--maintain','night','--window-start',begin,
                               '--window-end',end],cwd=work,env=env,timeout=45)
        assert result.returncode==0
        events=[json.loads(line.split('Maintenance event: ',1)[1]) for line in
                log.read_text(encoding='utf-8').splitlines() if 'Maintenance event: ' in line]
        outcomes=[e for e in events if e['event']=='login_result']
        assert len(outcomes)==len(login_times)==2,events
        gap=(login_times[1]-datetime.fromisoformat(outcomes[0]['timestamp'])).total_seconds()
        assert gap>=15,gap
        print('Test-only frozen maintenance: skipped submission rechecks next cycle; rejected POST retains >=15s cooldown OK')


        # Exercise file deployment and the real child EXE. Only task registration
        # is replaced; its XML is covered separately by Test-TaskPreview.ps1.
        fixture_payload = work / 'payload'
        fixture_payload.mkdir()
        shutil.copy2(exe_source, fixture_payload / exe_source.name)
        shutil.copy2(root / 'scripts/windows/Install-AutoLoginTask.ps1', fixture_payload)
        target = work / 'installed'
        task_calls = []

        def run_child(args, **kwargs):
            if args[0].lower().endswith('powershell.exe'):
                task_calls.append(args)
                return SimpleNamespace(returncode=0)
            kwargs['env'] = env
            return subprocess.run(args, **kwargs)

        configure_response(body=b'{"success":true}', status=200)
        install_autologin.install(fixture_payload, target, 'synthetic-user', 'synthetic-password', run_child)
        assert len(task_calls) == 1
        assert (target / exe_source.name).read_bytes() == exe_source.read_bytes()
        old_config = (target / '.env').read_bytes()
        configure_response(body=b"{'success':false,'msg':'denied'}", prior='authenticated', post='authenticated')
        try:
            install_autologin.install(fixture_payload, target, 'other-user', 'other-password', run_child)
            raise AssertionError('Rejected authentication accepted by installer')
        except RuntimeError:
            pass
        assert any(r[1].endswith('/ac_portal/login.php') for r in requests), 'Online credential validation skipped'
        assert (target / '.env').read_bytes() == old_config
        assert len(task_calls) == 1, 'Task registration reached after failed authentication'
        print('Deployment with real child EXE: success and failed-upgrade rollback OK')
finally:
    server.shutdown()
    thread.join()
    server.server_close()
