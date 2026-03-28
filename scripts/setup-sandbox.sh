#!/usr/bin/env bash
set -euo pipefail

echo "[sandbox] optional setup starting"

if command -v curl >/dev/null 2>&1; then
  echo "[sandbox] gVisor install hint:"
  echo "  curl -fsSL https://gvisor.dev/install.sh | bash"
fi

echo "[sandbox] Firecracker expected paths:"
echo "  TERMORGANISM_FIRECRACKER_BIN=/usr/local/bin/firecracker"
echo "  TERMORGANISM_FIRECRACKER_HELPER=./scripts/termorganism-firecracker-run"

echo "[sandbox] current integration is opt-in."
echo "[sandbox] example:"
echo "  termorganism repair demo/broken_import.py --sandbox-backend gvisor"
