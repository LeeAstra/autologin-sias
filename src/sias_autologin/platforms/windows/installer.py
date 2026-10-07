"""Windows installer UI and compatibility exports; deployment is separate."""
from pathlib import Path
import getpass
import os
import sys
from ...version import VERSION
from ...config import load_env_file, find_env_path
from .install_lock import InstallationLock
from .deployment import install, replace_file, check_install_directory
from .tasks import powershell_path, control_task, snapshot_task, restore_task, existing_directory


def payload_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[4])) / 'payload'


def main():
    if sys.argv[1:] in (['--version'], ['--verify-payload']):
        return _main()
    with InstallationLock():
        return _main()


def _main():
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
    print('旧程序和配置先备份；迁移时保留旧文件，待确认新目录维护正常后再处理。')
    if input('确认安装？[Y/n]：').strip().lower() == 'n':
        return
    install(payload_dir(), target, username, password, mode=mode, old_target=old_target)
    print('部署完成。任务已更新并请求启动；启动请求成功不代表维护已运行。夜间模式在时段外会正常退出。')



def entrypoint():
    # Keep redirected wizard output readable on Chinese and English Windows.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
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
