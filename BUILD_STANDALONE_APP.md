# 🚀 Create Standalone Mac Application (.app)

## Overview

You can create a **standalone Mac application** that requires NO installation, NO Python, and NO dependencies. Just double-click to run!

---

## 🎯 Method 1: PyInstaller (RECOMMENDED - Easiest)

### Step 1: Install PyInstaller
```bash
source venv/bin/activate
pip install pyinstaller
```

### Step 2: Run the Build Script
```bash
python build_mac.py
```

This creates:
- `dist/BibTeX Manager.app` - GUI application
- `dist/BibTeX Web` - Web application

### Step 3: Test the App
```bash
# Double-click the app in Finder, OR
./dist/BibTeX\ Manager.app/Contents/MacOS/BibTeX\ Manager
```

### Step 4: Package for Distribution
```bash
# Create a zip file to send to professor
cd dist
zip -r "BibTeX Manager.zip" "BibTeX Manager.app"
# Send BibTeX Manager.zip to professor
```

**That's it!** Professor just unzips and double-clicks.

---

## 🎯 Method 2: py2app (Apple Official Way)

### Step 1: Install py2app
```bash
source venv/bin/activate
pip install py2app
```

### Step 2: Build App
```bash
python setup.py py2app
```

This creates:
- `dist/BibTeX Manager.app` - Full Mac application

### Step 3: Package and Distribute
```bash
cd dist
zip -r "BibTeX Manager.zip" "BibTeX Manager.app"
```

---

## 📦 What Gets Produced

### PyInstaller Output:
```
dist/
├── BibTeX Manager.app          # Full app bundle (can double-click)
│   └── Contents/
│       ├── MacOS/              # Executable
│       ├── Resources/          # Data files (test_data)
│       └── Info.plist          # App configuration
└── BibTeX Web                  # Standalone web executable
```

- **Size**: ~100-200MB (includes Python runtime)
- **Works on**: macOS 10.14+
- **Installation**: Just copy .app to Applications folder
- **Running**: Double-click or `open BibTeX\ Manager.app`

---

## 🎁 Distribution to Professor

### Option A: Direct .app File
```bash
# Zip just the app
cd dist
zip -r "BibTeX Manager.app.zip" "BibTeX Manager.app"

# Send: BibTeX Manager.app.zip
# Professor: Unzip and double-click
```

### Option B: DMG Installer (Professional)
```bash
# Create a .dmg file (disk image for Mac)
hdiutil create -volname "BibTeX Manager" \
  -srcfolder dist/BibTeX\ Manager.app \
  -ov -format UDZO BibTeX_Manager.dmg

# Professor double-clicks BibTeX_Manager.dmg
# Sees app in Finder, drags to Applications
```

### Option C: GitHub Releases
```bash
# Push to GitHub
git add dist/
git commit -m "Add built Mac app"
git push

# Create release with .zip file attached
# Professor downloads from GitHub releases
```

---

## ⚙️ Manual Build Commands (If Script Doesn't Work)

### GUI Only:
```bash
pyinstaller --onefile --windowed \
  --name "BibTeX Manager" \
  --add-data "test_data:test_data" \
  --icon icon.icns \
  bib_gui_modern.py
```

### Web Only:
```bash
pyinstaller --onefile \
  --name "BibTeX Web" \
  --add-data "test_data:test_data" \
  bib_streamlit.py
```

### Both (No Console):
```bash
pyinstaller --onefile --windowed \
  --name "BibTeX Manager" \
  bib_gui_modern.py

pyinstaller --onefile --windowed \
  --name "BibTeX Web" \
  bib_streamlit.py
```

---

## 🔧 Troubleshooting

### "command not found: pyinstaller"
```bash
# Activate venv
source venv/bin/activate
# Try again
python build_mac.py
```

### "No module named 'bibtexparser'"
```bash
# Ensure all deps are installed
pip install -r requirements.txt
# Try again
python build_mac.py
```

### "Module not found at runtime"
Edit the build command to include hidden imports:
```bash
pyinstaller --onefile --windowed \
  --hidden-import=bibtexparser \
  --hidden-import=thefuzz \
  bib_gui_modern.py
```

### App runs but can't find files
The app needs bundled data. In build command:
```bash
--add-data "test_data:test_data"
```

This includes test_data folder in the app.

---

## 📋 Comparison: All Methods

| Method | File Size | Setup | Distribution | Best For |
|--------|-----------|-------|--------------|----------|
| **PyInstaller** | 100-200MB | 1 cmd | .zip or .dmg | Quick, simple |
| **py2app** | 100-200MB | 1 cmd | .zip or .dmg | Professional |
| **DMG Installer** | 100-200MB | 2 cmds | .dmg | Polished delivery |
| **Homebrew** | 50-100MB | Complex | brew install | Advanced users |

---

## ✅ Pre-Demo Checklist

- [ ] Install PyInstaller: `pip install pyinstaller`
- [ ] Run build script: `python build_mac.py`
- [ ] Test app: Double-click `dist/BibTeX Manager.app`
- [ ] Test with sample data
- [ ] Zip the app file
- [ ] Test unzipping and running from unzipped copy
- [ ] Share .zip file with professor

---

## 🎯 For Professor (Distribution Instructions)

Create a README in the .zip:

```
📚 BibTeX Bibliography Manager

Installation:
1. Unzip this file
2. Double-click "BibTeX Manager.app"
3. Done! No installation needed

Use:
1. Click "Browse" to select folder with .bib files
2. Adjust similarity threshold (85% recommended)
3. Click "Run Pipeline"
4. View results and HTML report

Features:
• Finds duplicate bibliography entries
• Removes duplicates intelligently
• Normalizes citation keys
• Creates automatic backups
• Generates professional HTML reports

Tested on: macOS 10.14+
```

---

## 🚀 Summary

**To send standalone app to professor:**

```bash
# 1. Install PyInstaller (one-time)
pip install pyinstaller

# 2. Build the app
python build_mac.py

# 3. Create distribution zip
cd dist
zip -r "BibTeX Manager.zip" "BibTeX Manager.app"

# 4. Send "BibTeX Manager.zip" to professor
# Professor unzips and double-clicks - done!
```

**That's it!** No Python, no dependencies, no setup needed on professor's Mac. ✨

---

## 💡 Pro Tips

1. **File Size**: Apps are large (100-200MB) because they include Python runtime. Normal.
2. **Notarization**: For Apple signing/notarization (advanced), see Apple docs.
3. **Code Signing**: Add `--codesign-identity` flag if you have a certificate.
4. **Icon**: Add `--icon icon.icns` to use custom app icon.
5. **Cached**: First run is slower. Subsequent runs are fast.

**Good luck with your demo!** 🎉
