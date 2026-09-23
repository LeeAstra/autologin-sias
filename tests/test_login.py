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
                self.wfile.write(json.dumps({'success': True}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            with patch.dict(os.environ, {'WLAN_USER': 'demo', 'WLAN_PWD': 'demo'}), \
                 patch.object(login, 'load_env_file', return_value={}), \
                 patch.object(login, 'PORTAL_PAGE', origin + '/portal'), \
                 patch.object(login, 'LOGIN_URL', origin + '/login'), \
                 patch.object(login, 'CHECK_JUMP_URL', origin + '/jump'):
                self.assertEqual(login.run_login(), 0)
            self.assertEqual([r[0] for r in requests], ['/login', '/jump'])
            self.assertTrue(all(r[1] == 'session=test' for r in requests))
            self.assertIn(b'userName=demo', requests[0][2])
            self.assertNotIn(b'pwd=demo', requests[0][2])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
