import logging
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC))
from sias_autologin.core.portal import PortalClient
from sias_autologin.core.service import ensure_authenticated
import auto_login_headless as legacy


class FakeClient(PortalClient):
    def __init__(self, states):
        super().__init__()
        self.states = iter(states)
        self.calls = []

    def query_state(self):
        return next(self.states), 'synthetic'

    def build_opener(self):
        return object()

    def request(self, opener, url, *, data=None):
        self.calls.append((url, data))
        return 200, b'{"success":true}'


class PortableCoreTests(unittest.TestCase):
    def test_core_import_has_no_cli_or_windows_dependencies(self):
        code = "from sias_autologin.core.service import ensure_authenticated; import sys; assert 'auto_login_headless' not in sys.modules; assert 'sias_autologin.cli' not in sys.modules; assert not any(n.startswith('sias_autologin.platforms') for n in sys.modules)"
        result = subprocess.run([sys.executable, '-c', code], env={**os.environ, 'PYTHONPATH': str(SRC)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_api_uses_explicit_credentials_and_order(self):
        client = FakeClient(['auth_required', 'authenticated'])
        with patch.dict(os.environ, {'WLAN_USER': 'ignored', 'WLAN_PWD': 'ignored'}):
            self.assertEqual(ensure_authenticated('synthetic-user', 'synthetic-password', client=client), 0)
        self.assertEqual([url for url, _ in client.calls], [client.settings.page, client.settings.login_url, client.settings.jump_url])
        self.assertEqual(client.calls[1][1]['userName'], 'synthetic-user')
        self.assertNotEqual(client.calls[1][1]['pwd'], 'synthetic-password')

    def test_online_skip_and_forced_validation(self):
        client = FakeClient(['authenticated'])
        self.assertEqual(ensure_authenticated('synthetic', 'synthetic', client=client), 0)
        self.assertEqual(client.calls, [])
        client = FakeClient(['authenticated', 'authenticated'])
        self.assertEqual(ensure_authenticated('synthetic', 'synthetic', client=client, validate_credentials=True), 0)
        self.assertEqual(len(client.calls), 3)

    def test_config_error_retains_summary_without_exception_details(self):
        with patch.object(legacy, 'load_env_file', side_effect=ValueError('secret-detail')), self.assertLogs(legacy.LOGGER, level=logging.INFO) as logs:
            self.assertEqual(legacy.run_login(), 9)
        output = '\n'.join(logs.output)
        self.assertIn('Authentication summary:', output)
        self.assertIn('exit_code=9', output)
        self.assertNotIn('secret-detail', output)

    def test_package_and_legacy_version_commands_match(self):
        env = {**os.environ, 'PYTHONPATH': str(SRC)}
        package = subprocess.run([sys.executable, '-m', 'sias_autologin', '--version'], env=env, capture_output=True, text=True)
        old = subprocess.run([sys.executable, str(SRC / 'auto_login_headless.py'), '--version'], env=env, capture_output=True, text=True)
        self.assertEqual(package.returncode, 0, package.stderr)
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertEqual(package.stdout, old.stdout)


if __name__ == '__main__':
    unittest.main()
