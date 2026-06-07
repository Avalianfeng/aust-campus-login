# 以管理员身份运行：注册「每 5 分钟检测校园网」计划任务（无控制台弹窗）
# 用法: powershell -ExecutionPolicy Bypass -File "D:\wifi\aust-campus-login\安装定时任务.ps1"

$TaskName = "AUST-Campus-Login-Watchdog"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $ScriptDir "AutoLogin.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "找不到 $ScriptPath"
    exit 1
}

# 计划任务用 PowerShell 隐藏窗口执行（比 pythonw 更可靠，且能正确返回退出码）
$RunnerPath = Join-Path $ScriptDir "静默运行.ps1"
if (-not (Test-Path $RunnerPath)) {
    Write-Error "找不到 $RunnerPath"
    exit 1
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunnerPath`"" `
    -WorkingDirectory $ScriptDir

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
    -MultipleInstances IgnoreNew `
    -Hidden

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger @($BootTrigger, $RepeatTrigger) `
    -Settings $Settings `
    -Description "安理工校园网断线自动重连（每5分钟 + 开机1分钟后，无窗口）" `
    -Force | Out-Null

Write-Host "已注册计划任务: $TaskName（后台静默，无黑框）"
Write-Host "  执行方式: powershell -WindowStyle Hidden"
Write-Host "  - 开机 1 分钟后检测一次"
Write-Host "  - 之后每 5 分钟检测一次"
Write-Host "日志: $ScriptDir\logs\campus-login.log"
Write-Host ""
Write-Host "手动测试: python `"$ScriptPath`" --check"
Write-Host "删除任务: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
