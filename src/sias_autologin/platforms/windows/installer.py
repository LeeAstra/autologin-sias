"""Single-file Windows deployment wizard; payloads are bundled by PyInstaller."""
from pathlib import Path
import getpass
import json
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ...version import VERSION
from ...config import write_env_file, load_env_file, find_env_path


def payload_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[4])) / 'payload'


def replace_file(path, writer):
    """Stage beside the target; retry transient Windows locks without truncation."""
    descriptor, name = tempfile.mkstemp(prefix='.autologin-', dir=path.parent)
    os.close(descriptor)
    staged = Path(name)
    try:
        writer(staged)
        for attempt in range(20):
            try:
                try:
                    os.replace(staged, path)
                except OSError as exc:
                    if os.name != 'nt' or getattr(exc, 'winerror', None) != 17:
                        raise
                    # EFS can reject a same-directory rename as cross-device.
                    # Permit Windows' copy/move fallback only for this staged pair.
                    if staged.parent.resolve() != path.parent.resolve():
                        raise
                    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                    kernel.MoveFileExW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
                    kernel.MoveFileExW.restype = ctypes.c_bool
                    if not kernel.MoveFileExW(str(staged), str(path), 0x1 | 0x2 | 0x8):
                        raise ctypes.WinError(ctypes.get_last_error())
                return
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.2)
    finally:
        staged.unlink(missing_ok=True)


def install(payload, target, username, password, runner=subprocess.run, *, mode=None, old_target=None):
    if not username or not password or any(c in username + password for c in '\r\n'):
        raise ValueError('账号和密码不能为空或包含换行。')
    if mode not in (None, 'continuous', 'night'):
        raise ValueError('Unsupported maintenance mode')
    target = Path(target).resolve()
    old_target = Path(old_target).resolve() if old_target else None
    target.mkdir(parents=True, exist_ok=True)
    old_snapshot = {}
    if old_target and old_target != target:
        for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1', '.env'):
            source = old_target / name
            if source.is_file():
                old_snapshot[name] = source.read_bytes()
    if mode:
        backup = Path(os.environ['LOCALAPPDATA']) / 'AutoLogin_SIAS_Backups' / (time.strftime('%Y%m%d-%H%M%S') + '-' + str(time.time_ns()))
        backup.mkdir(parents=True, exist_ok=False)
        for name, content in old_snapshot.items():
            (backup / name).write_bytes(content)
        for name in ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1', '.env'):
            source = target / name
            if source.is_file():
                (backup / ('target-' + name)).write_bytes(source.read_bytes())
        print(f'文件备份：{backup}')
    exe = target / 'AutoLogin_SIAS_Headless.exe'
    script = target / 'Install-AutoLoginTask.ps1'
    config = target / '.env'
    files = [exe, script, config]
    previous = {p: p.read_bytes() if p.exists() else None for p in files}
    changed = []
    # Keep credentials out of process arguments and environment variables.
    child_env = dict(os.environ)
    child_env.pop('WLAN_USER', None)
    child_env.pop('WLAN_PWD', None)
    snapshot = snapshot_task(runner) if mode else None
    if snapshot and snapshot['exists']:
        (backup / 'task-before.xml').write_text(snapshot['xml'], encoding='utf-8')
    registration_started = False
    phase = '停止旧任务'
    try:
        if mode:
            control_task('stop', runner)
        phase = '部署文件'
        for path in (exe, script):
            if previous[path] != (payload / path.name).read_bytes():
                changed.append(path)
                replace_file(path, lambda staged: shutil.copy2(payload / path.name, staged))
        changed.append(config)
        replace_file(config, lambda staged: write_env_file(staged, username, password))
        phase = '验证凭据'
        result = runner([str(exe), '--validate-credentials'], cwd=str(target), env=child_env, timeout=90)
        if result.returncode:
            raise RuntimeError(f'登录验证失败（退出码 {result.returncode}），请检查校园网连接、账号及日志。')
        powershell = powershell_path()
        phase = '注册计划任务'
        registration_started = True
        result = runner([powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                         'Bypass', '-File', str(script), '-ExePath', str(exe)] + (['-Mode', mode] if mode else []),
                        cwd=str(target), timeout=120)
        if result.returncode:
            raise RuntimeError('自动任务注册或验证失败。')
        if mode:
            phase = '启动计划任务'
            control_task('start', runner)
    except BaseException as original:
        # Legacy single-operation callers retain files if registration may have
        # referenced them. Maintenance upgrades restore the complete transaction.
        if not mode and registration_started:
            raise RuntimeError('自动任务安装失败，文件已保留，请检查后重试。') from original
        try:
            if mode:
                control_task('stop', runner)
            for path in reversed(changed):
                content = previous[path]
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    replace_file(path, lambda staged: staged.write_bytes(content))
            if mode:
                restore_task(snapshot, backup, runner)
        except BaseException as recovery:
            raise RuntimeError(f'安装失败且自动恢复未完成。请保留文件并使用备份检查恢复：{backup if mode else target}') from recovery
        if not mode:
            raise
        raise RuntimeError(f'安装未完成（阶段：{phase}）；原文件和任务设置已恢复。请检查失败原因后重试。') from original

    if mode:
        # Do not remove the source until task registration succeeded, and never
        # touch other files or remove the directory itself.
        for name, content in old_snapshot.items():
            source = old_target / name
            try:
                if source.is_file() and source.read_bytes() == content:
                    source.unlink()
            except OSError:
                print(f'旧文件暂未清理，可稍后手动处理：{source}')


def powershell_path():
    return str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')


