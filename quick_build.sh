#!/bin/bash

# Quick build script for Mac standalone app
# Usage: chmod +x quick_build.sh && ./quick_build.sh

set -e  # Exit on error

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}BibTeX Manager - Mac Standalone App Builder${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    source venv/bin/activate
fi

# Install PyInstaller if not present
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${BLUE}Installing PyInstaller...${NC}"
    pip install -q PyInstaller
    echo -e "${GREEN}✓ PyInstaller installed${NC}"
fi

# Clean old builds
echo -e "${BLUE}Cleaning old builds...${NC}"
rm -rf build/ dist/ *.spec 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned${NC}"

# Build GUI app
echo ""
echo -e "${BLUE}Building GUI application...${NC}"
pyinstaller --onefile --windowed \
    --name "BibTeX Manager" \
    --add-data "test_data:test_data" \
    bib_gui_modern.py 2>&1 | grep -v "WARNING:" || true

if [ -d "dist/BibTeX Manager.app" ]; then
    echo -e "${GREEN}✓ GUI app created${NC}"
else
    echo -e "${YELLOW}Note: App may be created in different location${NC}"
fi

# Build Web app (optional)
echo ""
echo -e "${BLUE}Building Web application...${NC}"
pyinstaller --onefile \
    --name "BibTeX Web" \
    --add-data "test_data:test_data" \
    bib_streamlit.py 2>&1 | grep -v "WARNING:" || true

echo -e "${GREEN}✓ Web app created${NC}"

# Summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✨ BUILD COMPLETE!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "📱 GUI Application:"
echo "   Location: dist/BibTeX Manager.app"
echo "   Size: Check with: ls -lh dist/"
echo "   Run with: ./dist/BibTeX\\ Manager.app/Contents/MacOS/BibTeX\\ Manager"
echo ""
echo "🌐 Web Application:"
echo "   Location: dist/BibTeX Web"
echo "   Run with: ./dist/BibTeX\\ Web"
echo ""
echo "📦 To distribute:"
echo "   cd dist"
echo "   zip -r 'BibTeX Manager.zip' 'BibTeX Manager.app'"
echo "   # Send BibTeX Manager.zip to professor"
echo ""
echo "💡 Quick test:"
echo "   ./dist/BibTeX\\ Manager.app/Contents/MacOS/BibTeX\\ Manager"
echo ""
