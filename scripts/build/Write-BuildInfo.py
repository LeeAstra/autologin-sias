"""Record build provenance without local paths, credentials or runtime logs."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import PyInstaller
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'src'))
from sias_autologin.version import VERSION


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + root.as_posix(), *args],
                                   cwd=root, text=True, encoding='utf-8').strip()


inputs = sorted([*root.glob('src/**/*.py'), *root.glob('packaging/*.spec'),
                 root / 'scripts/windows/Install-AutoLoginTask.ps1'])
fingerprint = hashlib.sha256()
for path in inputs:
    fingerprint.update(path.relative_to(root).as_posix().encode() + b'\0')
    fingerprint.update(hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).digest())
artifacts = {}
for name in ('AutoLogin_SIAS_Headless.exe', 'AutoLogin_SIAS_Installer.exe'):
    path = root / 'packaging/dist' / name
    compiled_version = CArchiveReader(str(path)).open_embedded_archive('PYZ.pyz').extract('sias_autologin.version')
    if VERSION not in compiled_version.co_consts:
        raise RuntimeError('Compiled artifact version differs from source: ' + name)
    artifacts[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'bytes': path.stat().st_size}
info = {'schema': 'autologin-build-v1', 'version': VERSION, 'commit': git('rev-parse', 'HEAD'),
        'source_tree': git('rev-parse', 'HEAD^{tree}'), 'source_dirty': bool(git('status', '--porcelain')),
        'source_fingerprint': fingerprint.hexdigest(), 'python': platform.python_version(),
        'pyinstaller': PyInstaller.__version__, 'platform': platform.system() + '-' + platform.machine(),
        'artifacts': artifacts}
(root / 'packaging/dist/BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
print('Build provenance: ' + info['commit'] + '; source_dirty=' + str(info['source_dirty']))
