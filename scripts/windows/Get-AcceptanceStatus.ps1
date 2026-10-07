#Requires -Version 5.1
# Read-only; emits a fixed summary without credentials or raw logs.
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName 'AutoLogin_SIAS' -TaskPath '\'
$info = Get-ScheduledTaskInfo -InputObject $task
$exe = $task.Actions[0].Execute
$version = if (Test-Path -LiteralPath $exe) { (& $exe --version | Out-String).Trim() } else { 'MISSING_EXE' }
$log = Join-Path (Split-Path -Parent $exe) 'auto_login_headless.log'
$events = @()
if (Test-Path -LiteralPath $log) {
    $events = @(Get-Content -LiteralPath $log -Tail 300 -Encoding UTF8 |
        Where-Object { $_ -match 'Maintenance (started:|state:|login result:|stopped:)' } |
        Select-Object -Last 12 |
        ForEach-Object { if ($_ -match '(Maintenance .*)') { $Matches[1] } })
}
$result = [ordered]@{
    schema = 'autologin-acceptance-v1'
    version = $version
    task_enabled = [bool]$task.Settings.Enabled
    task_state = [string]$task.State
    arguments = [string]$task.Actions[0].Arguments
    last_result = [long]$info.LastTaskResult
    missed_runs = [int]$info.NumberOfMissedRuns
    last_run = $info.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss')
    next_run = $info.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss')
    recent_maintenance_events = $events
}
$result | ConvertTo-Json -Depth 4
