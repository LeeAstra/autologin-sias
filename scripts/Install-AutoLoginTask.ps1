#Requires -Version 5.1
<# Creates or updates the root AutoLogin task. Does not run the login EXE. #>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)] [string]$ExePath,
    [ValidateNotNullOrEmpty()] [string]$SSID = 'UESTC',
    [ValidatePattern('^[^\\/]+$')] [string]$TaskName = 'AutoLogin_SIAS',
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')] [string]$DailyAt = '04:10',
    [ValidateSet('continuous','night')] [string]$Mode,
    [string]$ExportOnly
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'windows\Install-AutoLoginTask.ps1') @PSBoundParameters
