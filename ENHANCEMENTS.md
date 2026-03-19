# 📚 BibTeX Bibliography Manager - Enhanced Edition

A comprehensive bibliography management tool with CLI, modern GUI, and web interfaces.

## 🎨 New Enhancements (Feb 8, 2026)

### 1. ✨ HTML Report Generation

Every pipeline run now generates a beautiful, detailed HTML report with:

- **Executive Summary** - Key statistics at a glance
- **Interactive Visualizations** - Colored charts and graphs
- **Duplicate Analysis** - Full breakdown of each duplicate group with similarity scores
- **Citation Key Changes** - Before/after comparison of normalized keys
- **Responsive Design** - Beautiful gradient styling, hover effects

**Usage:**
```python
manager = BibliographyManager(directory)
manager.run_full_pipeline(generate_report=True)
# Report saved as report_TIMESTAMP.html
```

### 2. 🎨 Modern GUI (CustomTkinter)

Upgraded desktop application with modern aesthetics:

**Features:**
- **Dark/Light Mode** - System-aware with manual toggle
- **Modern Design** - Rounded buttons, smooth animations, gradient colors
- **Sidebar Controls** - Clean, organized layout
- **Real-time Progress** - Live log updates with colored output
- **Statistics Dashboard** - Metric cards showing all key stats
- **Report Viewer** - Open HTML reports directly from GUI

**Run:**
```bash
python bib_gui_modern.py
```

### 3. 🌐 Streamlit Web App

Cloud-ready web interface accessible from any device:

**Features:**
- **File Upload** - Drag-and-drop .bib files or specify directory
- **Live Processing** - Real-time progress bar and status updates
- **Interactive Charts** - Plotly pie charts and bar graphs
- **Tabbed Interface** - Visualization, Duplicates, Key Changes, Summary
- **Download Results** - Export master.bib directly
- **Responsive** - Works on desktop, tablet, mobile

**Run:**
```bash
streamlit run bib_streamlit.py
```

**Deploy to Cloud (Free):**
```bash
# Push to GitHub
git add .
git commit -m "Add streamlit app"
git push

# Deploy on Streamlit Cloud (streamlit.io/cloud)
# Free hosting, automatic updates from GitHub
```

## 📦 Installation

### Dependencies

**Core (CLI):**
```bash
pip install bibtexparser thefuzz python-Levenshtein
```

**Modern GUI:**
```bash
pip install customtkinter
```

**Web App:**
```bash
pip install streamlit plotly
```

**Install All:**
```bash
pip install bibtexparser thefuzz python-Levenshtein customtkinter streamlit plotly
```

## 🚀 Usage

### Option 1: Command Line (CLI)
```bash
python bib.py
```
- Interactive menu
- Step-by-step or automatic mode
- Configurable threshold
- Automatic HTML report generation

### Option 2: Modern Desktop GUI
```bash
python bib_gui_modern.py
```
- Beautiful dark/light theme
- Drag-and-drop directory selection
- Real-time processing logs
- Statistics dashboard
- One-click report viewing

### Option 3: Web Interface
```bash
streamlit run bib_streamlit.py
```
- Access from any browser
- Upload files or use directory
- Interactive visualizations
- Download processed results
- Share via cloud deployment

## 📊 Report Features

### HTML Report Includes:

1. **Statistics Cards**
   - Files processed
   - Initial/final entry counts
   - Duplicate groups found
   - Processing time

2. **Duplicate Groups**
   - Each group with similarity percentage
   - Visual badges (KEPT/REMOVED)
   - Full entry details (title, author, year, DOI)
   - Color-coded for easy scanning

3. **Citation Key Changes**
   - Before → After view
   - First 20 changes shown
   - Consistent formatting applied

4. **Processing Summary**
   - Reduction rate percentage
   - Quality metrics
   - Backup confirmation

### Example Report Output:
```
📁 Files: 10
📝 Initial: 100
🔄 Groups: 12
🗑️ Removed: 88
✅ Final: 12
⚡ Time: 2.3s

✓ 88.0% Duplicate Reduction Rate
```

## 🎯 Feature Comparison

