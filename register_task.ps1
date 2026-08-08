$action  = New-ScheduledTaskAction -Execute "C:\Users\munag\.gemini\antigravity\scratch\financial-assistant\start_bot.bat"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "FinancialAssistantBot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
Write-Host "SUCCESS: Bot registered to auto-start on login."
