# 兼容旧用法：等同于开启后台保活
python -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); from AutoLogin import enable_keepalive; ok, msg = enable_keepalive(); Write-Host $msg; if (-not $ok) { exit 1 }"
