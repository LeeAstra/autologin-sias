"""Windows file deployment transaction, rollback and bounded migration cleanup."""
from pathlib import Path
import ctypes
import os
import shutil
import subprocess
import tempfile
import time
from ...config import write_env_file
from .install_lock import InstallationLock
from . import tasks

INSTALL_FILES = ('AutoLogin_SIAS_Headless.exe', 'Install-AutoLoginTask.ps1', '.env')


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


def check_install_directory(target):
    """S4U scheduled tasks cannot reliably read EFS-encrypted installations."""
    if os.name != 'nt':
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    kernel.GetFileAttributesW.restype = ctypes.c_uint32
    attributes = kernel.GetFileAttributesW(str(target))
    if attributes == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    if attributes & 0x4000:
        raise ValueError('安装目录启用了 EFS 加密，计划任务可能无法读取。请选择未加密的本地目录。')


def install(payload, target, username, password, runner=subprocess.run, *, mode=None, old_target=None):
    with InstallationLock():
        return _install(payload, target, username, password, runner, mode=mode, old_target=old_target)


def _install(payload, target, username, password, runner=subprocess.run, *, mode=None, old_target=None):
    if not username or not password or any(c in username + password for c in '\r\n'):
        raise ValueError('账号和密码不能为空或包含换行。')
    if mode not in (None, 'continuous', 'night'):
        raise ValueError('Unsupported maintenance mode')
    payload = Path(payload).resolve()
    tasks.preflight_task(payload / INSTALL_FILES[1], payload / INSTALL_FILES[0], runner, mode=mode)
    snapshot = tasks.snapshot_task(runner) if mode else None
    target = Path(target).resolve()
    old_target = Path(old_target).resolve() if old_target else None
    target.mkdir(parents=True, exist_ok=True)
    check_install_directory(target)
    old_snapshot = {}
    if old_target and old_target != target:
        for name in INSTALL_FILES:
            source = old_target / name
            if source.is_file():
                old_snapshot[name] = source.read_bytes()
    exe, script, config = (target / name for name in INSTALL_FILES)
    previous = {path: path.read_bytes() if path.exists() else None
                for path in (exe, script, config)}
    backup = _save_backup(previous, old_snapshot) if mode else None
    changed = []
    # Keep credentials out of process arguments and environment variables.
    child_env = dict(os.environ)
    child_env.pop('WLAN_USER', None)
    child_env.pop('WLAN_PWD', None)
    if snapshot and snapshot['exists']:
        (backup / 'task-before.xml').write_text(snapshot['xml'], encoding='utf-8')
    registration_started = False
    phase = '停止旧任务'
    try:
        if mode:
            tasks.control_task('stop', runner)
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
        powershell = tasks.powershell_path()
        phase = '注册计划任务'
        registration_started = True
        result = runner([powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                         'Bypass', '-File', str(script), '-ExePath', str(exe)] + (['-Mode', mode] if mode else []),
                        cwd=str(target), timeout=120)
        if result.returncode:
            raise RuntimeError('自动任务注册或验证失败。')
        if mode:
            phase = '启动计划任务'
            tasks.control_task('start', runner)
    except BaseException as original:
        # Legacy single-operation callers retain files if registration may have
        # referenced them. Maintenance upgrades restore the complete transaction.
        if not mode and registration_started:
            raise RuntimeError('自动任务安装失败，文件已保留，请检查后重试。') from original
        try:
            if mode:
                tasks.control_task('stop', runner)
            _restore_files(previous, changed)
            if mode:
                tasks.restore_task(snapshot, backup, runner)
        except BaseException as recovery:
            raise RuntimeError(f'安装失败且自动恢复未完成。请保留文件并使用备份检查恢复：{backup if mode else target}') from recovery
        if not mode:
            raise
        raise RuntimeError(f'安装未完成（阶段：{phase}）；原文件和任务设置已恢复。请检查失败原因后重试。') from original

    if mode and old_snapshot:
        # Start-ScheduledTask acknowledges a request, not a successful process.
        # Night mode can legitimately finish immediately outside its window.
        print(f'新任务已请求启动，尚未确认本轮维护运行；旧文件保留在：{old_target}。'
              '确认新目录运行正常后再处理旧文件；不要手动运行旧程序。')


def _save_backup(previous, old_snapshot):
    backup = (Path(os.environ['LOCALAPPDATA']) / 'AutoLogin_SIAS_Backups' /
              (time.strftime('%Y%m%d-%H%M%S') + '-' + str(time.time_ns())))
    backup.mkdir(parents=True, exist_ok=False)
    for name, content in old_snapshot.items():
        (backup / name).write_bytes(content)
    for path, content in previous.items():
        if content is not None:
            (backup / ('target-' + path.name)).write_bytes(content)
    print(f'文件备份：{backup}')
    return backup


def _restore_files(previous, changed):
    for path in reversed(changed):
        content = previous[path]
        if content is None:
            path.unlink(missing_ok=True)
        else:
            replace_file(path, lambda staged: staged.write_bytes(content))
