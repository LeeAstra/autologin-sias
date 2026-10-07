import sys
from pathlib import Path
from datetime import datetime, timedelta, time
import logging
import tempfile
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sias_autologin.runtime.monitor import maintain, in_window
from sias_autologin.platforms.windows import installer

class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        snapshot = patch.object(installer, 'snapshot_task', return_value={'exists': False})
        snapshot.start()
        self.addCleanup(snapshot.stop)

    def test_window_cross_midnight_and_end_exclusion(self):
        self.assertTrue(in_window(datetime(2026,1,1,0,10), time(23), time(1)))
        self.assertFalse(in_window(datetime(2026,1,1,3,15), time(2,55), time(3,15)))

    def test_night_unknown_skip_recovery_and_retry_spacing(self):
        tick = [datetime(2026,1,1,3,14,35)]
        states = iter(['unknown','authenticated','auth_required','auth_required','auth_required'])
        calls = []
        def sleep(seconds): tick[0] += timedelta(seconds=seconds)
        result = maintain(mode='night', network=lambda:'target_network', query=lambda:(next(states),'synthetic'),
                          login=lambda:calls.append(tick[0]) or 7, logger=logging.getLogger('test'),
                          clock=lambda:tick[0], monotonic=lambda:tick[0].timestamp(), sleep=sleep)
        self.assertEqual(result,0)
        self.assertEqual(len(calls),1)
        self.assertEqual(tick[0].time(),time(3,15))

    def test_disconnect_before_login_prevents_authentication(self):
        networks=iter(['target_network','wrong_network'])
        calls=[]
        maintain(mode='continuous',network=lambda:next(networks),query=lambda:('auth_required','synthetic'),
                 login=lambda:calls.append(1),logger=logging.getLogger('test'),
                 sleep=lambda _:self.fail('A verified departure must exit immediately'))
        self.assertEqual(calls,[])

    def test_outside_window_does_not_query_network(self):
        def forbidden(): raise AssertionError('must not run')
        self.assertEqual(maintain(mode='night',network=forbidden,query=forbidden,login=forbidden,
                        logger=logging.getLogger('test'),clock=lambda:datetime(2026,1,1,12)),0)

    def test_migration_backs_up_and_only_cleans_identified_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); old=root/'old'; payload=root/'payload'; target=root/'new'
            old.mkdir(); payload.mkdir()
            for name in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                (old/name).write_bytes(b'old'); (payload/name).write_bytes(b'new')
            (old/'.env').write_bytes(b'old-config'); (old/'unrelated.txt').write_bytes(b'keep')
            calls=[]
            def runner(args,**kwargs): calls.append(args); return SimpleNamespace(returncode=0)
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root),'SystemRoot':'C:/Windows'}):
                installer.install(payload,target,'synthetic','synthetic',runner,mode='night',old_target=old)
            self.assertEqual([p.name for p in old.iterdir()],['unrelated.txt'])
            backup=next((root/'AutoLogin_SIAS_Backups').iterdir())
            self.assertEqual((backup/'.env').read_bytes(),b'old-config')
            self.assertIn('-Mode',calls[-2]); self.assertEqual(calls[-2][-1],'night')

    def test_failed_task_registration_does_not_clean_old_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); old=root/'old'; payload=root/'payload'; old.mkdir(); payload.mkdir()
            for name in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                (old/name).write_bytes(b'old'); (payload/name).write_bytes(b'new')
            results=iter([0,0,1])
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root),'SystemRoot':'C:/Windows'}), self.assertRaises(RuntimeError):
                installer.install(payload,root/'new','synthetic','synthetic',lambda *a,**k:SimpleNamespace(returncode=next(results)),mode='night',old_target=old)
            self.assertEqual((old/'AutoLogin_SIAS_Headless.exe').read_bytes(),b'old')

    def test_wizard_passes_custom_directory_and_continuous_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'custom-install'
            with patch.object(installer, 'existing_directory', return_value=None), \
                 patch.object(installer, 'install') as deploy, \
                 patch('builtins.input', side_effect=[str(target),'1','synthetic','y']), \
                 patch.object(installer.getpass, 'getpass', return_value='synthetic'), \
                 patch.object(sys, 'argv', ['installer']), \
                 patch.dict(os.environ, {'LOCALAPPDATA': directory}):
                installer.main()
            self.assertEqual(deploy.call_args.args[1], target)
            self.assertEqual(deploy.call_args.kwargs['mode'], 'continuous')

    @unittest.skipUnless(os.name == 'nt', 'Windows EFS move fallback')
    def test_windows_same_directory_cross_device_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'fixture'
            target.write_bytes(b'old')
            error = OSError('synthetic cross-device error')
            error.winerror = 17
            with patch.object(installer.os, 'replace', side_effect=error):
                installer.replace_file(target, lambda staged: staged.write_bytes(b'new'))
            self.assertEqual(target.read_bytes(), b'new')

if __name__ == '__main__': unittest.main()
