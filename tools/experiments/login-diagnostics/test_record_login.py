import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_login as diag


class Response:
    status = 200
    headers = {'Set-Cookie': 'AUTHSESSID=private-session; HttpOnly'}
    def __init__(self, body):
        self.content = body
    def read(self):
        return self.content
    def close(self):
        pass
    def geturl(self):
        return 'http://2.2.2.3/ac_portal/login.php'


class DiagnosticTests(unittest.TestCase):
    def test_default_port_and_proxy_path(self):
        origin = 'http://2.2.2.3'
        self.assertEqual(diag.route_candidate('http://2.2.2.3:80/ac_portal/proxy.html', origin), 'auth_required')
        self.assertEqual(diag.route_candidate('https://2.2.2.3/ac_portal/needauth.html', origin), 'unknown')
        self.assertEqual(diag.route_candidate('http://2.2.2.3:bad/ac_portal/needauth.html', origin), 'unknown')
    def test_root_redirects_for_both_states_and_javascript_hint(self):
        fixture = {'target': '/ac_portal/20210120210326/pc.html?mac=test-device'}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                if self.path == '/' and fixture['target']:
                    self.send_response(302)
                    self.send_header('Location', fixture['target'])
                    self.send_header('Set-Cookie', 'AUTHSESSID=redirect-secret; Path=/')
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'<script>if (false) { window.location.href="/homepage/index.html?_FLAG=1"; }</script>')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(
                diag.login, 'PORTAL_ORIGIN', f'http://127.0.0.1:{server.server_port}'
            ):
                recorder = diag.Recorder(Path(directory) / 'run.json')
                for target, expected in [('/ac_portal/20210120210326/pc.html?mac=test-device', 'auth_required'),
                                         ('/homepage/index.html?_FLAG=1', 'authenticated'),
                                         (None, 'unknown')]:
                    fixture['target'] = target
                    result = diag.observe_root(recorder)
                    self.assertEqual(result['route_candidate'], expected)
                    self.assertEqual(len(result['http_redirects']), 1 if target else 0)
                    self.assertEqual(result['page_navigation_hints'][0]['route_candidate'], 'authenticated')
                    self.assertFalse(result['page_navigation_hints'][0]['verified'])
                    if target:
                        self.assertEqual(result['http_redirects'][0]['response_headers']['Set-Cookie'], '[REDACTED]')
                self.assertNotIn('redirect-secret', recorder.path.read_text(encoding='utf-8'))
                self.assertEqual(diag.route_candidate('http://other.example/homepage/index.html', diag.login.PORTAL_ORIGIN), 'unknown')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_meta_refresh_is_only_a_hint(self):
        hints = diag.NavigationHints()
        hints.feed('<meta http-equiv="refresh" content="0; url=/ac_portal/needauth.html">')
        self.assertEqual(hints.meta_targets, ['/ac_portal/needauth.html'])

    def test_redacts_json_and_javascript_and_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = diag.Recorder(Path(directory) / 'run.json', ('account-example', 'password-example'))
            cleaned = recorder.clean({'Set-Cookie': 'session', 'Cookie': 'session', 'Authorization': 'secret'})
            self.assertTrue(all(v == '[REDACTED]' for v in cleaned.values()))
            self.assertEqual(recorder.body(b'{"success":true,"data":{"basic":{"name":"account-example","phone":"123","showname":"person"}}}')['data']['basic']['showname'], '[REDACTED]')
            body = recorder.body(b"{'success':true,'userName':'account-example','msg':'logon success'}")
            self.assertNotIn('account-example', body)
            self.assertIn("'success':true", body)

    def test_original_login_flow_unchanged_and_secrets_not_saved(self):
        requests = []
        class Opener:
            def open(self, request, timeout=None):
                requests.append(request)
                return Response(b"{'success':true,'userName':'account-example','msg':'logon success'}")
        with tempfile.TemporaryDirectory() as directory:
            recorder = diag.Recorder(Path(directory) / 'run.json', ('account-example', 'password-example'))
            recorder.phase = 'login'
            with patch.dict(diag.os.environ, {'WLAN_USER': 'account-example', 'WLAN_PWD': 'password-example'}), \
                 patch.object(diag.login, 'load_env_file', return_value={}), \
                 patch.object(diag.login, 'query_authentication_state', side_effect=[('auth_required', 'test'), ('authenticated', 'test')]), \
                 patch.object(diag.login, 'build_portal_opener', return_value=diag.RecordedOpener(Opener(), recorder)):
                self.assertEqual(diag.login.run_login(), 0)
            self.assertEqual(len(requests), 3)
            self.assertEqual([item.get_method() for item in requests], ['GET', 'POST', 'POST'])
            self.assertEqual([item['url'] for item in recorder.report['requests']],
                             [diag.login.PORTAL_PAGE, diag.login.LOGIN_URL, diag.login.CHECK_JUMP_URL])
            form = dict(diag.parse_qsl(requests[1].data.decode()))
            self.assertEqual(form['userName'], 'account-example')
            self.assertNotEqual(form['pwd'], 'password-example')
            saved = recorder.path.read_text(encoding='utf-8')
            for secret in ('account-example', 'password-example', form['pwd'], form['auth_tag'], 'private-session'):
                self.assertNotIn(secret, saved)
            self.assertEqual(json.loads(saved)['requests'][1]['request_form']['opr'], 'pwdLogin')


if __name__ == '__main__':
    unittest.main()
