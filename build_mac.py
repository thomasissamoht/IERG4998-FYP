#!/usr/bin/env python3
"""
Build script to create standalone Mac application
Run this to generate the .app file
"""

import subprocess
import sys
import os
from pathlib import Path

def build_gui_app():
    """Build the GUI application"""
    print("🔨 Building BibTeX Bibliography Manager GUI...")
    
    cmd = [
        "pyinstaller",
        "--onefile",           # Single executable
        "--windowed",          # No console window
        "--name=BibTeX Manager",
        "--add-data=test_data:test_data",  # Include test data
        "bib_gui_modern.py"
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("✅ GUI app created: dist/BibTeX Manager.app")
        print("📁 Location: dist/BibTeX Manager.app")
        print("🚀 Double-click to run!")
    else:
        print("❌ Build failed")
        sys.exit(1)

def build_web_app():
    """Build the web application"""
    print("\n🔨 Building BibTeX Bibliography Manager Web...")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=BibTeX Web",
        "--add-data=test_data:test_data",
        "bib_streamlit.py"
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("✅ Web app created: dist/BibTeX Web")
    else:
        print("❌ Build failed")
        sys.exit(1)

if __name__ == "__main__":
    # Check if PyInstaller executable is available on PATH
    import shutil

    if shutil.which('pyinstaller') is None:
        print("❌ PyInstaller not found on PATH")
        print("Install it in your environment: pip install pyinstaller")
        sys.exit(1)
    
    # Build apps
    print("=" * 60)
    print("Building BibTeX Bibliography Manager")
    print("=" * 60)
    
    build_gui_app()
    build_web_app()
    
    print("\n" + "=" * 60)
    print("✨ Build complete!")
    print("=" * 60)
    print("\nGenerated files:")
    print("📱 GUI: dist/BibTeX Manager.app")
    print("🌐 Web: dist/BibTeX Web")
    print("\n💡 To distribute to professor:")
    print("1. Zip the dist/ folder")
    print("2. Send the zip file")
    print("3. Professor unzips and double-clicks .app")
    print("4. No installation needed!")
