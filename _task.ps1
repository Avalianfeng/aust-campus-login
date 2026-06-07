# 计划任务管理（仅供 AutoLogin.py 内部调用，用户请用 管理.bat）
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("enable", "disable", "register", "status")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$TaskName = "AUST-Campus-Login-Watchdog"
$ProjectRoot = $PSScriptRoot
$AutoLoginPath = Join-Path $ProjectRoot "AutoLogin.py"

function Get-PythonwPath {
    $pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($pythonw) {
        return $pythonw.Source
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    throw "未找到 pythonw 或 python"
}

function Get-TaskInfo {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        return @{
            exists  = $false
            enabled = $false
            state   = "NotInstalled"
        }
    }
    $enabled = $task.State -eq "Ready"
    return @{
        exists  = $true
        enabled = $enabled
        state   = [string]$task.State
    }
}

function Register-KeepaliveTask {
    if (-not (Test-Path $AutoLoginPath)) {
        throw "找不到 $AutoLoginPath"
    }

    $pythonw = Get-PythonwPath
    $arguments = "`"$AutoLoginPath`" --once --scheduled --quiet"

    $action = New-ScheduledTaskAction `
        -Execute $pythonw `
        -Argument $arguments `
        -WorkingDirectory $ProjectRoot

    $bootTrigger = New-ScheduledTaskTrigger -AtStartup
    $bootTrigger.Delay = "PT1M"

    $repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5) `
        -RepetitionDuration (New-TimeSpan -Days 3650)

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
        -MultipleInstances IgnoreNew `
        -Hidden

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger @($bootTrigger, $repeatTrigger) `
        -Settings $settings `
        -Description "安理工校园网断线自动重连（每5分钟 + 开机1分钟后，无窗口）" `
        -Force | Out-Null
}

try {
    switch ($Action) {
        "status" {
            $info = Get-TaskInfo
            $info | ConvertTo-Json -Compress
            exit 0
        }
        "register" {
            Register-KeepaliveTask
            Write-Output "ok"
            exit 0
        }
        "enable" {
            $info = Get-TaskInfo
            if (-not $info.exists) {
                Register-KeepaliveTask
            }
            Enable-ScheduledTask -TaskName $TaskName | Out-Null
            Write-Output "ok"
            exit 0
        }
        "disable" {
            $info = Get-TaskInfo
            if (-not $info.exists) {
                Write-Output "ok"
                exit 0
            }
            Disable-ScheduledTask -TaskName $TaskName | Out-Null
            Write-Output "ok"
            exit 0
        }
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
