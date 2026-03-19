# 🎯 Demo Preparation Checklist

## 📋 Before You Go to Professor's Mac

### Day Before Demo:

- [ ] **Test on Your Own Mac First**
  ```bash
  cd ~/Desktop/bibtex-demo
  python3 -m venv test_venv
  source test_venv/bin/activate
  pip install -r requirements.txt
  python3 bib_gui_modern.py
  ```
  - Launch GUI successfully
  - Run with test_data
  - Verify HTML report generates
  - Test all 3 interfaces

- [ ] **Prepare Real Test Files**
  - [ ] Ask professor for 2-3 .bib files with known duplicates
  - [ ] Save them to a folder: `~/Desktop/demo_bibs/`
  - [ ] Or use your own bibliography files
  - [ ] Verify they have actual duplicates/similar entries

- [ ] **Stage Demo Files**
  - [ ] Create `demo_files/` folder on Desktop
  - [ ] Copy your real .bib files there (professor's if provided)
  - [ ] Keep test_data folder as backup
  - [ ] Test running pipeline with demo_files

- [ ] **Create Backup of Project**
  - [ ] Copy entire project folder to USB drive or cloud
  - [ ] Just in case something goes wrong on professor's Mac

- [ ] **Test on Another Mac (if possible)**
  - [ ] Use friend's Mac or school Mac
  - [ ] Verify setup process works
  - [ ] Document any issues

---

## 🎬 Day of Demo Setup

### On Professor's Mac (30 minutes before demo):

1. **Transfer Files**
   ```bash
   # Option A: Copy from USB
   cp -r ~/Desktop/bibtex-project ~/Desktop/
   
   # Option B: Clone from GitHub (if you have a repo)
   git clone https://github.com/yourname/bibtex-manager.git
   cd bibtex-manager
   ```

2. **Quick Setup (5 minutes)**
   ```bash
   cd ~/Desktop/bibtex-project
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Pre-Run One Example (5 minutes)**
   ```bash
   # Test with sample data first
   python3 bib_gui_modern.py
   # Browse to test_data folder
   # Run pipeline
   # See output
   # Close GUI
   ```

4. **Verify Professor's Files (optional)**
   ```bash
   # If professor wants to test with their real files
   python3 bib_gui_modern.py
   # Browse to professor's .bib files
   # Show the duplicate detection
   ```

---

## 🎭 During Demo (Recommended Flow)

### Opening (2 minutes)
- "This is the BibTeX Bibliography Manager I built for my FYP"
- "It automatically finds and removes duplicate bibliography entries"
- "Works with any .bib files"

### Live Demo (5-7 minutes)

**Step 1: Launch GUI** (1 min)
```bash
python3 bib_gui_modern.py
```
- Point out: Clean interface, dark mode, professional design

**Step 2: Load Files** (1 min)
```
Click "Browse" → Select test_data folder
```
- Explain: 3 folders with bibliography files
- Show the file structure

**Step 3: Run Pipeline** (2 min)
```
Adjust similarity slider to 85%
Click "Run Pipeline"
```
- Point out real-time progress
- Show the 4 steps:
  1. Crawling files
  2. Finding duplicates
  3. Removing duplicates
  4. Normalizing keys

**Step 4: Show Results** (1 min)
- Click "Results" tab
- Show statistics cards
- Point out reduction rate
- Explain the backup system

**Step 5: View Duplicates** (1 min)
- Click "Duplicates" tab
- Show duplicate groups found
- Explain similarity scores
- Which entry was kept, which removed

**Step 6: View HTML Report** (1 min)
```
Click "View Report" button
```
- Browser opens beautiful HTML report
- Show:
  - Statistics summary
  - Duplicate group details
  - Citation key changes
  - Professional styling

### With Real Files (optional, 3-5 min)
If professor provides real .bib files:
```
Edit directory path or upload files
Run pipeline with their real data
Show how many duplicates found
Explain it works with real research bibliographies
```

### Closing (1 minute)
- Summarize the 4 main features:
  1. ✓ Crawls folders recursively
  2. ✓ Detects duplicates (exact + fuzzy)
  3. ✓ Removes intelligently
  4. ✓ Beautiful HTML reports
- Mention: Also has web app version, CLI version
- Offer: "You can test anytime, it's easy to use"

---

## 💻 Backup Plans (If GUI Fails)

### Plan B: Web App
```bash
streamlit run bib_streamlit.py
```
- Opens in browser automatically
- More reliable across platforms
- Can still show all features
- Interactive visualizations

### Plan C: CLI
```bash
python3 bib.py
```
- Select option 1: Run full pipeline
- Enter test_data
- Shows all steps in terminal
- Professional terminal output
- Still demonstrates all functionality

### Plan D: Pre-recorded Demo
- Before you go, record a screencast of the GUI working
- Have it ready on your laptop
- "Here's how it looks normally..." if live version fails

---

## 🔧 Troubleshooting During Demo

| Problem | Solution |
|---------|----------|
| GUI won't launch | Use web app or CLI instead |
| Missing dependencies | Run `pip install -r requirements.txt` |
| Python not found | Use `python3` explicitly |
| Port already in use | `streamlit run --server.port 8502 bib_streamlit.py` |
| Files not found | Check paths are correct, use absolute paths |
| Permission error | Files might be locked, try with test_data first |

---

## 📝 Key Points to Emphasize

1. **Automatic**: No manual work, just select folder and click
2. **Smart**: Fuzzy matching finds similar entries, not just exact matches
3. **Safe**: Creates backups before making any changes
4. **Beautiful**: Professional HTML reports generated automatically
5. **Portable**: Works on Windows, Mac, Linux
6. **Cloud-Ready**: Can be deployed as web app (Streamlit Cloud)
7. **Fast**: Processes hundreds of entries in seconds

---

## 🎁 Deliverables to Show

- [ ] Working application (all 3 interfaces)
- [ ] Sample HTML report (printed or on screen)
- [ ] Clean, modern GUI
- [ ] Statistics dashboard
- [ ] Duplicate visualization
- [ ] Successfully processed files
- [ ] Show backup system

---

## 📸 Optional: Screenshots to Prepare

Take these beforehand as backup:
- [ ] GUI launching screenshot
- [ ] Test run with results
- [ ] HTML report in browser
- [ ] Statistics dashboard
- [ ] Duplicate groups view
- [ ] Citation key changes

Use these if live demo has issues.

---

## ✅ Final Checklist

Before leaving for demo:
- [ ] Laptop fully charged
- [ ] Internet not required (for offline)
- [ ] Project folder copied to USB or cloud
- [ ] requirements.txt is complete
- [ ] Tested on your Mac
- [ ] Test files prepared
- [ ] All 3 interfaces work
- [ ] HTML report example generated
- [ ] Notes/talking points written
- [ ] Backup plan ready (web app, CLI, screenshots)
- [ ] Demo script rehearsed (2-3 runs)

---

## 🎯 You're Ready!

You've got this! 🎉

The application is professional, works smoothly, and shows all the requirements.
Just do a dry run before you leave, and you'll do great!

Good luck! 💪