| Feature | CLI | GUI (tkinter) | GUI (Modern) | Web App |
|---------|-----|---------------|--------------|---------|
| Duplicate Detection | ✅ | ✅ | ✅ | ✅ |
| HTML Reports | ✅ | ✅ | ✅ | ✅ |
| Beautiful UI | ❌ | ⚠️ Basic | ✅ Modern | ✅ Modern |
| Dark Mode | ❌ | ❌ | ✅ | ✅ |
| Charts/Graphs | ❌ | ❌ | ❌ | ✅ |
| File Upload | ❌ | ❌ | ❌ | ✅ |
| Cloud Deploy | ❌ | ❌ | ❌ | ✅ |
| No Install | ❌ | ❌ | ❌ | ✅ (cloud) |

## 🔥 Quick Start Examples

### Generate Report from CLI:
```bash
python bib.py
# Select option 1 (Run full pipeline)
# Enter directory: test_data
# Push to folders: y
# Report automatically generated!
```

### Modern GUI Workflow:
```bash
python bib_gui_modern.py
# 1. Click "Browse" and select test_data folder
# 2. Adjust similarity slider (85% recommended)
# 3. Check "Generate HTML report"
# 4. Click "Run Pipeline"
# 5. Watch real-time progress
# 6. Click "View Report" to see results
```

### Web App with Upload:
```bash
streamlit run bib_streamlit.py
# 1. Select "Upload Files"
# 2. Drag .bib files into upload box
# 3. Set threshold with slider
# 4. Click "Run Pipeline"
# 5. View interactive charts
# 6. Download master.bib
```

## 📸 Screenshots

### HTML Report
- Beautiful gradient headers
- Color-coded duplicate groups (green=kept, red=removed)
- Responsive cards with hover effects
- Professional typography

### Modern GUI
- Dark theme with accent colors
- Sidebar controls with icons
- Tabbed interface (Pipeline, Results, Duplicates, About)
- Progress bar with real-time updates

### Web App
- Material design aesthetics
- Interactive Plotly charts
- Metric cards showing statistics
- Expandable duplicate group panels

## 🛠️ Technical Details

### Report Generation
- Pure HTML/CSS with inline styles
- No external dependencies
- Gradient backgrounds: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- Responsive layout with flexbox/grid
- Hover animations for interactivity

### Modern GUI (CustomTkinter)
- Based on tkinter, fully compatible
- Cross-platform (Windows, macOS, Linux)
- Dark mode auto-detection
- Smooth animations
- Modern color palette

### Web App (Streamlit)
- Built-in caching for performance
- Session state management
- Plotly for interactive charts
- Pandas for data tables
- Deployable to Streamlit Cloud (free tier available)

## 📝 Project Structure

```
IERG FYP/
├── bib.py                  # Core CLI with HTML reports
├── bib_gui.py             # Original tkinter GUI
├── bib_gui_modern.py      # Modern CustomTkinter GUI ⭐ NEW
├── bib_streamlit.py       # Streamlit web app ⭐ NEW
├── test_data/             # Sample .bib files
│   ├── folder1/
│   ├── folder2/
│   └── folder3/
├── master.bib             # Generated output
└── report_*.html          # Generated reports ⭐ NEW
```

## 🎓 Use Cases

### For Researchers:
- Merge bibliographies from multiple papers
- Clean up duplicates before submission
- Standardize citation keys across projects
- Generate reports for documentation

### For Students:
- Consolidate references from literature review
- Identify duplicate sources
- Prepare clean bibliography for thesis
- Share web app with supervisors

### For Librarians:
- Deduplicate large bibliography collections
- Normalize citation formats
- Generate quality reports
- Web interface for non-technical users

## 🚀 Next Steps

**Try it out:**
```bash
# Test with sample data
python bib_gui_modern.py
# Browse to test_data folder
# Click "Run Pipeline"
# View beautiful HTML report!
```

**Deploy web app:**
```bash
# Run locally first
streamlit run bib_streamlit.py

# Deploy to cloud (requires GitHub)
# 1. Push code to GitHub
# 2. Go to share.streamlit.io
# 3. Connect repository
# 4. Deploy with one click!
```

## 📧 Contact

Created by Thomas for Final Year Project 2026

---

**Enjoy the enhanced bibliography manager! 🎉**
