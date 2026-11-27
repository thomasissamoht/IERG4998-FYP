# 📚 BibTeX Bibliography Manager

A comprehensive, cross-platform tool for managing, deduplicating, and organizing BibTeX bibliography files. Built for researchers and students who need to consolidate references from multiple sources.

## ✨ Key Features

- **🔍 Intelligent Duplicate Detection** - Fuzzy matching for similar entries, DOI verification for exact matches
- **🗑️ Smart Deduplication** - Merges duplicates intelligently, keeps most complete entry
- **🔑 Citation Key Normalization** - Uses each author's surname initial plus publication year; repeated author/year keys receive `a`, `b`, `c` suffixes
- **👀 Review Before Export** - Inspect and filter the actual old-to-new citation-key mappings, then confirm before creating output
- **📂 Batch Processing** - Crawls folders recursively, processes hundreds of files
- **💾 Source Preservation** - Creates a processed project copy and leaves original bibliography and LaTeX files unchanged
- **📄 Document Preview** - View supported project text files in Documents; changed citations in `.tex` files have highlighting and next/previous navigation
- **📊 Beautiful HTML Reports** - Professional reports with statistics and duplicate analysis
- **🎨 Modern GUI** - CustomTkinter interface with system-aware light/dark themes, consistent colors, and adaptive window sizing
- **🌐 Web App** - Streamlit interface for cloud deployment
- **💻 CLI** - Full command-line control for automation

## 🚀 Quick Start

### Download the desktop app (no Python setup required)

Download the latest installer from the repository's [GitHub Releases](https://github.com/thomasissamoht/IERG4998-FYP/releases/latest):

- **Windows:** Download `BibTeXManagerSetup.exe`, run it, and launch **BibTeX Manager** from the Start menu.
- **macOS:** Download `BibTeXManager-mac-<version>-x86_64.dmg` for Intel or `BibTeXManager-mac-<version>-arm64.dmg` for Apple Silicon, open it, and drag **BibTeX Manager** to Applications.

Choose the file for your operating system. The installers include the app and its runtime dependencies; you do not need to install Python or run `pip`. Because these builds are currently unsigned/not notarized, Windows SmartScreen or macOS Gatekeeper may show a first-launch warning. Only continue if the installer came from this repository's Releases page. On Mac, Control-click the app and choose **Open** to approve it.

Maintainers: update `VERSION` to the release number, then push the matching tag (for example, set `VERSION` to `1.0.10` and push `v1.0.10`). GitHub Actions builds both installers and attaches them to that GitHub Release.

### On Windows:
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run GUI
python bib_gui_modern.py
```

### On Mac/Linux:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run GUI
python3 bib_gui_modern.py
```

Or use the automated launcher:
```bash
chmod +x launch.sh
./launch.sh
```

## 📖 Documentation

- **[README_MAC_SETUP.md](README_MAC_SETUP.md)** - Complete Mac setup and troubleshooting guide
- **[ENHANCEMENTS.md](ENHANCEMENTS.md)** - Detailed feature documentation
- **[DEMO_CHECKLIST.md](DEMO_CHECKLIST.md)** - Pre-demo preparation guide

## 🎯 Three Ways to Use

### 1. GUI (Recommended) 🎨
```bash
python3 bib_gui_modern.py
```
Modern desktop interface with:
- Clean sidebar controls
- Real-time progress logging
- Statistics dashboard
- One-click HTML report viewing
- Dark/light mode toggle

In the Library tab, select a reference to enable its inspector actions. Choose a collection destination before adding it; metadata edits, notes, tags, and collections are kept for the current app session and are not written to the source `.bib` files.

For a folder containing multiple projects, click **Analyze & Review** to see the discovered project locations, then **Analyze projects**. The Pipeline tab shows the current project and stage. In **Key Review**, choose each project, inspect its keys (using the page controls for large lists), and mark it reviewed. Once all ready projects are reviewed, click **Process reviewed projects**. Completed results become available as processing continues: use **Result project** to switch the Dashboard, Library, Duplicates, Fixes, and Documents to a completed project. Use **Open Report** to open its HTML report, if enabled. Failed or empty projects are listed separately; source projects remain unchanged.

Root-level `.tex` and `.bib` files are grouped into separate projects when multiple groups or subfolder projects are found. Literal `\input`, `\include`, `\bibliography`, and `\addbibresource` links and matching citation keys connect files; common keys can therefore connect otherwise separate documents. The list shows each group's files. Each group's processed copy contains only its root-level `.tex` and `.bib` files, not other files, assets, or subfolders; add any needed assets separately. Dynamic LaTeX paths and links to subfolder files are not used for grouping. To treat the folder and its subfolders as one project instead, choose **Treat this folder as one project**.

