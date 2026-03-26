@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

echo ===============================================
echo Build BibTeX Manager Setup.exe
echo ===============================================

if not exist VERSION (
  echo 1.0.0> VERSION
)

for /f "usebackq tokens=*" %%v in ("VERSION") do set VERSION=%%v
for /f "tokens=1-3 delims=." %%a in ("%VERSION%") do (
  set MAJOR=%%a
  set MINOR=%%b
  set PATCH=%%c
)
set /a PATCH=PATCH+1
set NEW_VERSION=%MAJOR%.%MINOR%.%PATCH%
echo %NEW_VERSION%> VERSION
echo Version bumped: %VERSION% ^> %NEW_VERSION%

echo [1/2] Building app with PyInstaller...
powershell -ExecutionPolicy Bypass -File build_windows.ps1
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [2/2] Building installer with Inno Setup...
powershell -NoProfile -ExecutionPolicy Bypass -File installer\compile_inno.ps1 -Version %NEW_VERSION%

if errorlevel 1 (
  echo Installer build failed.
  exit /b 1
)

echo.
echo SUCCESS: installer\output\BibTeXManagerSetup.exe
echo Installer Version: %NEW_VERSION%
