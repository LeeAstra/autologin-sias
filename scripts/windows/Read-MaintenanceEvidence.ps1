#Requires -Version 5.1
# Parse only structured, per-run events; never infer evidence from legacy text.
function Read-MaintenanceEvidence {
    param([Parameter(Mandatory=$true)][string]$LogPath,
          [Parameter(Mandatory=$true)][datetime]$LastRun,
          [string]$Mode, [string]$TaskState = 'Unknown')
    $result = [ordered]@{ evidence_status='unconfirmed'; reason='no_current_run';
        run_id=$null; started_at=$null; ended_at=$null; mode=$null; version=$null;
        observed_logout=$null; authentication_submitted=$null; recovery_confirmed=$null; events=@() }
    $records = @()
    foreach ($path in @(($LogPath+'.2'), ($LogPath+'.1'), $LogPath)) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
            if ($line -notmatch 'Maintenance event: (.+)$') { continue }
            try {
                $event = $Matches[1] | ConvertFrom-Json
                if ($event.schema -ne 1 -or $event.run_id -notmatch '^[a-f0-9]{32}$' -or
                    $event.event -notin @('start','state','login_result','end','duplicate')) { continue }
                [void][DateTimeOffset]::Parse($event.timestamp)
                $records += $event
            } catch { continue }
        }
    }
    $latest = @($records | Where-Object { $_.event -in @('start','duplicate') } | Select-Object -Last 1)
    if ($latest.Count -ne 1) { return [pscustomobject]$result }
    $begin = $latest[0]
    $delta = ([DateTimeOffset]::Parse($begin.timestamp) - [DateTimeOffset]$LastRun).TotalSeconds
    if ($delta -lt 0 -or $delta -gt 120 -or $LastRun.Year -lt 2000) {
        $result.reason='task_run_not_matched'; return [pscustomobject]$result
    }
    if ($begin.mode -ne $Mode) { $result.reason='mode_mismatch'; return [pscustomobject]$result }
    if ($begin.event -eq 'duplicate') { $result.reason='duplicate_skipped'; return [pscustomobject]$result }
    if ($records[-1].run_id -ne $begin.run_id) { $result.reason='latest_run_boundary_missing'; return [pscustomobject]$result }
    $run = @($records | Where-Object { $_.run_id -eq $begin.run_id })
    $result.run_id=$begin.run_id; $result.started_at=$begin.timestamp
    $result.mode=$begin.mode; $result.version=$begin.version
    $result.events=@($run | ForEach-Object {
        [ordered]@{ timestamp=$_.timestamp; event=$_.event; state=$_.state;
            previous=$_.previous; exit_code=$_.exit_code; submitted=$_.submitted;
            confirmed=$_.confirmed; reason=$_.reason }
    })
    $ends=@($run | Where-Object { $_.event -eq 'end' })
    if ($ends.Count -gt 1) { $result.reason='invalid_run_boundary'; return [pscustomobject]$result }
    if ($ends.Count -eq 1) {
        $result.ended_at=$ends[0].timestamp
        if ($ends[0].reason -eq 'interrupted_or_error' -or $run[-1].event -ne 'end') {
            $result.reason='incomplete_run'; return [pscustomobject]$result
        }
        $result.evidence_status='complete'
    } elseif ($TaskState -eq 'Running') {
        $result.evidence_status='running'
    } else {
        $result.reason='missing_end'; return [pscustomobject]$result
    }
    $result.reason='matched_current_run'
    $result.observed_logout=$false
    $seenOnline=$false
    foreach ($entry in $run) {
        if ($entry.event -ne 'state') { continue }
        if ($entry.state -eq 'authenticated') { $seenOnline=$true }
        if ($entry.state -eq 'auth_required' -and $seenOnline) { $result.observed_logout=$true }
    }
    $logins=@($run | Where-Object { $_.event -eq 'login_result' })
    if (@($logins | Where-Object { $null -eq $_.submitted -or $null -eq $_.confirmed }).Count -eq 0) {
        $result.authentication_submitted=@($logins | Where-Object { $_.submitted -eq $true }).Count -gt 0
        $result.recovery_confirmed=@($logins | Where-Object { $_.confirmed -eq $true -and $_.exit_code -eq 0 }).Count -gt 0
        $seenRequired=$false
        foreach ($entry in $run) {
            if ($entry.event -ne 'state') { continue }
            if ($entry.state -eq 'auth_required') { $seenRequired=$true }
            if ($seenRequired -and $entry.state -eq 'authenticated') { $result.recovery_confirmed=$true }
        }
    } else { $result.evidence_status='unconfirmed'; $result.reason='submission_not_recorded' }
    return [pscustomobject]$result
}
