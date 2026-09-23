# Exercise XML generation only; mocks prohibit changes to system tasks.
$ErrorActionPreference = 'Stop'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('autologin-test-' + [guid]::NewGuid())
[void](New-Item -ItemType Directory $testRoot)
function Import-Module { param($Name) }
function Get-ScheduledTask { param($TaskPath) if ($global:AutoLoginTestExistingXml) { [pscustomobject]@{TaskName='AutoLogin_SIAS'} } }
function Export-ScheduledTask { param($TaskName,$TaskPath) $global:AutoLoginTestExistingXml }
function Register-ScheduledTask { throw 'Tests must never register a task.' }
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
try {
    $exe = Join-Path $testRoot 'background.exe'
    Set-Content -LiteralPath $exe -Value 'fixture'
    $preview = Join-Path $testRoot 'preview.xml'
    $installer = Join-Path $PSScriptRoot '..\scripts\Install-AutoLoginTask.ps1'
    $global:AutoLoginTestExistingXml = $null
    & $installer -ExePath $exe -ExportOnly $preview
    [xml]$xml = Get-Content -LiteralPath $preview -Raw
    Assert ($xml.Task.Triggers.CalendarTrigger.StartBoundary -like '*T04:10:00') 'Daily trigger missing.'
    Assert ($xml.Task.Triggers.EventTrigger.Delay -eq 'PT30S') 'Event delay missing.'
    Assert ($xml.Task.Triggers.EventTrigger.Subscription -match '11005') 'Fallback WLAN event missing.'
    Assert ($xml.Task.Settings.MultipleInstancesPolicy -eq 'IgnoreNew') 'Instance policy incorrect.'
    Assert ($xml.Task.Settings.WakeToRun -eq 'false') 'Unexpected wake setting.'
    # An existing action may omit the optional WorkingDirectory element.
    [void]$xml.Task.Actions.Exec.RemoveChild($xml.Task.Actions.Exec.SelectSingleNode('*[local-name()="WorkingDirectory"]'))
    $xml.Task.Triggers.CalendarTrigger.StartBoundary = '2026-01-01T05:30:00'
    $xml.Task.Settings.WakeToRun = 'true'
    $global:AutoLoginTestExistingXml = $xml.OuterXml
    & $installer -ExePath $exe -ExportOnly $preview
    [xml]$updated = Get-Content -LiteralPath $preview -Raw
    Assert ($updated.Task.Triggers.CalendarTrigger.StartBoundary -eq '2026-01-01T05:30:00') 'Existing schedule changed.'
    Assert ($updated.Task.Settings.WakeToRun -eq 'true') 'Existing power settings changed.'
    Assert ($updated.Task.Actions.Exec.WorkingDirectory -eq $testRoot) 'Working directory not repaired.'
    $failed = $false
    try { & $installer -ExePath $exe -DailyAt '06:00' -ExportOnly $preview } catch { $failed = $true }
    Assert $failed 'Existing schedule must reject DailyAt override.'
    Write-Output 'Task XML preview tests passed (no tasks registered).'
} finally {
    # Only remove the unique, verified fixture directory created above.
    $resolved = [IO.Path]::GetFullPath($testRoot)
    $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolved.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path $resolved -Leaf) -like 'autologin-test-*') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
