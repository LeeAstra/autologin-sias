"""Real Windows task restoration using a unique synthetic task, never the user task."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sias_autologin.platforms.windows import installer
if os.name != 'nt' or not ctypes.windll.shell32.IsUserAnAdmin():
    print('SKIP: actual task recovery requires a Windows administrator')
    sys.exit(1 if os.environ.get('CI') == 'true' else 0)
name='AutoLogin_Test_'+uuid.uuid4().hex
def ps(command):
    result=subprocess.run([installer.powershell_path(),'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf-8',timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result
try:
    for enabled in (True,False):
        ps("$ErrorActionPreference='Stop'; $a=New-ScheduledTaskAction -Execute '"+installer.powershell_path()+"' -Argument '-NoProfile -NonInteractive -Command exit'; $p=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value) -LogonType S4U; Register-ScheduledTask -TaskName '"+name+"' -Action $a -Principal $p -Force | Out-Null" + ("; Disable-ScheduledTask -TaskName '"+name+"' | Out-Null" if not enabled else ''))
        for same in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder); old=root/'old'; old.mkdir(); payload=root/'payload'; payload.mkdir()
                target=old if same else root/'new'
                for filename in ('AutoLogin_SIAS_Headless.exe','Install-AutoLoginTask.ps1'):
                    (old/filename).write_bytes(b'old'); (payload/filename).write_bytes(b'new')
                (old/'.env').write_bytes(b'old-config')
                before=ps("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); Export-ScheduledTask -TaskName '"+name+"'").stdout
                def runner(args,**kwargs):
                    if '--validate-credentials' in args:
                        return subprocess.CompletedProcess(args,0)
                    if '-File' in args:
                        # Simulate a registration that changed the task, then failed verification.
                        ps("$ErrorActionPreference='Stop'; Enable-ScheduledTask -TaskName '"+name+"' | Out-Null")
                        return subprocess.CompletedProcess(args,1)
                    args=list(args); args[-1]=args[-1].replace('AutoLogin_SIAS',name)
                    return subprocess.run(args,**kwargs)
                with patch.dict(os.environ,{'LOCALAPPDATA':str(root)}):
                    try:
                        installer.install(payload,target,'synthetic','synthetic',runner,mode='night',old_target=old)
                    except RuntimeError as error:
                        assert '原文件和任务设置已恢复' in str(error), error
                    else:
                        raise AssertionError('Injected registration failure was accepted')
                after=ps("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); Export-ScheduledTask -TaskName '"+name+"'").stdout
                assert before.strip()==after.strip(), 'Original XML was not restored exactly'
                assert (old/'.env').read_bytes()==b'old-config'
                assert (old/'AutoLogin_SIAS_Headless.exe').read_bytes()==b'old'
                print(f'PASS: real task XML restored; enabled={enabled}; same_directory={same}')
finally:
    ps("$ErrorActionPreference='Stop'; $t=Get-ScheduledTask -TaskName '"+name+"' -ErrorAction SilentlyContinue; if ($t) { Stop-ScheduledTask -InputObject $t; Unregister-ScheduledTask -InputObject $t -Confirm:$false }")
