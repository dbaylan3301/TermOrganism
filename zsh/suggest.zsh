organism_last_suggest=""

organism_project_suggest() {
  local msg=""

  if [[ -f package.json ]]; then
    msg="[organism] suggest: npm run dev"
    if command -v python3 >/dev/null 2>&1; then
      local detected
      detected="$(python3 -c '
import json
from pathlib import Path
p = Path("package.json")
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    for key in ("dev", "start", "test", "build"):
        if key in scripts:
            print(f"[organism] suggest: npm run {key}")
            raise SystemExit
except Exception:
    pass
print("[organism] suggest: npm run dev")
' 2>/dev/null)"
      [[ -n "$detected" ]] && msg="$detected"
    fi

  elif [[ -f pyproject.toml || -f requirements.txt || -f setup.py ]]; then
    if [[ ! -d .venv ]]; then
      msg="[organism] suggest: python3 -m venv .venv"
    elif [[ -f pyproject.toml ]]; then
      msg="[organism] suggest: pytest"
    else
      msg="[organism] suggest: python main.py"
    fi

  elif [[ -f Cargo.toml ]]; then
    msg="[organism] suggest: cargo run"

  elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
      msg="[organism] suggest: lazygit"
    fi
  fi

  print -r -- "$msg"
}

organism_suggest() {
  local msg=""

  if typeset -f organism_memory_suggest >/dev/null 2>&1; then
    msg="$(organism_memory_suggest 2>/dev/null)"
  fi

  if [[ -z "$msg" ]]; then
    msg="$(organism_project_suggest)"
  fi

  if [[ -n "$msg" && "$msg" != "$organism_last_suggest" ]]; then
    print -r -- "$msg"
    organism_last_suggest="$msg"
  fi
}
