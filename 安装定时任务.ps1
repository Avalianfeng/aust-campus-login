# 以管理员身份运行：注册「每 5 分钟检测校园网」计划任务
# 用法: powershell -ExecutionPolicy Bypass -File "D:\wifi\aust-campus-login\安装定时任务.ps1"

$TaskName = "AUST-Campus-Login-Watchdog"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $ScriptDir "静默运行.bat"

if (-not (Test-Path $BatPath)) {
    Write-Error "找不到 $BatPath"
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $ScriptDir

# 开机后 1 分钟先跑一次
$BootTrigger = New-ScheduledTaskTrigger -AtStartup
$BootTrigger.Delay = "PT1M"

# 每 5 分钟重复检测（3650 天约 10 年，到期后重新运行本脚本即可）
$RepeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger @($BootTrigger, $RepeatTrigger) `
    -Settings $Settings `
    -Description "安理工校园网断线自动重连（每5分钟 + 开机1分钟后）" `
    -Force

Write-Host "已注册计划任务: $TaskName"
Write-Host "  - 开机 1 分钟后检测一次"
Write-Host "  - 之后每 5 分钟检测一次"
Write-Host "日志: $ScriptDir\logs\campus-login.log"
Write-Host ""
Write-Host "手动测试: python `"$ScriptDir\AutoLogin.py`" --check"
Write-Host "删除任务: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
