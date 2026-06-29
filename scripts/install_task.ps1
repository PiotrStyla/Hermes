# Registers (or replaces) a Windows Scheduled Task that runs the Hermes board
# meeting every day at 10:00 local time. Survives reboots and catches up on a
# missed run when the machine wakes (StartWhenAvailable). No admin required —
# it registers under the current user.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot "run_board_meeting.ps1"
$TaskName = "HermesBoardMeeting"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`"" `
    -WorkingDirectory $Root

$trigger = New-ScheduledTaskTrigger -Daily -At 10:00

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Runs the Hermes AI executive board meeting daily at 10:00." `
    -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' (daily 10:00, catch-up enabled)."
