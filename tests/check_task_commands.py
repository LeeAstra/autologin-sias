"""Parse generated installer commands with Windows PowerShell without executing them."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sias_autologin.platforms.windows import tasks

commands = []
def capture(args, **kwargs):
    commands.append(args[-1])
    return SimpleNamespace(returncode=0, stdout=json.dumps({'exists': False}))

tasks.control_task('stop', capture)
tasks.control_task('start', capture)
tasks.snapshot_task(capture)
for running in (False, True):
    tasks.restore_task({'exists': True, 'running': running}, Path("C:/验收/O'Brien"), capture)
tasks.restore_task({'exists': False}, None, capture)
def capture_discovery(args, **kwargs):
    commands.append(args[-1])
    return SimpleNamespace(returncode=0, stdout='')

with patch.object(tasks.subprocess, 'run', side_effect=capture_discovery):
    assert tasks.existing_directory() is None

with tempfile.TemporaryDirectory() as folder:
    validator = Path(folder) / 'parse.ps1'
    validator.write_text("""param([string]$Source)
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($Source, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }
""", encoding='utf-8-sig')
    for index, command in enumerate(commands):
        source = Path(folder) / f'command-{index}.ps1'
        source.write_text(command, encoding='utf-8-sig')
        subprocess.run([tasks.powershell_path(), '-NoProfile', '-NonInteractive', '-File', str(validator), '-Source', str(source)], check=True)
print(f'PASS: {len(commands)} generated task commands parse in Windows PowerShell; no task changed')