### 2. Web App 🌐
```bash
streamlit run bib_streamlit.py
```
Browser-based interface with:
- File upload support
- Interactive Plotly charts
- Tabbed interface
- Download results
- Cloud deployable

### 3. Command Line 💻
```bash
python3 bib.py
```
Full control with:
- Step-by-step or automatic mode
- Detailed logging
- Configurable threshold
- Automation ready

## 📂 Project Structure

```
bibtex-manager/
├── bib.py                    # Core application
├── bib_gui_modern.py        # Modern GUI (CustomTkinter)
├── bib_streamlit.py         # Web app interface
├── launch.sh                # Easy launcher for Mac/Linux
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── README_MAC_SETUP.md      # Mac-specific setup guide
├── ENHANCEMENTS.md          # Feature documentation
├── DEMO_CHECKLIST.md        # Demo preparation
└── test_data/               # Sample bibliography files
    ├── folder1/
    ├── folder2/
    └── folder3/
```

## 🧪 Test with Sample Data

The `test_data/` folder contains sample .bib files for testing:
```bash
python3 bib_gui_modern.py
# Click "Browse" → Select "test_data" folder
# Click "Analyze & Review"
# Inspect the proposed citation-key mappings in Key Review
# Confirm to create the processed project copy, then view results and the HTML report
```

Expected results:
- Files: 3
- Entries: 16
- Duplicate Groups: 4
- Entries Removed: 4
- Final Unique: 12

## 📋 How It Works

### The 4-Step Pipeline

1. **Crawl** 📁
   - Recursively searches the selected directory for `.bib` files and line-delimited `filecontents` / `filecontents*` blocks containing `.bib` files in `.tex` documents
   - Collects all bibliography entries
   - Preserves file information

2. **Detect Duplicates** 🔍
   - DOI matching for exact duplicates
   - Fuzzy title matching (60% weight)
   - Author name matching (30% weight)
   - Year bonus (+10%)
   - Configurable threshold (default 85%)

3. **Remove Duplicates** 🗑️
   - Intelligently merges duplicate groups
   - Keeps most complete entry
   - Merges missing fields from others
   - Eliminates redundant entries

4. **Normalize Keys** 🔑
   - Concatenates the first letter of each author's surname and adds the four-digit publication year (`Smith and Doe`, 2024 → `SD2024`)
   - Gives the first paper that author/year key; subsequent papers with the same initials and year receive `a`, `b`, `c` suffixes in source order (`SD2024`, `SD2024a`, `SD2024b`)
   - Uses `X` for records with no author surname and `0000` when no four-digit year is available
   - Scans source files in path order and keeps the entry order within each file, so suffixes are repeatable
   - Shows the exact old-to-new mappings in Key Review before writing output; after confirmation, creates a `processed` project folder beside the selected project with updated `.bib` and `.tex` files plus `master.bib`
   - Leaves the original files unchanged; later runs create a timestamped `processed_...` folder rather than replacing an existing result

For the web app, download the processed project ZIP and extract its top-level processed folder inside the Dropbox-synced project. That keeps the result as a nested folder in the existing Overleaf project; it does not create a separate Overleaf project.

The desktop GUI remembers the last selected project folder or source file in the current user's app settings and restores its preview on the next launch. It does not automatically run processing; use **Browse** to change projects. If the saved location is unavailable (for example, a disconnected drive), select the project again.

For an embedded `filecontents` bibliography, the processed copy keeps the block and updates its BibTeX keys and document citations. The app stops if an external file conflicts with the embedded filename, if the embedded filename is `master.bib`, or if the block is unclosed. Only blocks whose begin and end commands are on their own lines are recognized.

The app also reads literal `\bibitem` commands in `thebibliography` environments, including optional labels. It preserves their keys and formatting in the processed `.tex` rather than guessing author, title, or year from free-form text. The generated `master.bib` contains `@misc` entries with the reference text in `note`; these entries are not guaranteed to reproduce the manually formatted bibliography. Duplicate manual keys and conflicts with BibTeX keys must be resolved before processing. Macro-generated items are not supported.

Selecting an individual file scans its parent folder. For multiple separate projects in the desktop app:

1. Choose the parent folder and click **Analyze & Review**. Inspect the detected projects and click **Analyze projects**.
2. Review and mark each ready project in **Key Review**, then click **Process reviewed projects**. Cancelling stops the remaining batch; copies already created remain in place.
3. The dashboard lists completed, skipped, and failed projects and their output paths. Each completed project gets its own processed folder and `master.bib`. With HTML reports enabled, each report is inside its processed folder. Originals remain unchanged.

