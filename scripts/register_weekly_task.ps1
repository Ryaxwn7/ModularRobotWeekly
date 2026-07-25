param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [string]$TaskName = "Robotics Weekly Research Agent",
    [string]$Time = "08:30"
)

$scriptPath = Join-Path $ProjectRoot "scripts\run_weekly.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Thursday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Generate a twice-weekly robotics research report." -Force
