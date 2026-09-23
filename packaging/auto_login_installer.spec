# Build the headless spec first, into packaging/dist.
from pathlib import Path

root = Path(SPECPATH)
payload = root / 'dist' / 'AutoLogin_SIAS_Headless.exe'
if not payload.is_file():
    raise SystemExit('Build auto_login_headless.spec first (default dist directory).')
a = Analysis([str(root.parent / 'src' / 'install_autologin.py')],
             pathex=[], binaries=[],
             datas=[(str(payload), 'payload'),
                    (str(root.parent / 'scripts' / 'Install-AutoLoginTask.ps1'), 'payload')],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             # The deployment wizard performs no TLS or cryptographic operations.
             # Leave the embedded headless program's TLS dependencies intact.
             excludes=['_hashlib'], noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='AutoLogin_SIAS_Installer', console=True, uac_admin=True,
          debug=False, strip=False, upx=True)
