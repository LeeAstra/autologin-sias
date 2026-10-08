# Read-only collector regression: continuous tasks have no NextRunTime.
$ErrorActionPreference = 'Stop'
function Get-ScheduledTask {
    param($TaskName, $TaskPath)
    [pscustomobject]@{ Actions=@([pscustomobject]@{Execute=(Join-Path $env:TEMP 'sias-collector-missing.exe'); Arguments='--maintain continuous'}); Settings=[pscustomobject]@{Enabled=$true}; State='Running' }
}
function Get-ScheduledTaskInfo {
    param($InputObject)
    [pscustomobject]@{LastRunTime=[datetime]'2026-10-07T23:32:52'; NextRunTime=$global:AutoLoginCollectorTestNextTime; LastTaskResult=267009; NumberOfMissedRuns=0}
}
$collector=Join-Path $PSScriptRoot '..\scripts\windows\Get-AcceptanceStatus.ps1'
foreach ($expected in @($null, [datetime]'2026-10-08T02:55:00')) {
    $global:AutoLoginCollectorTestNextTime=$expected
    $result=(& $collector | Out-String) | ConvertFrom-Json
    if ($null -eq $expected) {
        if ($null -ne $result.next_run) { throw 'No scheduled time must remain JSON null.' }
    } elseif ($result.next_run -ne '2026-10-08 02:55:00') { throw 'Scheduled time formatting changed.' }
    if ($result.task_state -ne 'Running' -or $result.arguments -ne '--maintain continuous') { throw 'Task data changed.' }
}
Write-Output 'Acceptance collector null and scheduled time regressions passed.'
Remove-Variable -Name AutoLoginCollectorTestNextTime -Scope Global
