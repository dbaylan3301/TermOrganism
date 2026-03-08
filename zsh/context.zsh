organism_context() {
  if [[ -f package.json ]]; then
    echo "[node]"
    return
  fi

  if [[ -f pyproject.toml || -f requirements.txt || -f setup.py ]]; then
    echo "[python]"
    return
  fi

  if [[ -f Cargo.toml ]]; then
    echo "[rust]"
    return
  fi

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[git]"
    return
  fi
}
