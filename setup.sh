#!/usr/bin/env bash
# Recreate the exact environment on any machine (macOS / Linux).
#   ./setup.sh            # uses requirements.lock (exact versions, recommended)
#   ./setup.sh --latest   # resolves fresh from requirements.txt
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 9), "Python 3.9+ required"'

if ! command -v tesseract >/dev/null; then
  echo "Tesseract not found. Install it first:"
  echo "  macOS:  brew install tesseract"
  echo "  Debian: sudo apt install tesseract-ocr"
  exit 1
fi

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip

if [ "${1:-}" = "--latest" ]; then
  .venv/bin/pip install -q -r requirements.txt
else
  .venv/bin/pip install -q -r requirements.lock
fi

.venv/bin/python -m spacy download en_core_web_lg -q
.venv/bin/playwright install chromium

.venv/bin/python - <<'PY'
import spacy, presidio_analyzer, pytesseract
from playwright.sync_api import sync_playwright
spacy.load("en_core_web_lg")
print("tesseract", pytesseract.get_tesseract_version())
with sync_playwright() as p:
    p.chromium.launch().close()
print("environment OK — activate with: source .venv/bin/activate")
PY
