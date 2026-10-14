# 重新构建前端（改完 Vue 代码后执行）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run build
Write-Host "前端已构建到 frontend/dist，刷新 http://127.0.0.1:8000 即可看到最新页面" -ForegroundColor Green
