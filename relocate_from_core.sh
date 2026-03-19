#!/usr/bin/env bash
set -Eeuo pipefail

# =========================================================
# TermOrganism auto-dispatch script
# core/ içindeki dosyaları uygun klasörlere taşır
# Kullanım:
#   bash relocate_from_core.sh           # gerçek taşıma
#   bash relocate_from_core.sh --dry-run # sadece ne yapacağını göster
# =========================================================

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

ROOT_DIR="$(pwd)"
CORE_DIR="$ROOT_DIR/core"

if [[ ! -d "$CORE_DIR" ]]; then
  echo "HATA: core klasörü bulunamadı: $CORE_DIR"
  exit 1
fi

# Hedef klasörler
mkdir -p \
  "$ROOT_DIR/bin" \
  "$ROOT_DIR/cli" \
  "$ROOT_DIR/runtime" \
  "$ROOT_DIR/engine" \
  "$ROOT_DIR/repair" \
  "$ROOT_DIR/memory" \
  "$ROOT_DIR/brain" \
  "$ROOT_DIR/ai" \
  "$ROOT_DIR/sandbox" \
  "$ROOT_DIR/utils" \
  "$ROOT_DIR/config" \
  "$ROOT_DIR/tests" \
  "$ROOT_DIR/demo" \
  "$ROOT_DIR/docs" \
  "$ROOT_DIR/scripts" \
  "$ROOT_DIR/logs"

log() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

move_file() {
  local src="$1"
  local dst="$2"

  if [[ "$src" == "$dst" ]]; then
    return 0
  fi

  if [[ -e "$dst" ]]; then
    warn "Atlandı (hedef zaten var): $dst"
    return 0
  fi

  mkdir -p "$(dirname "$dst")"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY] mv \"$src\" \"$dst\""
  else
    mv "$src" "$dst"
    echo "[MOVE] $src -> $dst"
  fi
}

pick_target_dir() {
  local base="$1"
  local lower
  lower="$(echo "$base" | tr '[:upper:]' '[:lower:]')"

  # Önce dosya adına göre akıllı eşleme
  case "$lower" in
    *cli*|*main*|*entry*|*command* )
      echo "cli"; return
      ;;
    *runtime*|*runner*|*exec*|*watch* )
      echo "runtime"; return
      ;;
    *engine*|*dispatcher*|*router* )
      echo "engine"; return
      ;;
    *repair*|*fix*|*heal*|*patch* )
      echo "repair"; return
      ;;
    *memory*|*history*|*state*|*cache* )
      echo "memory"; return
      ;;
    *brain*|*learn*|*predict*|*model* )
      echo "brain"; return
      ;;
    *ai*|*llm*|*groq*|*openai* )
      echo "ai"; return
      ;;
    *sandbox*|*verify*|*validator* )
      echo "sandbox"; return
      ;;
    *util*|*helper*|*common* )
      echo "utils"; return
      ;;
    *config*|*settings*|*.env* )
      echo "config"; return
      ;;
    test_*|*_test.py|test_*.py|*.spec.py|*.test.py )
      echo "tests"; return
      ;;
    *demo*|example_*|*.demo.py )
      echo "demo"; return
      ;;
    readme*|*.md )
      echo "docs"; return
      ;;
    *.sh )
      echo "scripts"; return
      ;;
  esac

  # Uzantıya göre fallback
  case "$lower" in
    *.py ) echo "core"; return ;;
    *.json|*.toml|*.yaml|*.yml|*.ini|*.cfg ) echo "config"; return ;;
    *.md|*.rst|*.txt ) echo "docs"; return ;;
    *.sh ) echo "scripts"; return ;;
    * ) echo "utils"; return ;;
  esac
}

log "core içeriği taranıyor: $CORE_DIR"

mapfile -t FILES < <(find "$CORE_DIR" -maxdepth 1 -type f | sort)

if [[ "${#FILES[@]}" -eq 0 ]]; then
  warn "core içinde taşınacak dosya bulunamadı."
  exit 0
fi

for src in "${FILES[@]}"; do
  filename="$(basename "$src")"
  target_subdir="$(pick_target_dir "$filename")"

  # core klasöründe kalmasını istediğimiz dosyalar için özel durum
  if [[ "$target_subdir" == "core" ]]; then
    log "core içinde bırakıldı: $filename"
    continue
  fi

  dst="$ROOT_DIR/$target_subdir/$filename"
  move_file "$src" "$dst"
done

log "İşlem tamamlandı."

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Bu bir dry-run idi. Gerçek taşımak için --dry-run olmadan çalıştır."
fi
