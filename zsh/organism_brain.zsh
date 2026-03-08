# ===== organism brain =====

typeset -g ORGANISM_LAST_CMD=""
typeset -g organism_last_suggest=""

organism_preexec_log() {
  ORGANISM_LAST_CMD="$1"
}

organism_precmd_log() {
  if [[ -n "${ORGANISM_LAST_CMD:-}" ]]; then
    if command -v omega-brain-log >/dev/null 2>&1; then
      omega-brain-log "$ORGANISM_LAST_CMD" >/dev/null 2>&1
    fi
    ORGANISM_LAST_CMD=""
  fi
}

organism_memory_suggest() {
  local learned=""
  if command -v omega-brain-suggest >/dev/null 2>&1; then
    learned="$(omega-brain-suggest 2>/dev/null)"
  fi

  if [[ -n "$learned" ]]; then
    print "[organism] learned: $learned"
    return 0
  fi
  return 1
}

autoload -Uz add-zsh-hook 2>/dev/null || true

# idempotent hook install
if ! typeset -p preexec_functions 2>/dev/null | grep -q 'organism_preexec_log'; then
  preexec_functions+=(organism_preexec_log)
fi

if ! typeset -p precmd_functions 2>/dev/null | grep -q 'organism_precmd_log'; then
  precmd_functions+=(organism_precmd_log)
fi

# ===== end organism brain =====
