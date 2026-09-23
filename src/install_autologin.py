"""Single-file Windows deployment wizard; payloads are bundled by PyInstaller."""
from pathlib import Path
import getpass
import os
import shutil
import subprocess
import sys
from app_version import VERSION


def payload_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'payload'


def install(payload, target, username, password, runner=subprocess.run):
    if not username or not password or any(c in username + password for c in '\r\n'):
        raise ValueError('账号和密码不能为空或包含换行。')
    target.mkdir(parents=True, exist_ok=True)
    exe = target / 'AutoLogin_SIAS_Headless.exe'
    script = target / 'Install-AutoLoginTask.ps1'
    config = target / '.env'
    files = [exe, script, config]
    previous = {p: p.read_bytes() if p.exists() else None for p in files}
    # Keep credentials out of process arguments and environment variables.
    child_env = dict(os.environ)
    child_env.pop('WLAN_USER', None)
    child_env.pop('WLAN_PWD', None)
    try:
        shutil.copy2(payload / exe.name, exe)
        shutil.copy2(payload / script.name, script)
        config.write_text(f'WLAN_USER={username}\nWLAN_PWD={password}\n', encoding='utf-8')
        result = runner([str(exe), '--check'], cwd=str(target), env=child_env, timeout=90)
        if result.returncode:
            raise RuntimeError(f'登录验证失败（退出码 {result.returncode}），请检查校园网连接、账号及日志。')
    except BaseException:
        for path, content in previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    # Once registration begins, retain installed files even on failure: a task
    # may already reference them. The task script backs up the previous XML.
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = runner([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                     'Bypass', '-File', str(script), '-ExePath', str(exe)],
                    cwd=str(target), timeout=120)
    if result.returncode:
        raise RuntimeError('登录已验证，但自动任务安装失败。文件已保留，请根据上方错误处理后重新运行安装程序。')


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
    target = Path(os.environ['LOCALAPPDATA']) / 'AutoLogin_SIAS'
    print(f'安装目录：{target}')
    print('将安装后台程序，验证登录，并创建或更新 Wi-Fi / 每日自动任务。')
    if (target / '.env').exists():
        print('检测到已有安装，本次输入的账号密码将替换原配置。')
    username = input('校园网账号：').strip()
    password = getpass.getpass('校园网密码（不显示）：')
    install(payload_dir(), target, username, password)
    print('部署完成！后台认证和自动任务已就绪。可删除下载的安装包。')
    print('已有任务的时间计划会保留；新任务默认每天 04:10 运行。')


if __name__ == '__main__':
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
    sys.exit(code)
