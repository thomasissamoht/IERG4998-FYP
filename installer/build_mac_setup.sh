#!/usr/bin/env bash
set -euo pipefail

APP_NAME="BibTeX Manager"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f VERSION ]]; then
  VERSION="$(tr -d '[:space:]' < VERSION)"
else
  VERSION="1.0.0"
fi

OUT_DIR="installer/output"
APP_BUNDLE="dist/${APP_NAME}.app"
ZIP_OUT="${OUT_DIR}/BibTeXManager-mac-${VERSION}.zip"
DMG_OUT="${OUT_DIR}/BibTeXManager-mac-${VERSION}.dmg"
ICON_PATH="installer/app.icns"

mkdir -p "$OUT_DIR"

echo "==============================================="
echo "Build BibTeX Manager macOS package"
echo "==============================================="

echo "[1/4] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first."
  exit 1
fi

echo "[2/4] Preparing virtual environment..."
if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo "[3/4] Building .app..."
rm -rf build dist "${APP_NAME}.spec"

ICON_ARGS=()
if [[ -f "$ICON_PATH" ]]; then
  echo "Using icon: $ICON_PATH"
  ICON_ARGS=(--icon "$ICON_PATH")
else
  echo "No mac icon found at $ICON_PATH (continuing without custom icon)."
fi

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --collect-all customtkinter \
  --hidden-import bibtexparser.bparser \
  --hidden-import bibtexparser.bwriter \
  --hidden-import bibtexparser.bibdatabase \
  --add-data "test_data:test_data" \
  "${ICON_ARGS[@]}" \
  bib_gui_modern.py

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Expected app bundle not found: $APP_BUNDLE"
  exit 1
fi

echo "[4/4] Packaging for distribution..."
rm -f "$ZIP_OUT" "$DMG_OUT"

# Always create zip as fallback.
(cd dist && zip -r "../$ZIP_OUT" "${APP_NAME}.app" >/dev/null)

if command -v hdiutil >/dev/null 2>&1; then
  hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$APP_BUNDLE" \
    -ov \
    -format UDZO \
    "$DMG_OUT" >/dev/null
  echo "SUCCESS: $DMG_OUT"
else
  echo "hdiutil not found; DMG skipped (zip created instead)."
fi

echo "SUCCESS: $ZIP_OUT"
echo ""
echo "Distribute to Mac users:"
echo "  Preferred: $DMG_OUT"
echo "  Fallback:  $ZIP_OUT"
