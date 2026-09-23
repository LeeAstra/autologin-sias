import importlib.util
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'src/install_autologin.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.payload = Path(self.temp.name) / 'payload'
        self.target = Path(self.temp.name) / 'installed'
        self.payload.mkdir()
        self.target.mkdir()
        for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1'):
            (self.payload / name).write_bytes(b'new')

    def test_success_has_no_password_arguments_and_clears_overrides(self):
        calls = []
        def run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0)
        with patch.dict(os.environ, {'WLAN_PWD': 'stale', 'SystemRoot': 'C:\\Windows'}):
            installer.install(self.payload, self.target, 'user', 'secret', run)
        self.assertEqual(len(calls), 2)
        self.assertNotIn('WLAN_PWD', calls[0][1]['env'])
        self.assertNotIn('secret', str(calls))
        self.assertEqual((self.target / '.env').read_text(), 'WLAN_USER=user\nWLAN_PWD=secret\n')

    def test_login_failure_restores_old_installation(self):
        for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1', '.env'):
            (self.target / name).write_bytes(b'old')
        with self.assertRaises(RuntimeError):
            installer.install(self.payload, self.target, 'user', 'secret', lambda *a, **k: SimpleNamespace(returncode=5))
        for path in self.target.iterdir():
            self.assertEqual(path.read_bytes(), b'old')

    def test_task_failure_keeps_installed_payload(self):
        results = iter([0, 1])
        with patch.dict(os.environ, {'SystemRoot': 'C:\\Windows'}), self.assertRaises(RuntimeError):
            installer.install(self.payload, self.target, 'user', 'secret', lambda *a, **k: SimpleNamespace(returncode=next(results)))
        self.assertTrue((self.target / '.env').exists())
        self.assertEqual((self.target / 'AutoLogin_SIAS_Headless.exe').read_bytes(), b'new')

    def test_invalid_input_does_not_write(self):
        with self.assertRaises(ValueError):
            installer.install(self.payload, self.target, 'user\nother', 'secret')
        self.assertEqual(list(self.target.iterdir()), [])

    def test_interrupt_during_login_restores_old_config(self):
        (self.target / '.env').write_bytes(b'old')
        def interrupted(*args, **kwargs):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            installer.install(self.payload, self.target, 'user', 'secret', interrupted)
        self.assertEqual((self.target / '.env').read_bytes(), b'old')
        self.assertFalse((self.target / 'AutoLogin_SIAS_Headless.exe').exists())


if __name__ == '__main__':
    unittest.main()
