# 一键启动后端（同时托管前端页面）
# 用法：右键 -> 使用 PowerShell 运行，或在终端执行 .\start.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "[!] 未找到虚拟环境，正在创建..." -ForegroundColor Yellow
    python -m venv (Join-Path $root ".venv")
    & $python -m pip install -r (Join-Path $root "backend\requirements.txt")
}

Write-Host "启动服务： http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "接口文档： http://127.0.0.1:8000/docs" -ForegroundColor Green
Set-Location (Join-Path $root "backend")
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
