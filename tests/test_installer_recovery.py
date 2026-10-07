"""Failure matrix for maintenance deployment; no real tasks are changed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sias_autologin.platforms.windows import installer, deployment

class RecoveryTests(unittest.TestCase):
    def exercise(self, failure, *, exists=True, running=False, same_directory=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); old = root/'old'; old.mkdir()
            target = old if same_directory else root/'new'
            payload = root/'payload'; payload.mkdir()
            for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1'):
                (old/name).write_bytes(b'old'); (payload/name).write_bytes(b'new')
            (old/'.env').write_bytes(b'old-config')
            (old/'unrelated.txt').write_bytes(b'keep')
            snapshot = {'exists': exists, 'xml': '<Task>original</Task>', 'running': running}
            calls = []; failed = False
            def runner(args, **kwargs):
                nonlocal failed
                calls.append(args)
                if kwargs.get('capture_output'):
                    return SimpleNamespace(returncode=0, stdout=json.dumps(snapshot))
                phase = ('validate' if '--validate-credentials' in args else
                         'register' if '-File' in args else
                         'stop' if 'Disable-ScheduledTask' in args[-1] else
                         'start' if 'Enable-ScheduledTask' in args[-1] else 'restore')
                if phase == failure and not failed:
                    failed = True
                    if failure == 'register-timeout':
                        raise subprocess.TimeoutExpired(args, 120)
                    return SimpleNamespace(returncode=1)
                if failure == 'register-timeout' and phase == 'register' and not failed:
                    failed = True
                    raise subprocess.TimeoutExpired(args, 120)
                return SimpleNamespace(returncode=0)
            with patch.dict(os.environ, {'LOCALAPPDATA': str(root), 'SystemRoot': 'C:/Windows'}):
                with self.assertRaisesRegex(RuntimeError, '原文件和任务设置已恢复'):
                    installer.install(payload, target, 'synthetic', 'synthetic', runner,
                                      mode='night', old_target=old if exists else None)
            self.assertTrue(failed)
            for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1'):
                self.assertEqual((old/name).read_bytes(), b'old')
            self.assertEqual((old/'.env').read_bytes(), b'old-config')
            self.assertEqual((old/'unrelated.txt').read_bytes(), b'keep')
            if not same_directory:
                self.assertEqual(list(target.iterdir()), [])
            restoration = calls[-1][-1]
            if exists:
                self.assertIn('Register-ScheduledTask', restoration)
                self.assertEqual('Start-ScheduledTask' in restoration, running)
                backup = next((root/'AutoLogin_SIAS_Backups').iterdir())
                self.assertEqual((backup/'task-before.xml').read_text(encoding='utf-8'), snapshot['xml'])
            else:
                self.assertIn('Unregister-ScheduledTask', restoration)

    def test_failures_restore_files_and_original_task(self):
        for failure in ('stop', 'validate', 'register', 'register-timeout', 'start'):
            for same in (False, True):
                with self.subTest(failure=failure, same_directory=same):
                    self.exercise(failure, same_directory=same)

    def test_running_task_is_restarted_after_recovery(self):
        self.exercise('register', running=True)

    def test_failed_fresh_install_removes_new_task(self):
        self.exercise('start', exists=False)

    @unittest.skipUnless(os.name == 'nt', 'Windows EFS installation check')
    def test_encrypted_install_directory_is_rejected_before_task_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); payload=root/'payload'; payload.mkdir()
            for name in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                (payload/name).write_bytes(b'fixture')
            with patch.object(deployment.ctypes, 'WinDLL') as dll, patch.dict(os.environ,{'LOCALAPPDATA':folder}):
                dll.return_value.GetFileAttributesW.return_value=0x4000
                def forbidden(*args, **kwargs): raise AssertionError('Task must remain untouched')
                with self.assertRaisesRegex(ValueError,'EFS'):
                    installer.install(payload,root/'new','synthetic','synthetic',forbidden,mode='night')
            self.assertEqual(list((root/'new').iterdir()),[])

    def test_snapshot_rejects_invalid_output(self):
        for output in ('', '{}', '{"exists":true}', '{"exists":"false"}'):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                installer.snapshot_task(lambda *a, **k: SimpleNamespace(returncode=0, stdout=output))

    def test_snapshot_failure_does_not_stop_task(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); payload=root/'payload'; payload.mkdir(); calls=[]
            for name in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                (payload/name).write_bytes(b'fixture')
            def runner(args, **kwargs):
                calls.append(args)
                return SimpleNamespace(returncode=1)
            with patch.dict(os.environ, {'LOCALAPPDATA': folder, 'SystemRoot':'C:/Windows'}):
                with self.assertRaises(RuntimeError):
                    installer.install(payload,root/'new','synthetic','synthetic',runner,mode='night')
            self.assertEqual(len(calls),1)
            self.assertNotIn('Disable-ScheduledTask', calls[0][-1])

    def test_restore_preserves_disabled_xml_and_does_not_enable_or_start(self):
        with tempfile.TemporaryDirectory() as folder:
            backup=Path(folder); xml='<Task><Settings><Enabled>false</Enabled></Settings></Task>'
            (backup/'task-before.xml').write_text(xml,encoding='utf-8')
            calls=[]
            installer.restore_task({'exists':True,'xml':xml,'running':False},backup,
                                   lambda args, **kw: calls.append(args) or SimpleNamespace(returncode=0))
            self.assertNotIn('Enable-ScheduledTask',calls[0][-1])
            self.assertNotIn('Start-ScheduledTask',calls[0][-1])

    def test_recovery_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); payload=root/'payload'; payload.mkdir()
            for name in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                (payload/name).write_bytes(b'fixture')
            def runner(args,**kw):
                if kw.get('capture_output'):
                    return SimpleNamespace(returncode=0,stdout='{"exists":false}')
                return SimpleNamespace(returncode=1 if '-File' in args or 'Unregister-ScheduledTask' in args[-1] else 0)
            with patch.dict(os.environ,{'LOCALAPPDATA':folder,'SystemRoot':'C:/Windows'}):
                with self.assertRaisesRegex(RuntimeError,'自动恢复未完成'):
                    installer.install(payload,root/'new','synthetic','synthetic',runner,mode='night')

if __name__ == '__main__': unittest.main()
