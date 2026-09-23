#Requires -Version 5.1
<# Creates or updates the root AutoLogin task. Does not run the login EXE. #>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)] [string]$ExePath,
    [ValidateNotNullOrEmpty()] [string]$SSID = 'UESTC',
    [ValidatePattern('^[^\\/]+$')] [string]$TaskName = 'AutoLogin_SIAS',
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')] [string]$DailyAt = '04:10',
    [string]$ExportOnly
)
$ErrorActionPreference = 'Stop'
Import-Module ScheduledTasks
$exe = Get-Item -LiteralPath $ExePath
if ($exe.PSIsContainer -or $exe.Extension -ne '.exe') { throw 'ExePath must be an existing EXE.' }
if ($SSID.Contains("'") -and $SSID.Contains('"')) { throw 'SSID containing both quote types is not supported by the event XPath filter.' }
$ssidLiteral = if ($SSID.Contains("'")) { '"' + $SSID + '"' } else { "'" + $SSID + "'" }
$channel = 'Microsoft-Windows-WLAN-AutoConfig/Operational'
$query = [xml]('<QueryList><Query Id="0" Path="' + $channel + '"><Select Path="' + $channel + '" /></Query></QueryList>')
$query.SelectSingleNode('/QueryList/Query/Select').InnerText = "*[System[(EventID=8001 or EventID=11005)]] and *[EventData[Data[@Name='SSID']=$ssidLiteral]]"
# Enumerate rather than suppress access errors as if the task did not exist.
$existing = Get-ScheduledTask -TaskPath '\' | Where-Object TaskName -EQ $TaskName
if ($existing) {
    $before = Export-ScheduledTask -TaskName $TaskName -TaskPath '\'
    [xml]$xml = $before
    if (@($xml.Task.Actions.ChildNodes).Count -ne 1 -or -not $xml.Task.Actions.Exec) { throw 'Existing task must have exactly one Exec action.' }
    if ($xml.Task.Principals.Principal.LogonType -notin @('S4U', 'InteractiveToken')) { throw 'Existing task uses an unsupported logon type; update it manually to preserve its credentials.' }
} else {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    [xml]$xml = @"
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>SIAS: selected Wi-Fi connection and daily authentication</Description></RegistrationInfo>
  <Triggers />
  <Principals><Principal id="Author"><UserId>$identity</UserId><LogonType>S4U</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT3M</ExecutionTimeLimit>
    <RestartOnFailure><Interval>PT5M</Interval><Count>3</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author"><Exec><Command /><WorkingDirectory /></Exec></Actions>
</Task>
"@
}
$namespace = $xml.DocumentElement.NamespaceURI
function Add-TextElement($Parent, [string]$Name, [string]$Value) {
    $element = $xml.CreateElement($Name, $namespace)
    $element.InnerText = $Value
    [void]$Parent.AppendChild($element)
}
$triggers = $xml.Task.SelectSingleNode('*[local-name()="Triggers"]')
if (-not $triggers) { throw 'Task has no Triggers container; update it manually.' }
# Replace the WLAN trigger only; keep calendar, one-time, and unrelated triggers.
$wlan = @($triggers.ChildNodes | Where-Object { $_.LocalName -eq 'EventTrigger' -and $_.Subscription -like "*$channel*" })
if ($wlan.Count -gt 1) { throw 'Multiple WLAN triggers found; review them manually before updating.' }
if ($wlan.Count -eq 1) {
    $event = $wlan[0]
    $event.Subscription = $query.OuterXml
    $delay = $event.SelectSingleNode('*[local-name()="Delay"]')
    if ($delay) { $delay.InnerText = 'PT30S' } else { Add-TextElement $event 'Delay' 'PT30S' }
} else {
    $event = $xml.CreateElement('EventTrigger', $namespace)
    Add-TextElement $event 'Enabled' 'true'
    Add-TextElement $event 'Subscription' $query.OuterXml
    Add-TextElement $event 'Delay' 'PT30S'
    [void]$triggers.AppendChild($event)
}
if (-not $existing) {
    $daily = $xml.CreateElement('CalendarTrigger', $namespace)
    Add-TextElement $daily 'StartBoundary' ((Get-Date -Format 'yyyy-MM-dd') + 'T' + $DailyAt + ':00')
    Add-TextElement $daily 'Enabled' 'true'
    $schedule = $xml.CreateElement('ScheduleByDay', $namespace)
    Add-TextElement $schedule 'DaysInterval' '1'
    [void]$daily.AppendChild($schedule)
    [void]$triggers.AppendChild($daily)
} elseif ($PSBoundParameters.ContainsKey('DailyAt')) {
    throw 'DailyAt applies only to new tasks. Existing time triggers are preserved; edit them in Task Scheduler.'
}
$instances = $xml.Task.Settings.SelectSingleNode('*[local-name()="MultipleInstancesPolicy"]')
if ($instances) { $instances.InnerText = 'IgnoreNew' } else { Add-TextElement $xml.Task.Settings 'MultipleInstancesPolicy' 'IgnoreNew' }
$xml.Task.Actions.Exec.Command = $exe.FullName
$xml.Task.Actions.Exec.WorkingDirectory = $exe.DirectoryName
# An old action's arguments may invoke setup or other unintended modes.
if ($xml.Task.Actions.Exec.SelectSingleNode('*[local-name()="Arguments"]')) { throw 'Existing action has arguments; review them manually.' }
if ($ExportOnly) {
    $xml.Save($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ExportOnly))
    Write-Output "Preview saved: $ExportOnly (task not changed)"
    return
}
if (-not $PSCmdlet.ShouldProcess($TaskName, 'Back up and register Wi-Fi/daily task')) { return }
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run PowerShell as administrator using the same Windows account, then repeat this command.' }
if (-not (Get-WinEvent -ListLog $channel).IsEnabled) { throw 'WLAN event log is disabled. Enable it in Event Viewer before installing.' }
if ($existing) {
    $backupDir = Join-Path $env:LOCALAPPDATA 'AutoLogin_SIAS\TaskBackups'
    [void](New-Item -ItemType Directory -Path $backupDir -Force)
    $backup = Join-Path $backupDir ('task-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.xml')
    $before | Set-Content -LiteralPath $backup -Encoding Unicode
    Write-Output "Backup: $backup"
}
Register-ScheduledTask -TaskName $TaskName -TaskPath '\' -Xml $xml.OuterXml -Force | Out-Null
[xml]$registered = Export-ScheduledTask -TaskName $TaskName -TaskPath '\'
if (-not (@($registered.Task.Triggers.EventTrigger) | Where-Object { $_.Subscription -eq $query.OuterXml -and $_.Delay -eq 'PT30S' })) { throw 'Registered event trigger verification failed.' }
Write-Output "Installed: $TaskName. The login program has not been started."
Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath '\' | Select-Object NextRunTime, LastTaskResult
