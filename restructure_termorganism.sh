#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(pwd)"
SRC="$ROOT/core"

if [[ ! -d "$SRC" ]]; then
  echo "HATA: core klasörü bulunamadı: $SRC"
  exit 1
fi

echo "[INFO] Proje kökü: $ROOT"
echo "[INFO] Kaynak klasör: $SRC"

# Hedef klasörler
mkdir -p "$ROOT/core/engine"
mkdir -p "$ROOT/core/experts"
mkdir -p "$ROOT/core/memory"
mkdir -p "$ROOT/core/models"
mkdir -p "$ROOT/core/util"
mkdir -p "$ROOT/core/verify"
mkdir -p "$ROOT/memory/TermOrganism"

# __init__.py dosyaları
touch "$ROOT/core/__init__.py"
touch "$ROOT/core/engine/__init__.py"
touch "$ROOT/core/experts/__init__.py"
touch "$ROOT/core/memory/__init__.py"
touch "$ROOT/core/models/__init__.py"
touch "$ROOT/core/util/__init__.py"
touch "$ROOT/core/verify/__init__.py"

# memory jsonl
touch "$ROOT/memory/TermOrganism/repair_events.jsonl"

move_if_exists() {
  local src="$1"
  local dst="$2"

  if [[ -f "$src" ]]; then
    if [[ -e "$dst" ]]; then
      echo "[SKIP] Hedef zaten var: $dst"
    else
      mkdir -p "$(dirname "$dst")"
      mv "$src" "$dst"
      echo "[MOVE] $(basename "$src") -> ${dst#$ROOT/}"
    fi
  else
    echo "[MISS] Yok: ${src#$ROOT/}"
  fi
}

# -------------------------
# ROOT/core altında kalacaklar
# -------------------------
move_if_exists "$SRC/autofix.py" "$ROOT/core/autofix.py"

# -------------------------
# engine
# -------------------------
move_if_exists "$SRC/context_builder.py" "$ROOT/core/engine/context_builder.py"
move_if_exists "$SRC/orchestrator.py"    "$ROOT/core/engine/orchestrator.py"
move_if_exists "$SRC/ranker.py"          "$ROOT/core/engine/ranker.py"
move_if_exists "$SRC/router.py"          "$ROOT/core/engine/router.py"

# -------------------------
# experts
# -------------------------
move_if_exists "$SRC/base.py"              "$ROOT/core/experts/base.py"
move_if_exists "$SRC/dependency.py"        "$ROOT/core/experts/dependency.py"
move_if_exists "$SRC/llm_fallback.py"      "$ROOT/core/experts/llm_fallback.py"
move_if_exists "$SRC/memory_retrieval.py"  "$ROOT/core/experts/memory_retrieval.py"
move_if_exists "$SRC/python_syntax.py"     "$ROOT/core/experts/python_syntax.py"
move_if_exists "$SRC/shell_runtime.py"     "$ROOT/core/experts/shell_runtime.py"

# -------------------------
# core/memory
# -------------------------
move_if_exists "$SRC/event_store.py" "$ROOT/core/memory/event_store.py"
move_if_exists "$SRC/retrieval.py"   "$ROOT/core/memory/retrieval.py"
move_if_exists "$SRC/stats.py"       "$ROOT/core/memory/stats.py"

# -------------------------
# models
# -------------------------
move_if_exists "$SRC/schemas.py" "$ROOT/core/models/schemas.py"

# -------------------------
# util
# -------------------------
move_if_exists "$SRC/diffing.py"       "$ROOT/core/util/diffing.py"
move_if_exists "$SRC/fingerprints.py"  "$ROOT/core/util/fingerprints.py"
move_if_exists "$SRC/logging.py"       "$ROOT/core/util/logging.py"

# -------------------------
# verify
# -------------------------
move_if_exists "$SRC/python_verify.py" "$ROOT/core/verify/python_verify.py"
move_if_exists "$SRC/sandbox.py"       "$ROOT/core/verify/sandbox.py"

echo
echo "[INFO] Kalan düz dosyalar (taşınmamış olanlar):"
find "$SRC" -maxdepth 1 -type f | sort || true

echo
echo "[INFO] Son yapı:"
find "$ROOT/core" -maxdepth 3 | sort
echo
find "$ROOT/memory" -maxdepth 3 | sort

echo
echo "[DONE] Yeniden yapılandırma tamamlandı."
