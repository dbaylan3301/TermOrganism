#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. HOT FORCE MODE (Hedef: < 500ms) ==="
time TERMORGANISM_HOT_FORCE=1 python3 -u ./termorganism repair demo/broken_runtime.py --json 2>/dev/null

echo
echo "=== 2. FAST V2 MODE (Hedef: miss reason görünür) ==="
time TERMORGANISM_FAST_V2=1 python3 -u ./termorganism repair demo/broken_runtime.py --json --fast 2>/dev/null

echo
echo "=== 3. NORMAL MODE (Mevcut) ==="
time python3 -u ./termorganism repair demo/broken_runtime.py --json 2>/dev/null
