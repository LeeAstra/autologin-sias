#Requires -Version 5.1
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..\packaging')
try {
    & $Python -m PyInstaller --noconfirm --distpath dist auto_login_headless.spec
    if ($LASTEXITCODE -ne 0) { throw 'Headless build failed.' }
    & $Python -m PyInstaller --noconfirm --distpath dist auto_login_installer.spec
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
    Get-ChildItem dist\AutoLogin_SIAS_Headless.exe,dist\AutoLogin_SIAS_Installer.exe |
        ForEach-Object { '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name } |
        Set-Content -LiteralPath dist\SHA256SUMS.txt -Encoding ascii
    Write-Output "Installer: $(Join-Path (Get-Location) 'dist\AutoLogin_SIAS_Installer.exe')"
} finally { Pop-Location }
