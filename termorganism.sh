#!/usr/bin/env bash
set -euo pipefail

SOCKET="${TERMORGANISM_SOCKET:-/tmp/termorganism.sock}"

usage() {
  printf '%s\n' '{"error":"Usage: ./termorganism.sh repair <file> [--json]"}'
  exit 1
}

[[ $# -ge 2 ]] || usage
[[ "$1" == "repair" ]] || usage

FILE="${2:-}"
[[ -n "$FILE" ]] || usage

MODE="auto"
if [[ "${TERMORGANISM_HOT_FORCE:-}" =~ ^(1|true|yes|on)$ ]]; then
  MODE="hot_force"
elif printf '%s\n' "$*" | grep -q -- '--fast'; then
  MODE="fast"
fi

if [[ ! -S "$SOCKET" ]]; then
  printf '%s\n' "{\"success\":false,\"mode\":\"shell_client\",\"error\":\"daemon socket not found: $SOCKET\"}"
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  printf '%s\n' "{\"success\":false,\"mode\":\"shell_client\",\"error\":\"target does not exist: $FILE\"}"
  exit 1
fi

SIGNATURE=""
if [[ "$MODE" == "hot_force" ]]; then
  HEAD_CONTENT="$(head -c 4096 "$FILE" 2>/dev/null || true)"
  if printf '%s' "$HEAD_CONTENT" | grep -q 'open('; then
    if printf '%s' "$HEAD_CONTENT" | grep -q '\.read()'; then
      SIGNATURE="filenotfounderror:open:runtime"
    fi
  fi
  if [[ -z "$SIGNATURE" ]] && printf '%s' "$HEAD_CONTENT" | grep -q 'read_text('; then
    SIGNATURE="filenotfounderror:open:runtime"
  fi
  if [[ -z "$SIGNATURE" ]] && printf '%s\n' "$HEAD_CONTENT" | grep -Eq '^[[:space:]]*import[[:space:]]+[A-Za-z_][A-Za-z0-9_]*([[:space:]]+as[[:space:]]+[A-Za-z_][A-Za-z0-9_]*)?[[:space:]]*$'; then
    SIGNATURE="importerror:no_module_named"
  fi
  if [[ -z "$SIGNATURE" ]] && printf '%s\n' "$HEAD_CONTENT" | grep -Eq '^[[:space:]]*from[[:space:]]+[A-Za-z_][A-Za-z0-9_\.]*[[:space:]]+import[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*$'; then
    SIGNATURE="importerror:no_module_named"
  fi
fi

if [[ -n "$SIGNATURE" && "$MODE" == "hot_force" ]]; then
  PAYLOAD=$(printf '{"fast_path":"hot_force","file":"%s","signature":"%s","mode":"hot_force"}' "$FILE" "$SIGNATURE")
else
  PAYLOAD=$(printf '{"file":"%s","mode":"%s","context":{"file":"%s","hint":"minimal_shell"}}' "$FILE" "$MODE" "$FILE")
fi

if command -v socat >/dev/null 2>&1; then
  printf '%s' "$PAYLOAD" | socat - UNIX-CONNECT:"$SOCKET"
  exit $?
fi

CLIENT_TIMEOUT="${TERMORGANISM_CLIENT_TIMEOUT:-30}"
PAYLOAD_JSON="$PAYLOAD" SOCKET_PATH="$SOCKET" CLIENT_TIMEOUT="$CLIENT_TIMEOUT" python3 - <<'PY2'
import os
import socket
import sys

payload = os.environ["PAYLOAD_JSON"].encode("utf-8")
socket_path = os.environ["SOCKET_PATH"]

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(float(os.environ.get("CLIENT_TIMEOUT", "30")))
sock.connect(socket_path)
sock.sendall(payload)
sock.shutdown(socket.SHUT_WR)

buf = b""
while True:
    chunk = sock.recv(65536)
    if not chunk:
        break
    buf += chunk
sock.close()

sys.stdout.write(buf.decode("utf-8"))
PY2
