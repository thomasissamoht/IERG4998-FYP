#!/bin/bash or run with PowerShell

# PowerShell script to prepare portable folder
# Usage: Run this script in the project root directory

$sourceDir = (Get-Location).Path
$destDir = Join-Path $sourceDir "bibtex-manager-portable"

Write-Host "================================================"
Write-Host "Preparing portable BibTeX Manager"
Write-Host "================================================"
Write-Host ""

# Create destination if not exists
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

# Copy files
Write-Host "Copying files..."

Copy-Item "$sourceDir\bib.py" "$destDir\" -Force
Write-Host "✓ bib.py"

Copy-Item "$sourceDir\bib_gui_modern.py" "$destDir\" -Force
Write-Host "✓ bib_gui_modern.py"

Copy-Item "$sourceDir\bib_streamlit.py" "$destDir\" -Force
Write-Host "✓ bib_streamlit.py"

Copy-Item "$sourceDir\requirements.txt" "$destDir\" -Force
Write-Host "✓ requirements.txt"

Copy-Item "$sourceDir\build_mac.py" "$destDir\" -Force
Write-Host "✓ build_mac.py"

Copy-Item "$sourceDir\test_data" "$destDir\test_data" -Recurse -Force
Write-Host "✓ test_data/"

# Create setup guides
Write-Host ""
Write-Host "Creating setup guides..."

$readmeContent = @"
📚 BibTeX Bibliography Manager - Portable

Quick Start:

WINDOWS:
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  python bib_gui_modern.py

MAC/LINUX:
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python3 bib_gui_modern.py

For Mac standalone app:
  pip install pyinstaller
  python build_mac.py

See README_MAC_SETUP.md for detailed instructions.
"@

Set-Content -Path "$destDir\QUICK_START.txt" -Value $readmeContent
Write-Host "✓ QUICK_START.txt"

Write-Host ""
Write-Host "================================================"
Write-Host "✨ Portable folder ready!"
Write-Host "================================================"
Write-Host ""
Write-Host "Location: $destDir"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Copy the [bibtex-manager-portable] folder to USB"
Write-Host "2. On professors Mac:"
Write-Host "   cd bibtex-manager-portable"
Write-Host "   python3 -m venv venv"
Write-Host "   source venv/bin/activate"
Write-Host "   pip install -r requirements.txt pyinstaller"
Write-Host "   python build_mac.py"
Write-Host "3. Demo:"
Write-Host "   ./dist/BibTeX Manager.app/Contents/MacOS/BibTeX Manager"
Write-Host ""
