#!/usr/bin/env bash
# Startet alle Tests: Python (pytest) und Oberfläche (jsdom).
set -euo pipefail
cd "$(dirname "$0")/.."
( cd solasi/tests/ui && { [ -d node_modules ] || npm install --no-audit --no-fund --silent; } )   # jsdom auch für die Python-Tests
echo "== Python-Tests"
( cd solasi && python3 -m pytest -q )
echo "== Oberflächen-Tests"
( cd solasi/tests/ui && npm test --silent )
echo "Alles in Ordnung."
