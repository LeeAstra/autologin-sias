#Requires -Version 5.1
# Read-only; outputs only current-run evidence, not credentials or legacy logs.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Read-MaintenanceEvidence.ps1')
$task = Get-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\'
$info = Get-ScheduledTaskInfo -InputObject $task
$exe = $task.Actions[0].Execute
$mode = if ($task.Actions[0].Arguments -match '--maintain\s+(night|continuous)') { $Matches[1] } else { 'unknown' }
$log = Join-Path (Split-Path -Parent $exe) 'auto_login_headless.log'
$evidence = Read-MaintenanceEvidence -LogPath $log -LastRun $info.LastRunTime -Mode $mode -TaskState ([string]$task.State)
$result = [ordered]@{
    schema = 'autologin-acceptance-v2'
    version = if ($evidence.version) { $evidence.version } else { 'UNKNOWN_VERSION' }
    executable_present = [bool](Test-Path -LiteralPath $exe)
    task_enabled = [bool]$task.Settings.Enabled
    task_state = [string]$task.State
    arguments = [string]$task.Actions[0].Arguments
    last_result = [long]$info.LastTaskResult
    missed_runs = [int]$info.NumberOfMissedRuns
    last_run = $info.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss')
    next_run = if ($null -ne $info.NextRunTime) { $info.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss') } else { $null }
    evidence = $evidence
}
$result | ConvertTo-Json -Depth 6
