param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [string]$TaskName = "Robotics Daily Research Agent",
    [string]$Time = "08:30"
)

$scriptPath = Join-Path $ProjectRoot "scripts\run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Collect and summarize robotics research progress." -Force

