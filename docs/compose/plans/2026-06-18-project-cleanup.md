# TermOrganism Project Cleanup & Professionalization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all identified issues, clean up the project structure, and make it professionally organized.

**Architecture:** Phased approach — cleanup first, then critical fixes, then configuration and quality improvements.

**Tech Stack:** Python 3.10+, Bash, Git

---

### Task 1: Create _archive/ and move orphaned files

**Covers:** Root clutter cleanup

**Files:**
- Create: `_archive/` directory
- Move: All `patch_*.py`, `phase*.py`, and other orphaned root scripts

- [ ] **Step 1: Create archive directory**

```bash
mkdir -p /home/craftzzdog/TermOrganism/_archive
```

- [ ] **Step 2: Move patch files**

```bash
mv /home/craftzzdog/TermOrganism/patch_*.py /home/craftzzdog/TermOrganism/_archive/
```

- [ ] **Step 3: Move phase files**

```bash
mv /home/craftzzdog/TermOrganism/phase*.py /home/craftzzdog/TermOrganism/_archive/
```

- [ ] **Step 4: Move other orphaned scripts**

```bash
mv /home/craftzzdog/TermOrganism/bootstrap_missing_modules.py /home/craftzzdog/TermOrganism/_archive/
mv /home/craftzzdog/TermOrganism/create_integration_fixtures.py /home/craftzzdog/TermOrganism/_archive/
mv /home/craftzzdog/TermOrganism/planner_probe.py /home/craftzzdog/TermOrganism/_archive/
mv /home/craftzzdog/TermOrganism/semantic_probe.py /home/craftzzdog/TermOrganism/_archive/
mv /home/craftzzdog/TermOrganism/thinkingMode.py /home/craftzzdog/TermOrganism/_archive/
```

