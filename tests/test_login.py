import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import auto_login_headless as login


class LoginTests(unittest.TestCase):
    def test_rc4_known_vector(self):
        self.assertEqual(login.rc4_hex('Plaintext', 'Key'), 'bbf316e8d940af0ad3')

    def test_response_variants(self):
        for body, expected in [(b'{"success":true}', True),
                               (b'{"success":false}', False),
                               (b'{"result":false}', False),
                               (b'{"result":true}', True),
                               (b'<html>portal</html>', None), (b'', None)]:
            with self.subTest(body=body):
                self.assertIs(login.response_indicates_success(body)[0], expected)

    def test_env_bom_and_quoted_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('# comment\nWLAN_USER="demo"\nWLAN_PWD=a=b\n', encoding='utf-8-sig')
            self.assertEqual(login.load_env_file(path), {'WLAN_USER': 'demo', 'WLAN_PWD': 'a=b'})

    def test_exit_codes(self):
        for body, expected in [(b'{"success":true}', 0), (b'{"success":false}', 5), (b'unknown', 8)]:
            with self.subTest(expected=expected), patch.dict(os.environ, {}, clear=True), \
                 patch.object(login, 'load_env_file', return_value={'WLAN_USER': 'demo', 'WLAN_PWD': 'demo'}), \
                 patch.object(login, 'query_authentication_state', side_effect=[('auth_required', 'test'), ('authenticated', 'test')]), \
                 patch.object(login, 'request', side_effect=[(200, b''), (200, body), (200, b'')]):
                self.assertEqual(login.run_login(), expected)

    def test_missing_credentials_does_not_connect(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(login, 'load_env_file', return_value={}), \
             patch.object(login, 'request') as request:
            self.assertEqual(login.run_login(), 2)
            request.assert_not_called()

    def test_network_failure(self):
        with patch.dict(os.environ, {'WLAN_USER': 'demo', 'WLAN_PWD': 'demo'}), \
             patch.object(login, 'load_env_file', return_value={}), \
             patch.object(login, 'query_authentication_state', return_value=('unknown', 'TimeoutError')), \
             patch.object(login, 'request', side_effect=TimeoutError):
            self.assertEqual(login.run_login(), 7)

    def test_http_cookie_and_form_integration(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header('Set-Cookie', 'session=test; Path=/')
                self.end_headers()
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                requests.append((self.path, self.headers.get('Cookie'), body))
                self.send_response(200)
                self.end_headers()
                if self.path == '/info':
                    payload = ({'success': True, 'data': {'basic': {}}} if any(r[0] == '/login' for r in requests)
                               else {'success': False, 'location': origin + '/ac_portal/needauth.html'})
                else:
                    payload = {'success': True}
                self.wfile.write(json.dumps(payload).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            with patch.dict(os.environ, {'WLAN_USER': 'demo', 'WLAN_PWD': 'demo'}), \
                 patch.object(login, 'load_env_file', return_value={}), \
                 patch.object(login, 'PORTAL_ORIGIN', origin), \
                 patch.object(login, 'INFO_URL', origin + '/info'), \
                 patch.object(login, 'PORTAL_PAGE', origin + '/portal'), \
                 patch.object(login, 'LOGIN_URL', origin + '/login'), \
                 patch.object(login, 'CHECK_JUMP_URL', origin + '/jump'):
                self.assertEqual(login.run_login(), 0)
            self.assertEqual([r[0] for r in requests], ['/info', '/login', '/jump', '/info'])
            self.assertTrue(all(r[1] == 'session=test' for r in requests[1:3]))
            self.assertIsNone(requests[0][1])
            self.assertIsNone(requests[-1][1])
            self.assertIn(b'userName=demo', requests[1][2])
            self.assertNotIn(b'pwd=demo', requests[1][2])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_info_classification(self):
        cases = [
            (200, {'success': True, 'data': {'basic': {}}}, 'authenticated'),
            (200, {'success': False, 'location': 'http://2.2.2.3:80/ac_portal/needauth.html?device=ignored'}, 'auth_required'),
            (200, {'success': False, 'location': 'http://other.example/ac_portal/needauth.html'}, 'unknown'),
            (200, {'success': False, 'location': 'http://2.2.2.3:81/ac_portal/needauth.html'}, 'unknown'),
            (200, {'success': False, 'location': 'https://2.2.2.3/ac_portal/needauth.html'}, 'unknown'),
            (200, {'success': False, 'location': '/ac_portal/needauth.html'}, 'unknown'),
            (200, {'success': False, 'location': 'http://2.2.2.3:bad/ac_portal/needauth.html'}, 'unknown'),
            (200, {'success': False}, 'unknown'),
            (200, {'success': True, 'data': {}}, 'unknown'),
            (200, {'success': 1, 'data': {'basic': {}}}, 'unknown'),
            (200, [], 'unknown'),
            (503, {'success': True, 'data': {'basic': {}}}, 'unknown'),
        ]
        for status, payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(login.authentication_state(status, json.dumps(payload).encode())[0], expected)
        self.assertEqual(login.authentication_state(200, b'not JSON')[0], 'unknown')
        self.assertEqual(login.authentication_state(200, b'\xff')[0], 'unknown')

    def test_query_timeout_and_invalid_json(self):
        with patch.object(login, 'request', side_effect=TimeoutError('private-id')):
            self.assertEqual(login.query_authentication_state(), ('unknown', 'TimeoutError'))
        with patch.object(login, 'request', return_value=(200, b'<html>private-id</html>')):
            self.assertEqual(login.query_authentication_state(), ('unknown', 'invalid_json'))

    def test_online_skips_login(self):
        with patch.dict(os.environ, {'WLAN_USER': 'demo', 'WLAN_PWD': 'secret'}), \
             patch.object(login, 'load_env_file', return_value={}), \
             patch.object(login, 'query_authentication_state', return_value=('authenticated', 'info_basic_present')), \
             patch.object(login, 'request') as request, self.assertLogs(login.LOGGER, level='INFO') as logs:
            self.assertEqual(login.run_login(), 0)
            request.assert_not_called()
        self.assertIn('already_authenticated', '\n'.join(logs.output))
        self.assertIn('action=skip', '\n'.join(logs.output))

    def test_login_recovery_and_unknown_fallback(self):
        for prior in ('auth_required', 'unknown'):
            for post, expected in [('authenticated', 0), ('auth_required', 8), ('unknown', 8)]:
                with self.subTest(prior=prior, post=post), \
                     patch.dict(os.environ, {'WLAN_USER': 'private-user', 'WLAN_PWD': 'private-password'}), \
                     patch.object(login, 'load_env_file', return_value={}), \
                     patch.object(login, 'query_authentication_state', side_effect=[(prior, 'test'), (post, 'test')]), \
                     patch.object(login, 'request', side_effect=[(200, b''), (200, b'{"success":true}'), (200, b'0')]) as request, \
                     self.assertLogs(login.LOGGER, level='INFO') as logs:
                    self.assertEqual(login.run_login(), expected)
                    self.assertEqual(request.call_count, 3)
                output = '\n'.join(logs.output)
                self.assertIn(f'prior_state={prior} action=login', output)
                self.assertIn(f'post_state={post}', output)
                self.assertNotIn('private-user', output)
                self.assertNotIn('private-password', output)
                if expected == 8:
                    self.assertNotIn('Background login request completed successfully', output)


if __name__ == '__main__':
    unittest.main()
