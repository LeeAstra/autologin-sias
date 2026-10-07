"""Cross-process lock check, including the frozen installer; no installation."""
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
if os.name != 'nt':
    print('SKIP: Windows installer mutex check')
    sys.exit(1 if os.environ.get('CI')=='true' else 0)
env=dict(os.environ, PYTHONPATH=str(root/'src'), PYTHONUTF8='1', __COMPAT_LAYER='RunAsInvoker')
owner=subprocess.Popen([sys.executable,'-c',
    "from sias_autologin.platforms.windows.install_lock import InstallationLock; "
    "lock=InstallationLock(); lock.__enter__(); print('LOCKED',flush=True); input(); lock.__exit__(None,None,None)"],
    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env)
try:
    assert owner.stdout.readline().strip()=='LOCKED', 'Could not acquire fixture installer lock'
    exe=root/'packaging/dist/AutoLogin_SIAS_Installer.exe'
    blocked=subprocess.run([str(exe)],input='\n',capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=60)
    assert blocked.returncode==1,(blocked.returncode,blocked.stdout,blocked.stderr)
    assert '另一个安装器正在运行' in blocked.stdout, blocked.stdout
    assert '安装目录' not in blocked.stdout, 'Competing installer entered state discovery/wizard'
    readonly=subprocess.run([str(exe),'--version'],capture_output=True,env=env,timeout=60)
    assert readonly.returncode==0, 'Read-only version check unexpectedly blocked'
    print('PASS: frozen competing installer exits before discovery; read-only flags remain available')
finally:
    try:
        owner.communicate('\n',timeout=15)
    except subprocess.TimeoutExpired:
        owner.kill(); owner.communicate(timeout=15)
assert owner.returncode==0
released=subprocess.run([sys.executable,'-c',
    "from sias_autologin.platforms.windows.install_lock import InstallationLock; "
    "lock=InstallationLock(); lock.__enter__(); lock.__exit__(None,None,None)"],env=env,timeout=30)
assert released.returncode==0
print('PASS: installer lock released when owner exits')
