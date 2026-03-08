#!/usr/bin/env bash

OUT="/tmp/termorganism_proof"
rm -rf "$OUT"
mkdir -p "$OUT"

cat > "$OUT/broken_local.py" <<'PY2'
def x()
print("hi")
PY2

cat > "$OUT/broken_ai.py" <<'PY2'
print(helo")
PY2

echo "=== local repair ===" > "$OUT/repair_local.txt"
omega-autofix "$OUT/broken_local.py" >> "$OUT/repair_local.txt" 2>&1 || true
echo >> "$OUT/repair_local.txt"
python3 - <<'PY2' >> "$OUT/repair_local.txt" 2>&1
from pathlib import Path
print(Path("/tmp/termorganism_proof/broken_local.py").read_text())
PY2

echo "=== ai repair ===" > "$OUT/repair_ai.txt"
omega-autofix "$OUT/broken_ai.py" >> "$OUT/repair_ai.txt" 2>&1 || true
echo >> "$OUT/repair_ai.txt"
python3 - <<'PY2' >> "$OUT/repair_ai.txt" 2>&1
from pathlib import Path
print(Path("/tmp/termorganism_proof/broken_ai.py").read_text())
PY2

omega-stats > "$OUT/stats.txt" 2>&1 || true

echo "Proof bundle: $OUT"
