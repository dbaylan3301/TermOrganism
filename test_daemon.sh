#!/usr/bin/env bash
set -euo pipefail

echo "=== start daemon in another terminal first ==="
echo "python3 -m core.daemon.server"

echo
echo "=== hot force via daemon ==="
time TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 python3 -u ./termorganism repair /tmp/broken_runtime_hotforce.py --json

echo
echo "=== fast via daemon ==="
time TERMORGANISM_USE_DAEMON=1 TERMORGANISM_FAST_V2=1 python3 -u ./termorganism repair demo/broken_runtime.py --json --fast

echo
echo "=== normal via daemon ==="
time TERMORGANISM_USE_DAEMON=1 python3 -u ./termorganism repair demo/broken_runtime.py --json
