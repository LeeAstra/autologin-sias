"""Read-only artifact checks and frozen CLI smoke tests; never install a task."""
import os
from pathlib import Path
import subprocess
import tempfile
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[1]
dist = root / 'packaging' / 'dist'
bundle = dist / 'AutoLogin_SIAS_Installer.exe'
archive = CArchiveReader(str(bundle))
for name, source in {
    'AutoLogin_SIAS_Headless.exe': dist / 'AutoLogin_SIAS_Headless.exe',
    'Install-AutoLoginTask.ps1': root / 'scripts' / 'Install-AutoLoginTask.ps1',
}.items():
    key = next(k for k in archive.toc if k.replace('\\', '/') == 'payload/' + name)
    assert archive.extract(key) == source.read_bytes(), f'Payload mismatch: {name}'
assert not any('libcrypto' in k.lower() for k in archive.toc), 'Unused installer crypto dependency'
env = dict(os.environ, __COMPAT_LAYER='RunAsInvoker')
# Suppress the installer's UAC manifest only for read-only CLI checks.
for flag in ('--version', '--verify-payload'):
    result = subprocess.run([str(bundle), flag], env=env, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    print(result.stdout.decode(errors='replace').strip())
with tempfile.TemporaryDirectory() as directory:
    result = subprocess.run([str(dist / 'AutoLogin_SIAS_Headless.exe'), '--version'],
                            cwd=directory, timeout=60)
    assert result.returncode == 0
print(f'Bundle verified: {bundle.stat().st_size:,} bytes')
