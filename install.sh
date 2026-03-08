#!/usr/bin/env bash

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME/.termorganism/core" "$HOME/.termorganism/memory" "$HOME/.zsh" "$HOME/bin"

cp -f "$REPO_DIR/core/"*.py "$HOME/.termorganism/core/" 2>/dev/null || true
cp -f "$REPO_DIR/bin/"* "$HOME/bin/" 2>/dev/null || true
cp -f "$REPO_DIR/zsh/"*.zsh "$HOME/.zsh/" 2>/dev/null || true

chmod +x "$HOME/bin/"* 2>/dev/null || true

python3 - <<'PY2'
from pathlib import Path
base = Path.home() / ".termorganism" / "memory"
base.mkdir(parents=True, exist_ok=True)
for name in ("commands.json", "repairs.json"):
    p = base / name
    if not p.exists() or not p.read_text(encoding="utf-8", errors="ignore").strip():
        p.write_text("[]\n", encoding="utf-8")
PY2

for line in \
'export PATH="$HOME/bin:$PATH"' \
'source ~/.zsh/organism_guard.zsh' \
'source ~/.zsh/organism_brain.zsh' \
'source ~/.zsh/context.zsh' \
'source ~/.zsh/suggest.zsh' \
"alias python='organism_exec_guard python3'" \
"alias python3='organism_exec_guard python3'"
do
  grep -Fqx "$line" "$HOME/.zshrc" 2>/dev/null || echo "$line" >> "$HOME/.zshrc"
done

echo "OK: TermOrganism installed"
echo "Run: source ~/.zshrc"
