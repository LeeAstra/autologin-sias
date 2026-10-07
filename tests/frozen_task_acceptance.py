"""Administrator CI acceptance using a unique task and loopback-only frozen fixture."""
import ctypes
from datetime import datetime, time as day_time
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from sias_autologin.platforms.windows import deployment, tasks
from sias_autologin.runtime.monitor import in_window
from sias_autologin.version import VERSION


def check_isolated_installations(root, work, fixture_exe, configure_response):
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print('SKIP: isolated scheduled installation requires administrator')
        if os.environ.get('CI') == 'true':
            raise AssertionError('Administrator task acceptance is required in CI')
        return
    name = 'AutoLogin_Acceptance_' + uuid.uuid4().hex
    assert name.startswith('AutoLogin_Acceptance_') and name != 'AutoLogin_SIAS'
    area = work / 'task-acceptance'
    area.mkdir()
    payload = area / 'payload'
    payload.mkdir()
    shutil.copy2(fixture_exe, payload / deployment.INSTALL_FILES[0])
    shutil.copy2(root / 'scripts/windows/Install-AutoLoginTask.ps1', payload)

    def ps(command):
        result = subprocess.run([tasks.powershell_path(), '-NoProfile', '-NonInteractive',
                                 '-Command', "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
                                 "$ErrorActionPreference='Stop'; " + command],
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout

    def runner(args, **kwargs):
        args = list(args)
        if args[0].lower().endswith('powershell.exe'):
            if '-File' in args:
                args += ['-TaskName', name]
            else:
                args[-1] = args[-1].replace("'AutoLogin_SIAS'", "'" + name + "'")
                assert "'AutoLogin_SIAS'" not in args[-1]
        return subprocess.run(args, **kwargs)

    def events(target):
        path = target / 'auto_login_headless.log'
        return [json.loads(line.split('Maintenance event: ', 1)[1])
                for line in path.read_text(encoding='utf-8').splitlines()
                if 'Maintenance event: ' in line] if path.exists() else []

    def snapshot_xml():
        return ps("Export-ScheduledTask -TaskPath '\\' -TaskName '" + name + "'").strip()

    def remove_task():
        ps("$t=Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq '" + name + "'; "
           "if ($t) { Stop-ScheduledTask -InputObject $t; "
           "Unregister-ScheduledTask -InputObject $t -Confirm:$false }")

    def install_and_confirm(target, mode, old=None):
        previous = {entry['run_id'] for entry in events(target) if entry['event'] == 'start'}
        configure_response(body=b'{"success":true}', prior='authenticated', post='authenticated')
        deployment.install(payload, target, 'synthetic-user', 'synthetic-password', runner,
                           mode=mode, old_target=old)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            current = events(target)
            fresh = [e for e in current if e['event'] == 'start' and e['run_id'] not in previous]
            if fresh:
                start = fresh[-1]
                assert start['mode'] == mode and start['version'] == VERSION
                run = [e for e in current if e['run_id'] == start['run_id']]
                if mode == 'night' and not in_window(datetime.now(), day_time(2,55), day_time(3,15)):
                    if not any(e['event'] == 'end' for e in run):
                        time.sleep(.2)
                        continue
                    assert run[-1]['reason'] == 'outside_night_window', run
                    assert not any(e['event'] == 'login_result' for e in run)
                else:
                    if not any(e['event'] == 'state' for e in run):
                        time.sleep(.2)
                        continue
                    assert any(e.get('state') == 'authenticated' for e in run)
                xml = snapshot_xml()
                assert str(target / deployment.INSTALL_FILES[0]) in xml
                assert '--maintain ' + mode in xml
                print(f'PASS: isolated frozen scheduled run; mode={mode}; target={target.name}')
                return
            time.sleep(.2)
        raise AssertionError('No fresh scheduled maintenance evidence for ' + str(target))

    try:
        for mode in ('night', 'continuous'):
            target = area / (mode + '-original')
            install_and_confirm(target, mode)
            (target / 'unrelated.txt').write_bytes(b'keep')
            install_and_confirm(target, mode, old=target)
            migrated = area / (mode + '-migrated')
            original_files = {key: (target / key).read_bytes() for key in deployment.INSTALL_FILES}
            install_and_confirm(migrated, mode, old=target)
            for key, content in original_files.items():
                assert (target / key).read_bytes() == content
            assert (target / 'unrelated.txt').read_bytes() == b'keep'
            before_xml = snapshot_xml()
            before_files = {key: (migrated / key).read_bytes() for key in deployment.INSTALL_FILES}
            configure_response(body=b'{"success":false}', prior='authenticated', post='authenticated')
            try:
                deployment.install(payload, migrated, 'rejected-user', 'rejected-password', runner,
                                   mode=mode, old_target=migrated)
            except RuntimeError as exc:
                assert '原文件和任务设置已恢复' in str(exc), exc
            else:
                raise AssertionError('Invalid credentials were accepted')
            assert snapshot_xml() == before_xml
            for key, content in before_files.items():
                assert (migrated / key).read_bytes() == content
            print(f'PASS: isolated real task/files restored after online credential rejection; mode={mode}')

            tasks.control_task('stop', runner)
            ps("[xml]$x=Export-ScheduledTask -TaskPath '\\' -TaskName '" + name + "'; "
               "$x.Task.Actions.Exec.Arguments='--setup'; "
               "Register-ScheduledTask -TaskName '" + name + "' -TaskPath '\\' -Xml $x.OuterXml -Force | Out-Null")
            unsupported_xml = snapshot_xml()
            try:
                deployment.install(payload, area / (mode + '-rejected'), 'synthetic-user',
                                   'synthetic-password', runner, mode=mode, old_target=migrated)
            except RuntimeError as exc:
                assert '未停止任务或替换文件' in str(exc), exc
            else:
                raise AssertionError('Unsupported old task was accepted')
            assert snapshot_xml() == unsupported_xml
            assert not (area / (mode + '-rejected')).exists()
            for key, content in before_files.items():
                assert (migrated / key).read_bytes() == content
            print(f'PASS: unsupported isolated task unchanged before mutation; mode={mode}')
            remove_task()
    finally:
        remove_task()
    print('PASS: real temporary scheduled installation matrix; production task untouched')
