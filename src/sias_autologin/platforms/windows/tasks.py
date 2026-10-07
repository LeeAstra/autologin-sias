"""Windows task discovery, snapshots and recovery; no deployment or UI."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
from textwrap import dedent

_FIND_TASK = "Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq 'AutoLogin_SIAS'"
_STOP = """
    Disable-ScheduledTask -InputObject $task | Out-Null
    Stop-ScheduledTask -InputObject $task
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-ScheduledTask -TaskPath '\\' -TaskName 'AutoLogin_SIAS').State -eq 'Running') {
        if ((Get-Date) -gt $deadline) { throw 'Task did not stop' }
        Start-Sleep -Milliseconds 200
    }
"""
_START = """
    Enable-ScheduledTask -InputObject $task | Out-Null
    Start-ScheduledTask -InputObject $task
"""
_SNAPSHOT = """
    if ($task) {
        @{exists=$true; xml=(Export-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\');
          running=($task.State -eq 'Running')} | ConvertTo-Json -Compress
    } else { @{exists=$false} | ConvertTo-Json -Compress }
"""
_DIRECTORY = """
    if ($task) {
        if (@($task.Actions).Count -ne 1) { throw 'Unsupported task actions' }
        $id = $task.Principal.UserId
        if ($id -notlike 'S-1-*') {
            $id = ([Security.Principal.NTAccount]::new($id)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
        if ($id -ne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) {
            throw 'Task belongs to another account'
        }
        $task.Actions.Execute
    }
"""

def powershell_path():
    return str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')

def _run(script, runner, *, capture=False):
    command = ("[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
               "$ErrorActionPreference='Stop';\n" + dedent(script).strip())
    options = dict(capture_output=True, text=True, encoding='utf-8') if capture else {}
    return runner([powershell_path(), '-NoProfile', '-NonInteractive', '-Command', command],
                  timeout=30, **options)

def control_task(action, runner=subprocess.run, *, required=True):
    script = "$task = " + _FIND_TASK + "; if ($task) {\n" + (_STOP if action == 'stop' else _START) + "\n}"
    result = _run(script, runner)
    if result.returncode and required:
        raise RuntimeError('无法停止或启动已有任务，请检查权限和任务状态。')

def snapshot_task(runner=subprocess.run):
    """Capture the complete original XML before disabling the task."""
    result = _run('$task = ' + _FIND_TASK + ';\n' + _SNAPSHOT, runner, capture=True)
    if result.returncode:
        raise RuntimeError('无法备份原任务，尚未修改安装。')
    try:
        snapshot = json.loads(result.stdout)
        if not isinstance(snapshot, dict) or type(snapshot.get('exists')) is not bool:
            raise ValueError('Invalid task snapshot')
        if snapshot['exists'] and (not isinstance(snapshot.get('xml'), str) or
                                   not snapshot['xml'].strip() or type(snapshot.get('running')) is not bool):
            raise ValueError('Incomplete task snapshot')
        return snapshot
    except (ValueError, TypeError) as exc:
        raise RuntimeError('任务备份输出异常，尚未修改安装。') from exc

def restore_task(snapshot, backup, runner=subprocess.run):
    # Restore the original XML including disabled status, account and conditions.
    if snapshot['exists']:
        xml_path = str(backup / 'task-before.xml').replace("'", "''")
        script = ("$xml = Get-Content -LiteralPath '" + xml_path + "' -Raw -Encoding UTF8;\n"
                  "Register-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\' "
                  "-Xml $xml -Force | Out-Null")
        if snapshot['running']:
            script += "; Start-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\'"
    else:
        script = ('$task = ' + _FIND_TASK +
                  '; if ($task) { Unregister-ScheduledTask -InputObject $task -Confirm:$false }')
    if _run(script, runner).returncode:
        raise RuntimeError('原计划任务恢复失败。')

def existing_directory():
    script = '$task = ' + _FIND_TASK + ';\n' + _DIRECTORY
    result = _run(script, subprocess.run, capture=True)
    if result.returncode:
        raise RuntimeError('无法读取旧任务，请使用同一 Windows 账户的管理员权限运行。')
    value = result.stdout.strip().strip('"')
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute() or path.name.lower() != 'autologin_sias_headless.exe':
        raise RuntimeError('已有任务不是可识别的自动登录程序，请先人工检查。')
    return path.resolve().parent

def preflight_task(script, exe, runner=subprocess.run, *, mode=None):
    """Use registration's own XML checks before stopping tasks or replacing files."""
    with tempfile.TemporaryDirectory(prefix='autologin-preflight-') as folder:
        command = [powershell_path(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                   'Bypass', '-File', str(script), '-ExePath', str(exe),
                   '-ExportOnly', str(Path(folder) / 'preview.xml')]
        if mode:
            command += ['-Mode', mode]
        if runner(command, timeout=30).returncode:
            raise RuntimeError('旧任务或安装载荷检查未通过；未停止任务或替换文件。请检查上方错误。')
