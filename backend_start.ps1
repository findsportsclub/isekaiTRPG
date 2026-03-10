Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

cd $HOME\Desktop\myproject\isekaiTRPG\backend

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    Write-Host "[ERROR] .venv\Scripts\Activate.ps1 not found"
    exit 1
}

.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload