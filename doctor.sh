#!/usr/bin/env bash

echo "=== TermOrganism doctor ==="

command -v python3 >/dev/null 2>&1 && echo "OK: python3" || echo "MISS: python3"
command -v zsh >/dev/null 2>&1 && echo "OK: zsh" || echo "MISS: zsh"
python3 -c "import requests" >/dev/null 2>&1 && echo "OK: requests" || echo "MISS: requests"
[ -n "${GROQ_API_KEY:-}" ] && echo "OK: GROQ_API_KEY" || echo "WARN: GROQ_API_KEY not set"

[ -f "$HOME/.termorganism/core/autofix.py" ] && echo "OK: core/autofix.py" || echo "MISS: core/autofix.py"
[ -f "$HOME/.zsh/organism_guard.zsh" ] && echo "OK: organism_guard.zsh" || echo "MISS: organism_guard.zsh"

command -v omega-autofix >/dev/null 2>&1 && echo "OK: omega-autofix" || echo "MISS: omega-autofix"
command -v omega-stats >/dev/null 2>&1 && echo "OK: omega-stats" || echo "MISS: omega-stats"
