# Builds dist\TextFixer.exe (single file, no console, with icon).
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\python.exe)) {
    python -m venv .venv
}
.\.venv\Scripts\python -m pip install -r requirements.txt

New-Item -ItemType Directory -Force assets | Out-Null
.\.venv\Scripts\python -m ui.icons assets\icon.ico

.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed `
    --name TextFixer `
    --icon assets\icon.ico `
    --hidden-import uiautomation `
    --hidden-import comtypes.stream `
    --collect-submodules comtypes `
    --exclude-module PySide6.QtWebEngineCore `
    --exclude-module PySide6.QtQml `
    --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.Qt3DCore `
    main.py

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\TextFixer.exe" -ForegroundColor Green
