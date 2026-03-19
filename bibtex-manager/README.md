# BibTeX Manager — Portable Setup

This folder is prepared for a quick demo on another machine (e.g., your professor's Mac).
Follow the sections below to set up and run the app.

---

## Quick checklist (what's in this folder)
- `bib.py` — Core CLI application
- `bib_gui_modern.py` — Modern desktop GUI (CustomTkinter)
- `bib_streamlit.py` — Streamlit web app
- `requirements.txt` — Python dependencies
- `build_mac.py` — Script to build a macOS `.app` using PyInstaller
- `test_data/` — Sample `.bib` files for testing
- `QUICK_START.txt` — Short quick-start notes

---

## Recommended: Demo on macOS (5–15 minutes)
1. Copy this folder to the Mac (Desktop suggested)

2. Open Terminal and go to the folder:
```bash
cd ~/Desktop/bibtex-manager-portable
```

3. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Install dependencies (approx 2–5 minutes):
```bash
pip install -r requirements.txt
```

5A. (Quick run GUI without a bundled app)
```bash
python3 bib_gui_modern.py
```
- Click `Browse` → select the folder with `.bib` files (or `test_data`)
- Adjust similarity threshold (85% recommended)
- Click `Run Pipeline` and view results

5B. (Optional: Build a standalone `.app` to avoid repeating setup)
```bash
pip install pyinstaller
python build_mac.py
```
- After build, the app is in `dist/BibTeX Manager.app`
- Zip and give the `.app` to the professor: `zip -r "BibTeX Manager.zip" "BibTeX Manager.app"`

---

## If you prefer web app (Streamlit)
```bash
# (after venv is activated)
streamlit run bib_streamlit.py
```
- The web UI opens in a browser on `http://localhost:8501`
- Upload `.bib` files or point to a directory

---

## Quick Windows notes (if needed)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bib_gui_modern.py
```

---

## Troubleshooting
- If `python3` is not found, try `python`.
- If `tkinter` is missing on macOS, install system Tcl/Tk or use homebrew: `brew install python-tk`.
- If the GUI fails, use the Streamlit web app (more portable across systems).
- If `pyinstaller` cannot find a module at runtime, rebuild with hidden imports:
```bash
pyinstaller --onefile --windowed --hidden-import=bibtexparser bib_gui_modern.py
```

---

## Demo tips
- Ask the professor to prepare 1–3 real `.bib` files in a single folder before the demo.
- Run the app once on `test_data` so you know expected output.
- If anything goes wrong, run the CLI `python bib.py` to show step-by-step output.

---

If you want, I can also produce a zipped archive of this folder for you to copy to your USB. Say the word and I'll prepare `bibtex-manager-portable.zip` in the project root.
