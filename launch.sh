#!/bin/bash

# BibTeX Bibliography Manager - Mac Launch Script
# This makes it super easy to run on Mac without remembering commands

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📚 BibTeX Bibliography Manager${NC}"
echo "================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Setting up virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate venv
source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

echo ""
echo -e "${BLUE}Choose an option:${NC}"
echo "1) GUI (Modern Desktop Interface) 🎨"
echo "2) Web App (Browser Interface) 🌐"
echo "3) CLI (Command Line) 💻"
echo "4) Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}Launching GUI...${NC}"
        python3 bib_gui_modern.py
        ;;
    2)
        echo -e "${GREEN}Launching Web App...${NC}"
        echo "Opening http://localhost:8501 in your browser..."
        streamlit run bib_streamlit.py
        ;;
    3)
        echo -e "${GREEN}Launching CLI...${NC}"
        python3 bib.py
        ;;
    4)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
