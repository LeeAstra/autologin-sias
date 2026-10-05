param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& $Python -m PyInstaller --noconfirm --onefile --console --name AutoLogin_SIAS_Monitor --paths (Join-Path $PSScriptRoot '..\..\..\src') --paths (Join-Path $PSScriptRoot '..\login-diagnostics') --distpath $PSScriptRoot --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'monitor.py')
if ($LASTEXITCODE -ne 0) { throw 'Monitor build failed.' }
$sources = @('monitor.py','..\..\..\src\auto_login_headless.py','..\..\..\src\credentials.py','..\..\..\src\app_version.py','..\login-diagnostics\record_login.py')
$hashes = [ordered]@{}
foreach ($source in $sources) { $hashes[$source] = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $source) -Algorithm SHA256).Hash }
[ordered]@{built_at=[DateTimeOffset]::Now.ToString('o'); sources=$hashes; exe_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'AutoLogin_SIAS_Monitor.exe') -Algorithm SHA256).Hash} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'BUILD-INFO.json') -Encoding UTF8
