param(
    [string]$PythonExe = "venv\Scripts\python.exe",
    [string]$IconPath = "installer\app.ico"
)

$ErrorActionPreference = "Stop"

Write-Host "==============================================="
Write-Host "Building BibTeX Manager (Windows App)"
Write-Host "==============================================="

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found at '$PythonExe'. Activate/create venv first."
}

$py = Resolve-Path $PythonExe

Write-Host "Using Python: $py"

# Ensure PyInstaller is available in build environment
& $py -m pip install --upgrade pip
& $py -m pip install pyinstaller

# Clean old build artifacts
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "BibTeXManager.spec") { Remove-Item "BibTeXManager.spec" -Force }

# Optional app icon
$iconArgs = @()
if (Test-Path $IconPath) {
    Write-Host "Using app icon: $IconPath"
    $iconArgs = @("--icon", $IconPath)
} else {
    Write-Host "No app icon found at '$IconPath' (continuing without custom icon)."
}

# Build GUI app folder (best for installer creation)
& $py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "BibTeXManager" `
    --collect-all customtkinter `
    --hidden-import bibtexparser.bparser `
    --hidden-import bibtexparser.bwriter `
    --hidden-import bibtexparser.bibdatabase `
    --add-data "test_data;test_data" `
    @iconArgs `
    bib_gui_modern.py

Write-Host ""
Write-Host "Build complete. App folder: dist\BibTeXManager"
Write-Host ""
Write-Host "Next: Create installer using Inno Setup script: installer\BibTeXManager.iss"
Write-Host "If Inno Setup is installed, run: installer\build_setup.bat"
