# TermOrganism

**Context-aware, MoE-style self-healing repair runtime for terminal and Python workflows.**

TermOrganism is a repair orchestrator that transforms failures into structured repair loops:

```text
error -> context -> route -> expert -> candidate -> verify -> apply/exec -> memory
```

Instead of using one generic fixer, it routes each failure to the most relevant repair expert and produces typed, verifiable remediation candidates.

---

## Overview

TermOrganism is designed as a **Mixture-of-Experts (MoE) repair runtime** for terminal and Python workflows.

It can currently:

- detect and route Python syntax failures
- generate structured repair candidates
- verify Python repair payloads
- auto-apply eligible file-based fixes with backup + re-verification
- suggest dependency installation candidates
- repair runtime file/path failures
- diagnose shell failures such as `command not found` and `permission denied`
- safely dry-run or execute whitelisted shell remediations
- persist repair events into JSONL memory

---

## Why this project exists

Most terminal workflows still look like this:

```text
run -> fail -> manual fix
```

TermOrganism aims to move them toward:

```text
run -> classify -> repair -> verify -> learn
```

The goal is to turn failures into repair opportunities rather than passive logs.

---

## Current capabilities

### Python syntax repair

TermOrganism can detect Python syntax failures, generate a structured repair candidate, verify the patched code using AST parsing, and optionally apply the fix to disk with backup.

### Dependency repair suggestions

For missing imports such as `ModuleNotFoundError`, it extracts the missing package and emits a dependency-install candidate.

Example:

```bash
pip install definitely_missing_package_12345
```

### Runtime file/path repair

For file-related runtime failures, it can emit operational remediations such as:

```bash
mkdir -p logs && touch logs/app.log
```

When the failing target is a Python file, it can also generate a guarded rewrite using `Path(...).exists()`.

### Shell/runtime diagnostics

It can classify shell failures such as:

- `command not found`
- `permission denied`
- missing shell path/file failures

and produce structured shell candidates with suggestions.

### Safe execution

Shell remediations are separated from patch apply logic and routed through a **whitelisted execution layer**.

### Repair memory

Repair traces are written to:

```text
memory/TermOrganism/repair_events.jsonl
```

This creates an audit trail and prepares the system for future retrieval-augmented repair logic.

---

## Architecture

```text
TermOrganism/
├── core/
│   ├── __init__.py
│   ├── autofix.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── autofix_cli.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── context_builder.py
│   │   ├── orchestrator.py
│   │   ├── ranker.py
│   │   └── router.py
│   ├── experts/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dependency.py
│   │   ├── file_runtime.py
│   │   ├── llm_fallback.py
│   │   ├── memory_retrieval.py
│   │   ├── python_syntax.py
│   │   └── shell_runtime.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── event_store.py
│   │   ├── retrieval.py
│   │   └── stats.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── util/
│   │   ├── __init__.py
│   │   ├── diffing.py
│   │   ├── fingerprints.py
│   │   ├── logging.py
│   │   ├── patch_apply.py
│   │   └── safe_exec.py
│   └── verify/
│       ├── __init__.py
│       ├── python_verify.py
│       └── sandbox.py
└── memory/
    └── TermOrganism/
        └── repair_events.jsonl
```

---

## How it works

### 1. Context building

Raw failures are normalized into a structured `RepairContext`.

Typical fields include:

- `error_text`
- `file_path`
- `source_code`
- `filename`
- `error_type`

### 2. Routing

The policy router maps an error signature to one or more experts.

Typical mappings:

- `SyntaxError`, `IndentationError` -> `python_syntax`
- `ModuleNotFoundError` -> `dependency`
- `FileNotFoundError` -> `file_runtime`
- `command not found`, `permission denied` -> `shell_runtime`

### 3. Candidate generation

Experts emit structured candidates.

Example candidate:

```json
{
  "expert": "python_syntax",
  "kind": "syntax",
  "confidence": 0.85,
  "summary": "missing block colons restored",
  "patch": "... unified diff ...",
  "candidate_code": "... patched source ..."
}
```

### 4. Verification

Candidates are verified according to type.

- Python patch -> AST validation
- dependency install -> accepted as non-Python operational candidate
- runtime file fix -> operational validation or Python validation depending on target type
- shell candidate -> safe execution layer only

### 5. Apply / exec

Depending on candidate type:

- file-based Python fixes can be auto-applied with backup
- shell suggestions can be executed only through a whitelist-based safe executor
- dangerous commands are intentionally blocked

### 6. Memory logging

Every repair attempt is appended to JSONL memory for auditability and future retrieval.

---

## Expert routing table

| Failure class | Routed expert |
|---|---|
| `SyntaxError`, `IndentationError` | `python_syntax` |
| `ModuleNotFoundError`, missing import | `dependency` |
| `FileNotFoundError`, missing runtime file | `file_runtime` |
| `command not found`, `permission denied` | `shell_runtime` |
| uncategorized / weak match | `memory_retrieval`, `llm_fallback` |

---

## CLI usage

### Analyze a broken Python file