In **Documents**, select a completed project and a text file to preview it in the app. Supported UTF-8 files include `.tex`, `.bib`, `.txt`, `.md`, `.csv`, `.tsv`, `.json`, `.yaml`, `.yml`, `.sty`, `.cls`, `.cfg`, `.bst`, `.bbl`, `.ini`, `.log`, `.xml`, and `.html`. The viewer shows files in the processed copy; root-level project groups contain only their selected `.tex` and `.bib` files. For `.tex` files, jump between citations actually rewritten during processing. If the processed file is edited afterward, navigation is disabled because the saved positions may no longer be valid. Citations to duplicate entries removed during merging may remain unchanged; review them manually.

Generated `processed`, `processed_*`, and `backup_*` folders are excluded. The batch always creates processed copies, regardless of the single-project copy option.

### Dropbox and Overleaf

The app does not connect to Dropbox directly. With Overleaf's Dropbox integration enabled for the account, Dropbox syncs the contents of its `Apps/Overleaf` folder with Overleaf. The desktop app's processed copy is created inside the selected source folder, so it will appear as a nested folder in that existing Overleaf project if the source is already synced. To make the processed result a separate Overleaf project, place or copy the processed folder directly under `Dropbox/Apps/Overleaf` (not inside another project folder). Dropbox then syncs that top-level folder as its own project. Confirm the result in Overleaf before deleting or replacing any files.

### Safety Features

- **Originals Preserved** - The processed folder is a copy; source `.bib` and `.tex` files are not overwritten
- **Repeatable Output** - Existing processed results are kept and later runs use a timestamped folder
- **Safe Processing** - Validation at each step
- **Error Handling** - Graceful handling of corrupt or locked files

## 📊 Output

### Generated Files

1. **Processed project folder**
   - Clean, deduplicated bibliography
   - Normalized citation keys
   - Updated `.bib` and `.tex` files and a `master.bib`
   - Created beside the source project as `processed/` (or `processed_<timestamp>/`)

2. **HTML Report**
   - `report_YYYYMMDD_HHMMSS.html`
   - Beautiful, professional styling
   - Statistics and metrics
   - Duplicate analysis
   - Interactive elements

## 💡 Use Cases

**Researchers:**
- Merge bibliographies from multiple papers
- Clean up duplicates before submission
- Standardize citation keys across projects
- Generate professional reports

**Students:**
- Consolidate literature review references
- Identify duplicate sources
- Prepare clean bibliography for thesis
- Share analysis with advisors

**Librarians:**
- Deduplicate large collections
- Normalize citation formats
- Generate quality reports
- Non-technical web interface

## 🔧 Requirements

- Python 3.8+
- bibtexparser
- thefuzz
- python-Levenshtein
- customtkinter (for GUI)
- streamlit (for web app)
- plotly (for charts)
- pandas (for data tables)

See `requirements.txt` for exact versions.

## 🐛 Troubleshooting

**"No .bib files found"**
- Check directory path is correct
- Ensure .bib files exist in that directory
- Try absolute path instead of relative

**"Permission denied"**
- Files might be open in editor or other app
- Close files and try again
- Use test_data as a sanity check

**GUI won't launch**
- Use `python3 bib_gui_modern.py` explicitly
- Try web app instead: `streamlit run bib_streamlit.py`
- Check tkinter is installed: `python3 -m tkinter`

**Dependencies missing**
- Run: `pip install -r requirements.txt`
- On Mac, may need: `brew install python-tk`

See [README_MAC_SETUP.md](README_MAC_SETUP.md) for more Mac-specific troubleshooting.

## 📝 Example Workflow

```bash
# 1. Launch the application
python3 bib_gui_modern.py

# 2. Select directory with .bib files
Click "Browse" → Select folder

# 3. Configure settings
Similarity threshold: 85% (default)
Create processed copy: Yes
Generate report: Yes

# 4. Run pipeline
Click "Run Pipeline"

# 5. Review results
- See statistics
- View duplicate groups
- Download report
- Verify master.bib in folders

# 6. Check backups
- Original files in backup_[timestamp]/ folders
- Original folder structure preserved
```

## 📞 Support

For issues or questions:
1. Check [README_MAC_SETUP.md](README_MAC_SETUP.md) for troubleshooting
2. Review [ENHANCEMENTS.md](ENHANCEMENTS.md) for feature details
3. See [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) for demo preparation

## 📄 License

Educational project - Final Year Project 2026

## ✨ Created By

**Thomas** - Final Year Project  
BibTeX Bibliography Manager  
March 2026

---

**Ready to get started?**

1. Follow [README_MAC_SETUP.md](README_MAC_SETUP.md) for setup
2. Run with sample [test_data](test_data/)
3. Use with your own bibliography files
4. Check [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) before demonstrations

Happy deduplicating! 🎉