def control_task(action, runner=subprocess.run, *, required=True):
    command = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq 'AutoLogin_SIAS'; if ($task) { "
    command += ("Disable-ScheduledTask -InputObject $task | Out-Null; Stop-ScheduledTask -InputObject $task; $deadline=(Get-Date).AddSeconds(15); while ((Get-ScheduledTask -TaskPath '\\' -TaskName 'AutoLogin_SIAS').State -eq 'Running') { if ((Get-Date) -gt $deadline) { throw 'Task did not stop' }; Start-Sleep -Milliseconds 200 }" if action == 'stop' else "Enable-ScheduledTask -InputObject $task | Out-Null; Start-ScheduledTask -InputObject $task") + ' }'
    result = runner([powershell_path(), '-NoProfile', '-NonInteractive', '-Command', command], timeout=30)
    if result.returncode and required:
        raise RuntimeError('无法停止或启动已有任务，请检查权限和任务状态。')


def snapshot_task(runner=subprocess.run):
    """Capture settings before disabling; malformed output must fail closed."""
    command = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq 'AutoLogin_SIAS'; if ($task) { @{exists=$true; xml=(Export-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\'); running=($task.State -eq 'Running')} | ConvertTo-Json -Compress } else { @{exists=$false} | ConvertTo-Json -Compress }"
    result = runner([powershell_path(), '-NoProfile', '-NonInteractive', '-Command', command],
                    capture_output=True, text=True, encoding='utf-8', timeout=30)
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
    # The XML contains the original Enabled flag, principal and all conditions.
    if snapshot['exists']:
        xml_path = str(backup / 'task-before.xml').replace("'", "''")
        command = "$ErrorActionPreference='Stop'; $xml=Get-Content -LiteralPath '" + xml_path + "' -Raw -Encoding UTF8; Register-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\' -Xml $xml -Force | Out-Null"
        if snapshot['running']:
            command += "; Start-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\\'"
    else:
        command = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq 'AutoLogin_SIAS'; if ($task) { Unregister-ScheduledTask -InputObject $task -Confirm:$false }"
    result = runner([powershell_path(), '-NoProfile', '-NonInteractive', '-Command', command], timeout=30)
    if result.returncode:
        raise RuntimeError('原计划任务恢复失败。')


def existing_directory():
    command = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq 'AutoLogin_SIAS'; if ($task) { if (@($task.Actions).Count -ne 1) { throw 'Unsupported task actions' }; $id=$task.Principal.UserId; if ($id -notlike 'S-1-*') { $id=([Security.Principal.NTAccount]::new($id)).Translate([Security.Principal.SecurityIdentifier]).Value }; if ($id -ne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) { throw 'Task belongs to another account' }; $task.Actions.Execute }"
    result = subprocess.run([powershell_path(), '-NoProfile', '-NonInteractive', '-Command', command], capture_output=True, text=True, encoding='utf-8', timeout=30)
    if result.returncode:
        raise RuntimeError('无法读取旧任务，请使用同一 Windows 账户的管理员权限运行。')
    value = result.stdout.strip().strip('"')
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute() or path.name.lower() != 'autologin_sias_headless.exe':
        raise RuntimeError('已有任务不是可识别的自动登录程序，请先人工检查。')
    return path.resolve().parent


def main():
    if sys.argv[1:] == ['--version']:
        print(f'AutoLogin SIAS Installer {VERSION}')
        return
    if sys.argv[1:] == ['--verify-payload']:
        payload = payload_dir()
        if not all((payload / name).is_file() for name in
                   ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1')):
            raise RuntimeError('安装包缺少必要文件。')
        print(f'Payload OK: {VERSION}')
        return
    if sys.argv[1:]:
        raise ValueError('不支持的参数。')
    print(f'AutoLogin SIAS {VERSION} 一键部署\n请连接 UESTC 校园网后继续。')
    print('请使用自己的 Windows 管理员账户；不要使用其他账户的凭据提权。')
    old_target = existing_directory()
    default_target = Path(os.environ['LOCALAPPDATA']) / 'AutoLogin_SIAS'
    location = input(f'安装目录（回车使用 {default_target}）：').strip().strip('"')
    target = Path(location).expanduser() if location else default_target
    if not target.is_absolute():
        raise ValueError('请选择绝对安装路径。')
    print('① UESTC 持续维护：每30秒检测，断开后退出')
    print('② 夜间时段维护：02:55～03:15，每5秒检测')
    choice = input('选择模式 [1/2，默认2]：').strip() or '2'
    if choice not in ('1','2'):
        raise ValueError('模式只能选择1或2。')
    mode = 'continuous' if choice == '1' else 'night'
    config_dir = target if (target / '.env').is_file() else old_target
    config_path = find_env_path(config_dir) if config_dir else None
    config = load_env_file(config_path) if config_path else {}
    reuse = bool(config.get('WLAN_USER') and config.get('WLAN_PWD')) and input('检测到旧配置，保留账号密码？[Y/n]：').strip().lower() != 'n'
    username = config['WLAN_USER'] if reuse else input('校园网账号：').strip()
    password = config['WLAN_PWD'] if reuse else getpass.getpass('校园网密码（不显示）：')
    print(f'将安装至 {target}，更新 AutoLogin_SIAS 任务为 {mode} 模式。')
    print('旧程序和配置先备份；迁移成功后清理旧目录中的三个已识别文件，其他文件保留。')
    if input('确认安装？[Y/n]：').strip().lower() == 'n':
        return
    install(payload_dir(), target, username, password, mode=mode, old_target=old_target)
    print('部署完成。任务已更新并启动；夜间模式在时段外会直接退出。')



def entrypoint():
    code = 0
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print(f'部署未完成：{exc}')
        code = 1
    if len(sys.argv) == 1:
        try:
            input('按回车键关闭窗口……')
        except (EOFError, KeyboardInterrupt):
            pass
    return code
