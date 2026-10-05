import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import monitor


class MonitorTests(unittest.TestCase):
    def test_route_and_info_rules(self):
        self.assertEqual(monitor.route('http://2.2.2.3:80/ac_portal/proxy.html?mac=example'), 'auth_required')
        self.assertEqual(monitor.route('http://2.2.2.3/homepage/index.html?_FLAG=1'), 'authenticated')
        self.assertEqual(monitor.route('http://other.example/homepage/index.html'), 'unknown')
        self.assertEqual(monitor.info_state(200, {'success': True}), 'unknown')
        self.assertEqual(monitor.info_state(200, {'success': True, 'data': None}), 'unknown')
        self.assertEqual(monitor.info_state(200, {'success': False, 'msg': 'temporary failure'}), 'unknown')
        self.assertEqual(monitor.combine('authenticated', 'auth_required'), 'unknown')
        self.assertEqual(monitor.combine('auth_required', 'unknown'), 'auth_required')

    def test_info_only_accepts_verified_needauth_path(self):
        for location, expected in [('http://2.2.2.3:80/ac_portal/needauth.html?x=ignored','auth_required'),
                                   ('http://2.2.2.3/ac_portal/proxy.html','unknown'),
                                   ('http://2.2.2.3/ac_portal/template/pc.html','unknown'),
                                   ('http://other.example/ac_portal/needauth.html','unknown'),
                                   ('http://2.2.2.3:bad/ac_portal/needauth.html','unknown')]:
            with self.subTest(location=location):
                self.assertEqual(monitor.info_state(200, {'success':False,'location':location}), expected)
        self.assertEqual(monitor.route('http://2.2.2.3:bad/ac_portal/proxy.html'),'unknown')

    def test_observed_loss_count_recovery_and_censoring(self):
        tracker = monitor.Tracker()
        tracker.observe('auth_required', 'initial')
        self.assertFalse(tracker.active['observed_loss'])
        tracker.observe('authenticated', 'online')
        tracker.observe('auth_required', 'lost')
        tracker.observe('auth_required', 'still-lost')
        tracker.observe('unknown', 'uncertain')
        self.assertEqual(len(tracker.events), 2)
        self.assertTrue(tracker.active['observed_loss'])
        tracker.observe('wrong_network', 'switched')
        self.assertEqual(tracker.events[-1]['censored_at'], 'switched')
        tracker.observe('auth_required', 'return-offline')
        self.assertFalse(tracker.active['observed_loss'])
        tracker.observe('observation_gap', 'sleep')
        self.assertIsNone(tracker.active)

    def test_actual_saved_offline_and_online_evidence(self):
        # Local evidence is optional; synthetic rules above remain portable.
        folder = Path(__file__).resolve().parents[1] / 'login-diagnostics' / 'results'
        fixtures = [('20261004-143404-462698.json', 'auth_required'),
                    ('20261004-143424-870094.json', 'authenticated')]
        if not all((folder / name).is_file() for name, _ in fixtures):
            self.skipTest('Local captured evidence is unavailable')
        for name, expected in fixtures:
            report = json.loads((folder / name).read_text(encoding='utf-8'))
            info = next(request for request in report['requests'] if request['phase'] == 'before'
                        and request['url'].endswith('/homepage/info.php'))
            self.assertEqual(monitor.info_state(info['status'], info['response_body']), expected)
            self.assertEqual(monitor.root_state(report['before']['root_navigation']), expected)
            self.assertEqual(monitor.root_state(report['after']['root_navigation']), 'authenticated')

    def test_loop_skips_online_and_unknown_then_records_one_recovery(self):
        class Session:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        class Response:
            status = 200
            headers = {'Set-Cookie': 'AUTHSESSID=test-session'}
            def geturl(self):
                return monitor.login.LOGIN_URL
            def read(self):
                return b'{"success":true}'
            def close(self):
                pass
        requests = []
        class Opener:
            def open(self, request, timeout=None):
                requests.append(request)
                return Response()
        observations = [{'state': state} for state in (
            'authenticated', 'unknown', 'auth_required', 'authenticated', 'authenticated')]
        observations.append(KeyboardInterrupt())
        roots = [{'http_status': 200, 'final_url': url, 'http_redirects': []}
                 for url in ('http://2.2.2.3/homepage/index.html?_FLAG=1',
                             'http://2.2.2.3/unrecognized',
                             'http://2.2.2.3:80/ac_portal/proxy.html')]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'results'
            env = Path(directory) / '.env'
            env.write_text('WLAN_USER=test-account\nWLAN_PWD=test-password\n', encoding='utf-8')
            argv = ['monitor', '--continuous', '--env', str(env), '--output', str(out)]
            with patch.object(sys, 'argv', argv), patch.object(monitor, 'WindowsSession', Session), \
                 patch.object(monitor, 'target_wifi', return_value='target_network'), \
                 patch.object(monitor, 'query_info', side_effect=observations), \
                 patch.object(monitor.diag, 'observe_root', side_effect=roots), \
                 patch.object(monitor, 'verify_internet', return_value={'state': 'online'}), \
                 patch.object(monitor.login, 'build_portal_opener', return_value=Opener()), \
                 patch.object(monitor.login, 'query_authentication_state', side_effect=[('auth_required', 'test'), ('authenticated', 'test')]), \
                 patch.dict(monitor.os.environ, {'WLAN_USER': '', 'WLAN_PWD': ''}), \
                 patch.object(monitor.time, 'sleep'):
                self.assertEqual(monitor.main(), 0)
            self.assertEqual(len(requests), 3)
            report = json.loads(next(out.glob('run-*.json')).read_text(encoding='utf-8'))
            self.assertEqual(len(report['events']), 1)
            event = report['events'][0]
            self.assertTrue(event['observed_loss'])
            self.assertTrue(event['recovered_at'])
            self.assertEqual(len(event['attempts']), 1)
            self.assertEqual(event['attempts'][0]['portal_after'], 'authenticated')
            self.assertEqual(report['unknown_samples'], 1)
            self.assertEqual(report['stop_reason'], 'keyboard_interrupt')
            detail = next(out.glob('login-*.json')).read_text(encoding='utf-8')
            self.assertNotIn('test-password', detail)
            self.assertNotIn('test-account', detail)
            monitor.summary(out)


if __name__ == '__main__':
    unittest.main()
