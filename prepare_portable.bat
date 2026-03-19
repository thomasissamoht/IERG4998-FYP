@echo off
REM Batch script to prepare portable folder for USB
REM Run this in the project root directory

setlocal enabledelayedexpansion

set "sourceDir=%CD%"
set "destDir=%CD%\bibtex-manager-portable"

echo ================================================
echo Preparing portable BibTeX Manager
echo ================================================
echo.

REM Create destination folder
if not exist "!destDir!" mkdir "!destDir!"

echo Copying files...

copy "!sourceDir!\bib.py" "!destDir!\" /Y >nul
echo. ✓ bib.py

copy "!sourceDir!\bib_gui_modern.py" "!destDir!\" /Y >nul
echo. ✓ bib_gui_modern.py

copy "!sourceDir!\bib_streamlit.py" "!destDir!\" /Y >nul
echo. ✓ bib_streamlit.py

copy "!sourceDir!\requirements.txt" "!destDir!\" /Y >nul
echo. ✓ requirements.txt

copy "!sourceDir!\build_mac.py" "!destDir!\" /Y >nul
echo. ✓ build_mac.py

REM Copy test_data folder
if exist "!sourceDir!\test_data" (
    xcopy "!sourceDir!\test_data" "!destDir!\test_data\" /E /I /Y >nul
    echo. ✓ test_data/
)

echo.
echo ================================================
echo. ✨ Portable folder ready!
echo ================================================
echo.
echo Location: !destDir!
echo.
echo Next steps:
echo 1. Copy the 'bibtex-manager-portable' folder to USB
echo 2. On professor's Mac:
echo    cd bibtex-manager-portable
echo    python3 -m venv venv
echo    source venv/bin/activate
echo    pip install -r requirements.txt pyinstaller
echo    python build_mac.py
echo 3. Demo - the .app file is ready to use!
echo.
pause
