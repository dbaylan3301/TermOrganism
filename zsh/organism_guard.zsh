organism_exec_guard() {
  local runner="$1"
  shift

  local target="$1"
  shift

  case "$target" in
    *.py)
      if command -v omega-autofix >/dev/null 2>&1; then
        omega-autofix "$target"
      fi
      command "$runner" "$target" "$@"
      return
      ;;
    *.sh|*.zsh)
      command "$runner" "$target" "$@"
      return
      ;;
  esac

  command "$runner" "$target" "$@"
}
