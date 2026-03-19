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

copy "!sourceDir!\bib.py" "!destDir!\" /Y 
echo. + bib.py

copy "!sourceDir!\bib_gui_modern.py" "!destDir!\" /Y 
echo. + bib_gui_modern.py

copy "!sourceDir!\bib_streamlit.py" "!destDir!\" /Y 
echo. + bib_streamlit.py

copy "!sourceDir!\requirements.txt" "!destDir!\" /Y 
echo. + requirements.txt

copy "!sourceDir!\build_mac.py" "!destDir!\" /Y 
echo. + build_mac.py

REM Copy test_data folder
if exist "!sourceDir!\test_data" (
    xcopy "!sourceDir!\test_data" "!destDir!\test_data" /E /I /Y >nul
    echo. + test_data/
)

echo.
echo ================================================
echo SUCCESS - Portable folder ready!
echo ================================================
echo.
echo Location: !destDir!
echo.
echo Your portable folder is ready to copy to USB.
echo.
echo Instructions for professor's Mac:
echo 1. Copy bibtex-manager-portable folder to USB
echo 2. On Mac: cd bibtex-manager-portable
echo 3. Run: python3 -m venv venv
echo 4. Run: source venv/bin/activate  
echo 5. Run: pip install -r requirements.txt pyinstaller
echo 6. Run: python build_mac.py
echo 7. Demo with: ./dist/BibTeX Manager.app
echo.
echo Press any key to close...
pause
