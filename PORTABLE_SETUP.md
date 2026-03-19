# 📦 Portable Setup Instructions

## ⚡ Quick (Windows)

```bash
# Just double-click this file:
prepare_portable.bat

# Done! Your folder is ready at: bibtex-manager-portable/
```

## ⚡ Quick (Mac/Linux)

```bash
# Run this:
./prepare_portable.ps1

# Or manually copy these files to bibtex-manager-portable/:
# - bib.py
# - bib_gui_modern.py
# - bib_streamlit.py
# - requirements.txt
# - build_mac.py
# - test_data/ (entire folder)
```

---

## 📋 What Gets Created

```
bibtex-manager-portable/
├── bib.py
├── bib_gui_modern.py
├── bib_streamlit.py
├── requirements.txt
├── build_mac.py
├── test_data/
│   ├── folder1/
│   ├── folder2/
│   └── folder3/
└── QUICK_START.txt
```

---

## 🚀 What You Do

### Step 1: Create Portable Folder
**On Windows:**
- Double-click `prepare_portable.bat`

**On Mac:**
```bash
chmod +x prepare_portable.ps1
./prepare_portable.ps1
```

### Step 2: Copy to USB
```bash
# Copy the entire folder
cp -r bibtex-manager-portable /Volumes/USB/

# Or drag-and-drop in Finder
```

### Step 3: On Professor's Mac
```bash
# Copy from USB to desktop
cp -r /Volumes/USB/bibtex-manager-portable ~/Desktop/

# Or just use from USB directly
cd /Volumes/USB/bibtex-manager-portable

# Setup (5 min)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt pyinstaller

# Build (2 min)
python build_mac.py

# Demo! 
./dist/BibTeX\ Manager.app/Contents/MacOS/BibTeX\ Manager
```

---

## ✅ Checklist

Before copying to USB:
- [ ] Run `prepare_portable.bat` (or manual copy)
- [ ] Check folder exists: `bibtex-manager-portable/`
- [ ] Verify these files are inside:
  - [ ] bib.py
  - [ ] bib_gui_modern.py
  - [ ] bib_streamlit.py
  - [ ] requirements.txt
  - [ ] build_mac.py
  - [ ] test_data/ folder (with 3 subfolders)

---

## 📍 Folder Location

After running the script, the folder is at:

```
c:\Users\dicta\OneDrive\Documents\IERG FYP\bibtex-manager-portable
```

Just copy this entire folder to USB.

---

## 💡 Troubleshooting

**"prepare_portable.bat not found"**
- Make sure you're in the project root directory
- Run: `dir prepare_portable.bat`

**Script runs but folder is empty**
- Run it again
- Or manually copy files from project root to `bibtex-manager-portable/`

**test_data not copied**
- Check it exists in project root: `ls test_data/`
- Manually copy: `cp -r test_data bibtex-manager-portable/`

---

## 🎯 Result

You'll have a **single folder** with everything needed:
- Copy to USB ✓
- Works on any Mac ✓
- No dependencies needed ✓
- Can build standalone app ✓
- Easy to share ✓

Perfect for tomorrow's demo! 🚀