```bash
./termorganism demo/broken_syntax.py
```

### Analyze and auto-apply a safe Python fix

```bash
./termorganism demo/broken_syntax.py --auto-apply
```

### Analyze a dependency failure as JSON

```bash
./termorganism demo/broken_import.py --json
```

### Analyze a shell error log

```bash
./termorganism demo/broken_shell_bat.txt --json
```

### Dry-run safe shell remediations

```bash
./termorganism demo/broken_shell_path.txt --exec --dry-run --json
```

---

## Example outputs

### Example 1 — Python syntax repair

Input:

```python
def add(a, b)
    return a + b
```

Output candidate:

```json
{
  "expert": "python_syntax",
  "kind": "syntax",
  "confidence": 0.85,
  "summary": "missing block colons restored",
  "candidate_code": "def add(a, b):\n    return a + b\n"
}
```

Expected behavior:

- route -> `python_syntax`
- generate patched source
- verify using AST
- optionally auto-apply with backup
- persist event to memory

---

### Example 2 — Dependency repair

Input error:

```text
ModuleNotFoundError: No module named 'definitely_missing_package_12345'
```

Output candidate:

```json
{
  "expert": "dependency",
  "kind": "dependency_install",
  "patch": "pip install definitely_missing_package_12345"
}
```

---

### Example 3 — Runtime file repair

Input error:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
```

Output candidate:

```json
{
  "expert": "file_runtime",
  "kind": "runtime_file_missing",
  "patch": "mkdir -p logs && touch logs/app.log"
}
```

---

### Example 4 — Shell command repair

Input error:

```text
zsh: command not found: bat
```

Output candidate includes:

- missing command extraction
- package hint
- safe suggestions
- structured metadata

Example:

```json
{
  "expert": "shell_runtime",
  "kind": "shell_command_missing",
  "metadata": {
    "missing_command": "bat",
    "package_hint": "bat",
    "suggestions": [
      "command -v bat",
      "which bat",
      "echo $PATH",
      "sudo apt install bat",
      "pkg install bat",
      "brew install bat"
    ]
  }
}
```

---

## Safety model

> **Important**
>
> TermOrganism explicitly separates **apply** from **exec**.

### Auto-apply

Used only for eligible file-based repair candidates.

Current supported classes:

- `syntax`
- `python_patch`
- `runtime_file_missing` when a valid Python rewrite exists

### Safe exec

Used only with explicit `--exec`, and only for whitelisted commands.

Currently allowed:

- `command -v ...`
- `which ...`
- `echo $PATH`
- `mkdir -p ...`
- `touch ...`
- `chmod +x ...`

Blocked by design:

- `sudo ...`
- `rm ...`
- `mv ...`
- `curl ...`
- `wget ...`
- unrestricted shell execution

---

## Event memory

Repair traces are stored in:

```text
memory/TermOrganism/repair_events.jsonl
```

A typical event may include:

- original error text
- selected routes
- generated candidates
- best candidate
- verify result
- sandbox result
- apply result
- exec result

This memory layer is the foundation for future:

- retrieval-augmented repair
- confidence reweighting
- repeated failure adaptation
- project-aware remediation ranking

---

## Quick start

### 1. Analyze a broken file

```bash
./termorganism demo/broken_syntax.py
```

### 2. Auto-apply a verified syntax repair

```bash
./termorganism demo/broken_syntax.py --auto-apply
```

### 3. Dry-run shell remediation

```bash
./termorganism demo/broken_shell_path.txt --exec --dry-run --json
```

---

## Current status

TermOrganism is currently in an **operational prototype** phase.

It already supports:

- MoE-style routing
- structured expert outputs
- candidate normalization
- typed verification
- auto-apply with backup + re-verification
- safe shell execution with dry-run
- persistent repair event logging
- CLI-driven workflows

It is not yet a full production runtime, but it is already a working self-healing repair prototype.

---

## Roadmap

### Near-term

- real sandbox verification
- stronger shell/runtime remediation
- environment-aware dependency validation
- better retrieval-based ranking
- richer diff safety scoring

### Mid-term

- native production orchestrator components
- project-aware patch ranking
- patch policies by error class
- confidence calibration

### Longer-term

- continuous terminal observation
- retrieval from prior successful local repairs
- command learning
- policy-controlled LLM fallback

---

## Development note

At this stage, the strongest validated repair loop is:

```text
error -> route -> expert -> structured candidate -> verify -> apply/exec -> memory
```

That loop is already working end-to-end across multiple repair classes.

---

## Demo

Create a broken Python file:

```python
def mul(a, b)
    return a * b
```

Then run:

```bash
./termorganism demo/broken_syntax.py --auto-apply
```

Expected result:

- `python_syntax` selected
- patch generated
- AST verification passes
- backup created
- file rewritten
- repair event stored in memory

---

## Philosophy

TermOrganism treats failure as a first-class runtime signal.

Instead of:

```text
run -> fail -> inspect manually
```

it moves toward:

```text
run -> classify -> repair -> verify -> remember
```
