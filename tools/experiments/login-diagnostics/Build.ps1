param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& $Python -m PyInstaller --noconfirm --clean --onefile --console --name AutoLogin_SIAS_Diagnostic --paths (Join-Path $PSScriptRoot '..\..\..\src') --distpath $PSScriptRoot --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'record_login.py')
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic build failed.' }
