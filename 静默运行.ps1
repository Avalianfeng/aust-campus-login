# 供计划任务调用：无窗口、正确返回退出码
Set-Location $PSScriptRoot

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    exit 9009
}

& $python "$PSScriptRoot\AutoLogin.py" --once
exit $LASTEXITCODE
