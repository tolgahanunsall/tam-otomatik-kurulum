#!/bin/bash
# ============================================================
# Note Backup Tool - Linux/macOS Kurulum Scripti
# ============================================================

set -e

echo "========================================"
echo "  Note Backup Tool - Kurulum"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check Python
echo "Python kontrol ediliyor..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}[HATA] Python bulunamadi! Python 3.8+ yukleyin.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}[OK] $PYTHON_VERSION${NC}"

# Check pip
echo "pip kontrol ediliyor..."
if ! $PYTHON -m pip --version &> /dev/null; then
    echo -e "${RED}[HATA] pip bulunamadi! pip yukleyin.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] pip mevcut${NC}"

# Create virtual environment
echo ""
echo "Sanal ortam olusturuluyor..."
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[INFO] Sanal ortam zaten mevcut, atlanıyor...${NC}"
else
    $PYTHON -m venv "$VENV_DIR"
    echo -e "${GREEN}[OK] Sanal ortam olusturuldu: $VENV_DIR${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo ""
echo "Bagimliliklar yukleniyor..."
pip install -r "$PROJECT_DIR/requirements.txt" --quiet
echo -e "${GREEN}[OK] Bagimliliklar yuklendi${NC}"

# Create config directory
CONFIG_DIR="$HOME/.note-backup"
mkdir -p "$CONFIG_DIR"

# Copy example config if no config exists
if [ ! -f "$PROJECT_DIR/config.yaml" ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo ""
    echo "Ornek yapilandirma dosyasi kopyalaniyor..."
    cp "$PROJECT_DIR/config.example.yaml" "$PROJECT_DIR/config.yaml"
    echo -e "${GREEN}[OK] config.yaml olusturuldu${NC}"
    echo -e "${YELLOW}[ONEMLI] Lutfen config.yaml dosyasini duzenleyin!${NC}"
fi

# Make backup.py executable
chmod +x "$PROJECT_DIR/backup.py"

echo ""
echo "========================================"
echo -e "${GREEN}  Kurulum Tamamlandi!${NC}"
echo "========================================"
echo ""
echo "Sonraki adimlar:"
echo "  1. config.yaml dosyasini duzenleyin:"
echo "     nano $PROJECT_DIR/config.yaml"
echo ""
echo "  2. Test yedeklemesi yapin:"
echo "     cd $PROJECT_DIR"
echo "     source venv/bin/activate"
echo "     python backup.py"
echo ""
echo "  3. Otomatik zamanlama kurun:"
echo "     python backup.py schedule install"
echo ""
