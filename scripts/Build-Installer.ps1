#Requires -Version 5.1
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build\Build-Installer.ps1') @PSBoundParameters
