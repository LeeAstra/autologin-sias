"""Read-only artifact checks and frozen CLI smoke tests; never install a task."""
import os
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import tempfile
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[1]
dist = root / 'packaging' / 'dist'
info=json.loads((dist/'BUILD-INFO.json').read_text(encoding='utf-8'))
head=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'rev-parse','HEAD'],cwd=root,text=True).strip()
assert info['commit']==head and not info['source_dirty'], 'Artifact source is not the clean tested commit'
sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (dist/'SHA256SUMS.txt').read_text().splitlines()}
for name, recorded in info['artifacts'].items():
    actual=hashlib.sha256((dist/name).read_bytes()).hexdigest()
    assert recorded['sha256']==sums[name]==actual, 'Artifact checksum mismatch: '+name
print('Clean build provenance and SHA256 verified: '+head)
bundle = dist / 'AutoLogin_SIAS_Installer.exe'
archive = CArchiveReader(str(bundle))
for artifact in (bundle, dist/'AutoLogin_SIAS_Headless.exe'):
    product=CArchiveReader(str(artifact))
    assert not any('fixture_wlan' in entry.lower() or 'WlanPolicyFixture' in entry
                   for entry in product.toc), 'Test-only WLAN hook entered product artifact'
for name, source in {
    'AutoLogin_SIAS_Headless.exe': dist / 'AutoLogin_SIAS_Headless.exe',
    'Install-AutoLoginTask.ps1': root / 'scripts' / 'windows' / 'Install-AutoLoginTask.ps1',
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

# Outside-window maintenance smoke test: no network or authentication is run.
start = (datetime.now() + timedelta(hours=2)).strftime('%H:%M')
end = (datetime.now() + timedelta(hours=2, minutes=1)).strftime('%H:%M')
result = subprocess.run([str(dist / 'AutoLogin_SIAS_Headless.exe'), '--maintain', 'night',
                         '--window-start', start, '--window-end', end], timeout=60)
assert result.returncode == 0, 'Frozen maintenance entry failed'
print('Frozen maintenance outside-window exit verified')
