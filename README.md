# 📚 BibTeX Bibliography Manager

A comprehensive, cross-platform tool for managing, deduplicating, and organizing BibTeX bibliography files. Built for researchers and students who need to consolidate references from multiple sources.

## ✨ Key Features

- **🔍 Intelligent Duplicate Detection** - Fuzzy matching for similar entries, DOI verification for exact matches
- **🗑️ Smart Deduplication** - Merges duplicates intelligently, keeps most complete entry
- **🔑 Citation Key Normalization** - Standardizes citation keys to `firstname-year-keyword` format
- **📂 Batch Processing** - Crawls folders recursively, processes hundreds of files
- **💾 Automatic Backups** - Timestamped backups created before any changes
- **📊 Beautiful HTML Reports** - Professional reports with statistics and duplicate analysis
- **🎨 Modern GUI** - CustomTkinter interface with dark/light mode
- **🌐 Web App** - Streamlit interface for cloud deployment
- **💻 CLI** - Full command-line control for automation

## 🚀 Quick Start

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
# Click "Run Pipeline"
# View results and generated HTML report
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
   - Recursively searches directory for .bib files
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
   - Generates consistent citation keys
   - Format: `firstname-year-keyword`
   - Ensures uniqueness with suffixes
   - Maintains valid BibTeX format

### Safety Features

- **Automatic Backups** - Timestamped backup folders created before changes
- **No Data Loss** - Original files preserved, can restore anytime
- **Safe Processing** - Validation at each step
- **Error Handling** - Graceful handling of corrupt or locked files

## 📊 Output

### Generated Files

1. **master.bib**
   - Clean, deduplicated bibliography
   - Normalized citation keys
   - Distributed to original folders

2. **Backup Folders**
   - `backup_YYYYMMDD_HHMMSS/` in each directory
   - Original files preserved
   - Can restore if needed

3. **HTML Report**
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
Push to folders: Yes
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
