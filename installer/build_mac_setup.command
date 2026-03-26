#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
chmod +x build_mac_setup.sh
./build_mac_setup.sh
read -n 1 -s -r -p "Press any key to close..."
