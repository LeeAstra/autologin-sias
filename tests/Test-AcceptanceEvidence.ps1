# Synthetic logs only; no actual task or network changes.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\scripts\windows\Read-MaintenanceEvidence.ps1')
$testRoot=Join-Path ([IO.Path]::GetTempPath()) ('sias-evidence-'+[guid]::NewGuid())
[void](New-Item -ItemType Directory -Path $testRoot)
$log=Join-Path $testRoot 'fixture.log'
function Assert($Condition,$Message) { if (-not $Condition) { throw $Message } }
function Event($Id,$Type,$Stamp,$Values=@{}) {
    $record=@{schema=1;run_id=$Id;event=$Type;timestamp=$Stamp;mode='night';version='fixture'}
    foreach ($key in $Values.Keys) { $record[$key]=$Values[$key] }
    'log | INFO | Maintenance event: '+($record | ConvertTo-Json -Compress)
}
$old='a'*32; $current='b'*32; $duplicate='c'*32
$t='2026-10-07T03:00:00+08:00'
$u='2026-10-07T12:00:00+08:00'
try {
    $historical=@((Event $old start $t),
        (Event $old state $t @{previous=$null;state='authenticated'}),
        (Event $old state $t @{previous='authenticated';state='unknown'}),
        (Event $old state $t @{previous='unknown';state='auth_required'}),
        (Event $old login_result $t @{exit_code=0;submitted=$true;confirmed=$true}), (Event $old end $t @{reason='outside_night_window'}))
    $latest=@((Event $current start $u), (Event $current end $u @{reason='outside_night_window'}))
    @($historical+$latest) | Set-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night
    Assert ($result.evidence_status -eq 'complete') 'Current run not identified.'
    Assert (-not $result.observed_logout -and -not $result.authentication_submitted -and -not $result.recovery_confirmed) 'Old success leaked into current evidence.'
    Assert ($result.run_id -eq $current -and $result.events[0].timestamp -eq $u) 'Run ID or timestamps lost.'
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode continuous
    Assert ($result.evidence_status -eq 'unconfirmed' -and $null -eq $result.recovery_confirmed) 'Mode mismatch accepted.'
    (Event $duplicate duplicate $u) | Add-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night
    Assert ($result.reason -eq 'duplicate_skipped') 'Duplicate invocation reused previous success.'
    # Rotation: start and result in .1, end in current file form one complete run.
    $historical[0..4] | Set-Content -LiteralPath ($log+'.1') -Encoding UTF8
    $historical[5] | Set-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($t).LocalDateTime) -Mode night
    Assert ($result.recovery_confirmed -eq $true -and $result.observed_logout -eq $true) 'Rotated run not joined.'
    Remove-Item -LiteralPath ($log+'.1')
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($t).LocalDateTime) -Mode night
    Assert ($result.evidence_status -eq 'unconfirmed') 'Missing start accepted.'
    (Event $current start $u) | Set-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night -TaskState Ready
    Assert ($result.reason -eq 'missing_end') 'Incomplete stopped run accepted.'
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night -TaskState Running
    Assert ($result.evidence_status -eq 'running') 'Active run evidence missing.'
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($t).LocalDateTime) -Mode night -TaskState Running
    Assert ($result.reason -eq 'task_run_not_matched') 'Different task run accepted.'
    # A newer run whose start has rotated away must not reuse an older start.
    (Event $duplicate state $u @{state='auth_required'}) | Add-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night -TaskState Running
    Assert ($result.reason -eq 'latest_run_boundary_missing') 'Missing latest start reused old run.'
    @((Event $current start $u), (Event $current end $u @{reason='interrupted_or_error'})) | Set-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night
    Assert ($result.evidence_status -eq 'unconfirmed' -and $null -eq $result.recovery_confirmed) 'Interrupted run accepted.'
    @((Event $current start $u), (Event $current state $u @{state='auth_required'}),
      (Event $current login_result $u @{exit_code=0;submitted=$false;confirmed=$true}),
      (Event $current end $u @{reason='outside_night_window'})) | Set-Content -LiteralPath $log -Encoding UTF8
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime) -Mode night
    Assert ($result.recovery_confirmed -and -not $result.authentication_submitted) 'Recovery confused with credential submission.'
    $result=Read-MaintenanceEvidence -LogPath $log -LastRun ([DateTimeOffset]::Parse($u).LocalDateTime.AddSeconds(1)) -Mode night
    Assert ($result.reason -eq 'task_run_not_matched') 'A previous fast run was accepted for a later trigger.'
    Write-Output 'Acceptance evidence fixtures passed.'
} finally {
    $resolved=[IO.Path]::GetFullPath($testRoot)
    $prefix=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if ($resolved.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -like 'sias-evidence-*') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
