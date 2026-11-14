# Installs dist\TextFixer.exe like normal software:
#   - copies it to %LOCALAPPDATA%\Programs\TextFixer\TextFixer.exe
#   - adds a "Text Fixer" icon to the Desktop and the Start menu
#   - removes the old "FixIt" version (same app, old name) if it's there
#   - starts Text Fixer
# Your settings and API keys stay in %APPDATA%\FixIt and are kept.
# Usage:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$src = Join-Path $PSScriptRoot "dist\TextFixer.exe"
if (-not (Test-Path $src)) { throw "dist\TextFixer.exe not found - run build.ps1 first." }

$dir = Join-Path $env:LOCALAPPDATA "Programs\TextFixer"
$exe = Join-Path $dir "TextFixer.exe"
New-Item -ItemType Directory -Force $dir | Out-Null

# Close any running copy (new or old name) so files can be replaced.
Get-Process TextFixer, FixIt -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500
Copy-Item $src $exe -Force

$desktop = [Environment]::GetFolderPath("Desktop")
$programs = [Environment]::GetFolderPath("Programs")

# Remove the old FixIt install and its shortcuts.
foreach ($old in @((Join-Path $desktop "FixIt.lnk"), (Join-Path $programs "FixIt.lnk"),
                   (Join-Path $env:LOCALAPPDATA "Programs\FixIt"))) {
    if (Test-Path $old) { Remove-Item $old -Recurse -Force; Write-Host "Removed old: $old" }
}

$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in @((Join-Path $desktop "Text Fixer.lnk"), (Join-Path $programs "Text Fixer.lnk"))) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath = $exe
    $s.WorkingDirectory = $dir
    $s.IconLocation = "$exe,0"
    $s.Description = "Text Fixer - fix grammar anywhere with AI"
    $s.Save()
    Write-Host "Shortcut: $lnk"
}

# "Start with Windows": move the old FixIt entry to the new name / path.
$run = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$hadOld = [bool](Get-ItemProperty -Path $run -Name FixIt -ErrorAction SilentlyContinue)
$hasNew = [bool](Get-ItemProperty -Path $run -Name TextFixer -ErrorAction SilentlyContinue)
if ($hadOld) { Remove-ItemProperty -Path $run -Name FixIt }
if ($hadOld -or $hasNew) { Set-ItemProperty -Path $run -Name TextFixer -Value "`"$exe`"" }

Start-Process $exe
Write-Host "Installed: $exe" -ForegroundColor Green