- [ ] **Step 5: Move test scripts to tests/**

```bash
mv /home/craftzzdog/TermOrganism/test_*.py /home/craftzzdog/TermOrganism/tests/
mv /home/craftzzdog/TermOrganism/smoke_test_termorganism.py /home/craftzzdog/TermOrganism/tests/
mv /home/craftzzdog/TermOrganism/apply_test_termorganism.py /home/craftzzdog/TermOrganism/tests/
mv /home/craftzzdog/TermOrganism/integration_test_termorganism.py /home/craftzzdog/TermOrganism/tests/
```

- [ ] **Step 6: Verify**

```bash
ls /home/craftzzdog/TermOrganism/*.py
# Should only show: No .py files at root (all moved)
```

---

### Task 2: Clean up backup files

**Covers:** Backup file cleanup

**Files:**
- Delete: All `.bak*` files tracked in git
- Update: `.gitignore`

- [ ] **Step 1: Remove all .bak files from git tracking**

```bash
cd /home/craftzzdog/TermOrganism
git rm --cached $(git ls-files '*.bak*' 2>/dev/null) 2>/dev/null || true
find . -name "*.bak*" -not -path "./.git/*" -delete
```

- [ ] **Step 2: Remove .backup_shell_fix directory**

```bash
rm -rf /home/craftzzdog/TermOrganism/.backup_shell_fix_20260410_162315
```

- [ ] **Step 3: Update .gitignore to catch all backup patterns**

Edit `/home/craftzzdog/TermOrganism/.gitignore` — add after `*.bak`:
```
*.bak.*
*.BAK.*
*.backup
```

- [ ] **Step 4: Verify no backup files remain**

```bash
find /home/craftzzdog/TermOrganism -name "*.bak*" -not -path "*/.git/*" | wc -l
# Should be 0
```

---

### Task 3: Remove old architecture directories

**Covers:** Remove legacy stub directories

**Files:**
- Delete: `repair/`, `ai/`, `sandbox/`, `runtime/`, `engine/`, `memory/`
- Delete: Empty directories `brain/`, `cli/`, `config/`, `utils/`, `docs/`, `logs/`

- [ ] **Step 1: Archive old architecture directories first (safety)**

```bash
mv /home/craftzzdog/TermOrganism/repair /home/craftzzdog/TermOrganism/_archive/repair_old
mv /home/craftzzdog/TermOrganism/ai /home/craftzzdog/TermOrganism/_archive/ai_old
mv /home/craftzzdog/TermOrganism/sandbox /home/craftzzdog/TermOrganism/_archive/sandbox_old
mv /home/craftzzdog/TermOrganism/runtime /home/craftzzdog/TermOrganism/_archive/runtime_old
mv /home/craftzzdog/TermOrganism/engine /home/craftzzdog/TermOrganism/_archive/engine_old
mv /home/craftzzdog/TermOrganism/memory /home/craftzzdog/TermOrganism/_archive/memory_old
```

- [ ] **Step 2: Remove empty stub directories**

```bash
rmdir /home/craftzzdog/TermOrganism/brain /home/craftzzdog/TermOrganism/cli /home/craftzzdog/TermOrganism/config /home/craftzzdog/TermOrganism/utils /home/craftzzdog/TermOrganism/logs 2>/dev/null || true
```

- [ ] **Step 3: Create docs/ with proper structure**

```bash
mkdir -p /home/craftzzdog/TermOrganism/docs/compose/specs
mkdir -p /home/craftzzdog/TermOrganism/docs/compose/plans
```

- [ ] **Step 4: Verify**

```bash
ls -d /home/craftzzdog/TermOrganism/repair /home/craftzzdog/TermOrganism/ai /home/craftzzdog/TermOrganism/sandbox /home/craftzzdog/TermOrganism/runtime /home/craftzzdog/TermOrganism/engine /home/craftzzdog/TermOrganism/memory 2>&1
# Should show "No such file or directory" for all
```

---

### Task 4: Fix broken bin/ scripts (hardcoded paths)

**Covers:** Fix all 18+ broken CLI entry points

**Files:**
- Modify: All files in `bin/`

- [ ] **Step 1: Fix all bin/ scripts with a single sed command**

```bash
cd /home/craftzzdog/TermOrganism
for f in bin/*; do
  if [ -f "$f" ] && grep -q '/root/TermOrganismGitFork' "$f" 2>/dev/null; then
    sed -i 's|cd /root/TermOrganismGitFork|cd "$(dirname "$0")/.."|g' "$f"
    sed -i 's|/root/TermOrganismGitFork/.studio-venv/bin/python|python3|g' "$f"
    sed -i 's|\.venv/bin/activate|/dev/null|g' "$f"
  fi
done
```

- [ ] **Step 2: Verify no hardcoded paths remain**

```bash
grep -r '/root/TermOrganismGitFork' /home/craftzzdog/TermOrganism/bin/
# Should return nothing
```

- [ ] **Step 3: Make bin/ scripts executable**

```bash
chmod +x /home/craftzzdog/TermOrganism/bin/*
```

---

### Task 5: Fix broken import (RoutingDecision)

**Covers:** Fix critical import error in engine/router.py

**Files:**
- Modify: `core/models/schemas.py`
- Modify: `engine/router.py` (or remove if engine/ is archived)

- [ ] **Step 1: Check if engine/router.py is still needed**

Since `engine/` was an old architecture directory, and `core/engine/` exists, check if core/engine/router.py handles routing:

```bash
cat /home/craftzzdog/TermOrganism/core/engine/router.py 2>/dev/null | head -20
```

- [ ] **Step 2: If core/engine/router.py exists and works, remove engine/router.py**

```bash
rm /home/craftzzdog/TermOrganism/engine/router.py 2>/dev/null || true
```

(If engine/ was already archived in Task 3, this is already done.)

---

### Task 6: Add missing __init__.py files

**Covers:** Fix 12 missing __init__.py in core packages

**Files:**
- Create: 12 `__init__.py` files

- [ ] **Step 1: Create all missing __init__.py files**

```bash
for pkg in lsp sandbox planner context project llm contracts tools editor ranker causal perf; do
  touch /home/craftzzdog/TermOrganism/core/$pkg/__init__.py
done
```

- [ ] **Step 2: Verify all core packages have __init__.py**

```bash
for d in /home/craftzzdog/TermOrganism/core/*/; do
  name=$(basename "$d")
  if [ "$name" != "__pycache__" ] && [ ! -f "$d/__init__.py" ]; then
    echo "MISSING: $name"
  fi
