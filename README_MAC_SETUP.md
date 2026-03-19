# 📚 BibTeX Bibliography Manager - Quick Start Guide

## 🎯 For Mac Demonstration

### System Requirements
- **macOS** 10.14 or later
- **Python** 3.8 or later (built-in or from python.org)
- **Xcode Command Line Tools** (for first-time setup)

---

## ⚡ Quick Setup (5 minutes)

### Step 1: Install Xcode Command Line Tools (First time only)
```bash
xcode-select --install
```

### Step 2: Verify Python Installation
```bash
python3 --version
# Should show Python 3.8+
```

If Python is not installed, download from https://www.python.org/downloads/

### Step 3: Clone/Transfer Project Files
```bash
# On Mac, navigate to where you want the project
cd ~/Desktop  # or any folder

# Copy all project files here (or use git clone if on GitHub)
```

### Step 4: Create Virtual Environment
```bash
cd <project-folder>
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal line.

### Step 5: Install Dependencies
```bash
pip install -r requirements.txt
```

That's it! ✅

---

## 🚀 Running the Application

### Option A: Modern GUI (Recommended for Demo) 🎨
```bash
source venv/bin/activate
python3 bib_gui_modern.py
```
- Most intuitive
- Beautiful dark/light theme
- Perfect for live demonstration
- Works offline

### Option B: Web App 🌐
```bash
source venv/bin/activate
streamlit run bib_streamlit.py
```
- Opens in browser automatically
- Interactive charts
- Upload files directly
- Great for collaborative testing

### Option C: Command Line 💻
```bash
source venv/bin/activate
python3 bib.py
```
- Step-by-step guided mode
- Full control
- Best for automation

---

## 📂 Project Structure

```
bibtex-manager/
├── bib.py                    # Core application
├── bib_gui_modern.py        # Desktop GUI
├── bib_streamlit.py         # Web app
├── requirements.txt         # Dependencies
├── ENHANCEMENTS.md          # Feature documentation
├── test_data/               # Sample files
│   ├── folder1/
│   ├── folder2/
│   └── folder3/
├── venv/                    # Virtual environment (created after setup)
└── README_SETUP.md          # This file
```

---

## 🧪 Test with Sample Data

1. **Using GUI:**
   ```bash
   python3 bib_gui_modern.py
   ```
   - Click "Browse" → Select `test_data` folder
   - Adjust similarity slider (85% default)
   - Click "Run Pipeline"
   - View results and HTML report

2. **Using Web App:**
   ```bash
   streamlit run bib_streamlit.py
   ```
   - Upload .bib files or select directory
   - Click "Run Pipeline"
   - View interactive visualizations

---

## 🔄 Using with Real Bibliography Files

### Prepare Test Files Before Demo:
```bash
# Create a demo folder
mkdir ~/Desktop/demo_bibs
cp ~/path/to/your/files/*.bib ~/Desktop/demo_bibs/

# OR use with professor's files directly
```

### During Demo:
1. Launch GUI: `python3 bib_gui_modern.py`
2. Click "Browse" → Select folder with real .bib files
3. Show the duplicate detection live
4. View generated HTML report
5. Show distributed files in folders

---

## ⚙️ Troubleshooting on Mac

### Python Command Not Found
```bash
# Use python3 explicitly
python3 --version
python3 -m pip install -r requirements.txt
```

### Permission Denied on venv
```bash
# Fix permissions
chmod +x venv/bin/python
source venv/bin/activate
```

### GUI Won't Launch
```bash
# May need to use python3 explicitly
python3 bib_gui_modern.py

# Or check if tkinter is installed
python3 -m tkinter
```

### Streamlit Issues
```bash
# Clear streamlit cache
streamlit cache clear

# Run with verbose output
streamlit run bib_streamlit.py --logger.level=debug
```

---

## 💡 Demo Tips

### Best Flow for Live Demo:
1. **Show the GUI** (most impressive visually)
   - Clean, modern interface
   - Real-time progress
   - Statistics dashboard

2. **Run Pipeline** with sample or real files
   - Show duplicate detection in action
   - Display similarity scores
   - Show HTML report generation

3. **View HTML Report** in browser
   - Professional formatting
   - Interactive elements
   - All statistics in one place

4. **Show Download** of master.bib
   - Distributed to folders
   - Backups created

### If GUI Has Issues:
- Fall back to web app (more reliable cross-platform)
- Or use CLI with visible output

---

## 🔐 Before Handing to Professor

### Pre-Demo Checklist:
- [ ] Test with your real bibliography files on your own Mac first
- [ ] Pre-run one example so you know what output looks like
- [ ] Have sample output/HTML report ready as backup
- [ ] Test GUI launch to ensure it works
- [ ] Have professor's .bib files ready in a folder
- [ ] Create a ~/Desktop/demo_files folder with test files
- [ ] Write down or screenshot the commands if needed

### Shell Script for Easy Launch (Optional):
Create `launch_demo.sh`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 bib_gui_modern.py
```

Then:
```bash
chmod +x launch_demo.sh
./launch_demo.sh
```

---

## 📊 What to Show Professor

1. **Core Functionality:**
   - CLI mode: Basic functionality, step-by-step
   - GUI mode: Modern interface, real-time processing
   - Web mode: Cloud-deployable, interactive

2. **Key Features:**
   - ✓ Crawls multiple folders for .bib files
   - ✓ Detects duplicates (exact and fuzzy)
   - ✓ Intelligently removes duplicates
   - ✓ Normalizes citation keys
   - ✓ Creates backups before changes
   - ✓ Generates HTML reports
   - ✓ Distributes to original folders

3. **With Real Files:**
   - Show it processing actual bibliography
   - Display duplicate analysis
   - Show the HTML report
   - Verify distributed files

---

## 📝 Quick Reference

| Task | Command |
|------|---------|
| Activate venv | `source venv/bin/activate` |
| Deactivate venv | `deactivate` |
| Install deps | `pip install -r requirements.txt` |
| Run GUI | `python3 bib_gui_modern.py` |
| Run Web App | `streamlit run bib_streamlit.py` |
| Run CLI | `python3 bib.py` |

---

## ✨ You're Ready!

The project is now portable and ready for demonstration on any Mac. Just follow the 5-step setup, and you're good to go!

Good luck with your demo! 🎉
