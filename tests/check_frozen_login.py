"""Exercise the shipped EXE against a loopback proxy using synthetic credentials.

No requests reach the real portal and no system tasks are registered.
"""
import os
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
response = {'body': b'{"success":true}', 'status': 200}


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
        self.send_response(response['status'] if is_login else 200)
        self.end_headers()
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
            ('boolean-result-rejected', b'{"result":false}', 200, 5),
            ('unrecognized-html', b'<html>portal</html>', 200, 8),
            ('empty-response', b'', 200, 8),
            ('server-error', b'Unavailable', 503, 6),
        ]:
            response.update(body=body, status=status)
            requests.clear()
            result = subprocess.run([str(exe), '--check'], cwd=work, env=env, timeout=60)
            assert result.returncode == expected, (label, result.returncode, expected)
            posts = [r for r in requests if r[0] == 'POST']
            assert posts and posts[0][3] == 'session=frozen-test', label
            assert b'userName=synthetic-user' in posts[0][2], label
            assert b'pwd=synthetic-password' not in posts[0][2], label
            print(f'Frozen EXE: {label} -> {result.returncode} OK')

        response.update(body=b'{"success":true}', status=200)
        for password in [' spaced-password ', '"quoted-password"', r'back\slash']:
            write_env_file(work / '.env', 'synthetic-user', password)
            requests.clear()
            result = subprocess.run([str(exe), '--check'], cwd=work, env=env, timeout=60)
            assert result.returncode == 0
            form = parse_qs(next(r[2] for r in requests if r[0] == 'POST').decode())
            assert form['pwd'][0] == rc4_hex(password, form['auth_tag'][0])
        print('Frozen EXE: whitespace, quotes and backslashes preserved through encryption OK')

        # Exercise file deployment and the real child EXE. Only task registration
        # is replaced; its XML is covered separately by Test-TaskPreview.ps1.
        fixture_payload = work / 'payload'
        fixture_payload.mkdir()
        shutil.copy2(exe_source, fixture_payload / exe_source.name)
        shutil.copy2(root / 'scripts/Install-AutoLoginTask.ps1', fixture_payload)
        target = work / 'installed'
        task_calls = []

        def run_child(args, **kwargs):
            if args[0].lower().endswith('powershell.exe'):
                task_calls.append(args)
                return SimpleNamespace(returncode=0)
            kwargs['env'] = env
            return subprocess.run(args, **kwargs)

        response.update(body=b'{"success":true}', status=200)
        install_autologin.install(fixture_payload, target, 'synthetic-user', 'synthetic-password', run_child)
        assert len(task_calls) == 1
        assert (target / exe_source.name).read_bytes() == exe_source.read_bytes()
        old_config = (target / '.env').read_bytes()
        response.update(body=b'{"success":false}')
        try:
            install_autologin.install(fixture_payload, target, 'other-user', 'other-password', run_child)
            raise AssertionError('Rejected authentication accepted by installer')
        except RuntimeError:
            pass
        assert (target / '.env').read_bytes() == old_config
        assert len(task_calls) == 1, 'Task registration reached after failed authentication'
        print('Deployment with real child EXE: success and failed-upgrade rollback OK')
finally:
    server.shutdown()
    thread.join()
    server.server_close()