done
# Should output nothing
```

---

### Task 7: Fix duplicate _critical_files() in self_heal.py

**Covers:** Code quality - remove duplicate function definition

**Files:**
- Modify: `core/bootstrap/self_heal.py`

- [ ] **Step 1: Remove the first (simpler) definition, keep the second (import-graph aware) one**

Read lines 52-58 and 342-356. The second definition (line 342) is a superset that tries import-graph discovery first, then falls back to the basic list. Remove lines 52-58 and update the call site at line 78 to work with the remaining definition.

The call at line 78 (`for p in paths or _critical_files():`) should still work since the second definition returns the same type.

- [ ] **Step 2: Verify no syntax errors**

```bash
python3 -c "import ast; ast.parse(open('/home/craftzzdog/TermOrganism/core/bootstrap/self_heal.py').read())"
# Should output nothing (no errors)
```

---

### Task 8: Add pyproject.toml for proper packaging

**Covers:** Project packaging and distribution

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "termorganism"
version = "0.1.0"
description = "AI-powered code repair engine with semantic routing and behavioral verification"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = [
    "rich>=13.0",
    "aiohttp>=3.9",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
termorganism = "core.cli.autofix_cli:main"

[tool.setuptools.packages.find]
include = ["core*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Verify pyproject.toml is valid**

```bash
python3 -c "import tomllib; tomllib.load(open('/home/craftzzdog/TermOrganism/pyproject.toml', 'rb'))"
# Should output nothing (valid TOML)
```

---

### Task 9: Fix install.sh for new structure

**Covers:** Update installation script

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Rewrite install.sh to use pip install**

```bash
cat > /home/craftzzdog/TermOrganism/install.sh << 'INSTALL_EOF'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/termorganism"

echo "Installing TermOrganism..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy project files
cp -r "$REPO_DIR/core" "$INSTALL_DIR/"
cp -r "$REPO_DIR/bin" "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"

# Add to PATH if not already there
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "termorganism" "$SHELL_RC" 2>/dev/null; then
        echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" >> "$SHELL_RC"
        echo "Added to PATH in $SHELL_RC"
    fi
fi

echo "Installed to $INSTALL_DIR"
echo "Run 'source $SHELL_RC' or open a new terminal"
INSTALL_EOF
chmod +x /home/craftzzdog/TermOrganism/install.sh
```

---

### Task 10: Fix duplicate __future__ imports

**Covers:** Code cleanup

**Files:**
- Modify: Multiple files with duplicate imports

- [ ] **Step 1: Find and fix all files with duplicate `from __future__ import annotations`**

```bash
cd /home/craftzzdog/TermOrganism
for f in $(grep -rl "from __future__ import annotations" . --include="*.py" 2>/dev/null); do
  count=$(grep -c "from __future__ import annotations" "$f")
  if [ "$count" -gt 1 ]; then
    # Remove all but the first occurrence
    awk '!seen && /from __future__ import annotations/ { seen=1; print; next } /from __future__ import annotations/ { next } { print }' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    echo "Fixed: $f"
  fi
done
```

---

### Task 11: Fix doctor.sh references

**Covers:** Fix diagnostic tool references

**Files:**
- Modify: `doctor.sh`

- [ ] **Step 1: Update doctor.sh to use correct paths**

```bash
cd /home/craftzzdog/TermOrganism
sed -i 's|omega-autofix|termorganism|g' doctor.sh
sed -i 's|omega-stats|termorganism-stats|g' doctor.sh
```

---

### Task 12: Create proper tests/ structure

**Covers:** Test infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests/__init__.py**

```bash
touch /home/craftzzdog/TermOrganism/tests/__init__.py
```

- [ ] **Step 2: Create basic conftest.py**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

Write this to `tests/conftest.py`.

- [ ] **Step 3: Verify test discovery works**

```bash
cd /home/craftzzdog/TermOrganism
python3 -m pytest tests/ --collect-only 2>&1 | head -20
```

---

### Task 13: Update README.md

**Covers:** Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README to reflect new project structure**

Key changes to make:
- Remove references to old directories (repair/, ai/, sandbox/, etc.)
- Update installation instructions to use new install.sh
- Add quick start section
- Document the core/ package structure

---

### Task 14: Final verification

**Covers:** All tasks

**Files:** N/A

- [ ] **Step 1: Run Python syntax check on all core files**

```bash
cd /home/craftzzdog/TermOrganism
find core/ -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \; 2>&1 | grep -v "^$"
# Should output nothing
```

- [ ] **Step 2: Verify project structure**

```bash
ls /home/craftzzdog/TermOrganism/
# Expected: README.md, pyproject.toml, requirements.txt, install.sh, 
#           core/, bin/, tests/, docs/, _archive/, .gitignore, LICENSE, etc.
# No .py files at root except maybe termorganism entry point
```

- [ ] **Step 3: Verify no broken imports in core**

```bash
cd /home/craftzzdog/TermOrganism
python3 -c "from core.models.schemas import FailureContext, RepairCandidate, RankedCandidate, VerificationResult, SemanticRepairCandidate; print('OK')"
```

- [ ] **Step 4: Verify bin/ scripts are syntactically correct**

```bash
bash -n /home/craftzzdog/TermOrganism/bin/termorganism-watch
bash -n /home/craftzzdog/TermOrganism/bin/termorganism-ask
# Should output nothing
```
