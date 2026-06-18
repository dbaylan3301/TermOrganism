#!/usr/bin/env bash
set -euo pipefail

echo "== prepare fixture =="
cat > /tmp/broken_runtime_hotforce.py <<'EOF'
print(open("logs/app.log").read())
EOF

echo
echo "== daemon hot_force minimal cli =="
time TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_runtime_hotforce.py --json
