# Builds the Text Fixer Android APK → ..\dist\TextFixer-android.apk
# Uses Android Studio's bundled Java and the Gradle version already cached on this PC (works offline).
# Usage:  powershell -ExecutionPolicy Bypass -File android\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$gradle = Get-ChildItem "$env:USERPROFILE\.gradle\wrapper\dists\gradle-9.5.1-bin" -Recurse -Filter gradle.bat |
          Select-Object -First 1
if (-not $gradle) { throw "Gradle 9.5.1 not found in ~/.gradle. Open the project once in Android Studio." }

& $gradle.FullName --offline --console=plain assembleRelease
if ($LASTEXITCODE -ne 0) { throw "Build failed" }

$out = Join-Path $PSScriptRoot "..\dist"
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item "app\build\outputs\apk\release\app-release.apk" "$out\TextFixer-android.apk" -Force
Write-Host "Built: $((Resolve-Path "$out\TextFixer-android.apk").Path)" -ForegroundColor Green
