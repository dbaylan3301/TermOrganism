```## TermOrganism
Context-aware, MoE-style self-healing repair runtime for terminal and Python workflows.
TermOrganism turns a passive developer runtime into an error-aware repair system that can:
classify failures,
route them to specialized experts,
generate structured repair candidates,
verify patches,
optionally apply safe fixes,
execute whitelisted shell remediations,
and persist repair history for future retrieval.
It is designed as a Mixture-of-Experts (MoE) repair orchestrator for local debugging, terminal automation, and self-healing development workflows.
# Core idea
Instead of treating every failure with one generic fixer, TermOrganism uses a repair orchestration pipeline:

error
  -> context builder
  -> policy router
  -> expert selection
  -> candidate generation
  -> verification
  -> optional apply / safe exec
  -> memory event logging

This allows different classes of failures to be handled by different specialists.

# Examples:
SyntaxError → python_syntax
ModuleNotFoundError → dependency
FileNotFoundError → file_runtime
command not found → shell_runtime

# Current capabilities
Python syntax repair
TermOrganism can detect Python syntax failures, generate a structured repair candidate, verify the patched code with AST parsing, and optionally apply the change with automatic backup.
Dependency repair suggestions
For missing module errors, it extracts the missing package and emits a dependency-install candidate such as:

`pip install missing_package_name`

# Runtime file/path repair
For file-related runtime failures, it can propose operational fixes such as:

`mkdir -p logs && touch logs/app.log`

and, for Python files, generate a guarded source rewrite using Path(...).exists().
Shell/runtime diagnostics
It can classify shell failures such as:
command not found
permission denied
missing shell paths
and emit safe suggestions with command metadata.

# Safe execution
Shell suggestions can be run only through a whitelisted execution layer with:
explicit --exec
optional --dry-run
restricted allowed commands

# Auto-apply
Eligible Python repair candidates can be:
backed up,
written to disk,
re-verified,
logged to memory.

# Repair memory
Repair events are stored in:

`memory/TermOrganism/repair_events.jsonl`

This creates an audit trail and prepares the system for future retrieval-based repair ranking.

# Architecture

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

## Repair pipeline
 Context building
context_builder.py converts raw failure input into a structured repair context.
Typical fields include:

error_text
file_path
source_code
filename
error_type

 Routing
router.py maps an error signature to one or more experts.

Examples:
syntax failures → python_syntax
missing imports → dependency
missing files → file_runtime
shell failures → shell_runtime

 Candidate generation
Experts emit structured candidates with fields such as:

`{
  "expert": "python_syntax",
  "kind": "syntax",
  "confidence": 0.85,
  "summary": "missing block colons restored",
  "patch": "... unified diff ...",
  "candidate_code": "... patched source ..."
}`

Verification
Candidates are verified according to their type:
Python patch → AST validation
dependency install → accepted as non-Python operational candidate
shell/runtime operational fix → optional operational validation
runtime Python rewrite → AST validation when applicable

 Apply / execute
Depending on candidate type:
Python patches can be auto-applied with backup
shell suggestions can be run via safe whitelist execution
dangerous operations are blocked

 Memory logging
Every repair attempt is written to JSONL memory for later inspection and future retrieval-based ranking.

CLI usage
Analyze a broken Python file

`./termorganism demo/broken_syntax.py`

# Analyze and auto-apply a Python syntax fix

`./termorganism demo/broken_syntax.py --auto-apply`

Analyze a dependency failure as JSON

`./termorganism demo/broken_import.py --json`

Analyze a shell error log

`./termorganism demo/broken_shell_bat.txt --json`

Dry-run safe shell execution

`./termorganism demo/broken_shell_path.txt --exec --dry-run --json`

# Example outputs
Syntax repair
Input:

`def add(a, b)
    return a + b`

Output candidate:

`{
  "expert": "python_syntax",
  "kind": "syntax",
  "confidence": 0.85,
  "summary": "missing block colons restored",
  "candidate_code": "def add(a, b):\n    return a + b\n"
}`

Dependency repair
Input error:

`ModuleNotFoundError: No module named 'definitely_missing_package_12345'`

Output candidate:

`{
  "expert": "dependency",
  "kind": "dependency_install",
  "patch": "pip install definitely_missing_package_12345"
}`

Runtime file repair
Input error:

`FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'`

Output candidate:

`{
  "expert": "file_runtime",
  "kind": "runtime_file_missing",
  "patch": "mkdir -p logs && touch logs/app.log"
}`

Shell command repair
Input error:

zsh: command not found: bat

Output candidate:

`{
  "expert": "shell_runtime",
  "kind": "shell_command_missing",
  "metadata": {
    "missing_command": "bat",
    "suggestions": [
      "command -v bat",
      "which bat",
      "echo $PATH",
      "sudo apt install bat",
      "pkg install bat",
      "brew install bat"
    ]
  }
}`

Safety model
TermOrganism separates apply from exec.
Auto-apply
Used only for eligible file-based patch candidates.

Current allowed kinds:
syntax
python_patch
runtime_file_missing (only when there is a valid Python source rewrite)

Safe exec
Used only for restricted shell actions and only when explicitly requested.

Whitelisted commands currently include:
command -v ...
which ...
echo $PATH
mkdir -p ...
touch ...
chmod +x ...
Blocked by design:
sudo ...
rm ...
mv ...
curl ...
wget ...
unrestricted command execution
Event memory
Repair traces are stored as JSONL records in:

`memory/TermOrganism/repair_events.jsonl`

A typical event includes:
original error text
selected routes
generated candidates
best candidate
verify result
sandbox result
apply result
exec result

This memory layer is the basis for future:
retrieval-augmented repair,
confidence reweighting,
repeated failure adaptation.

Current status
TermOrganism is currently in an operational prototype phase.
It already supports:
routing,
structured expert outputs,
candidate normalization,
verification,
safe patch apply,
safe shell exec dry-run,
repair event logging,
CLI-driven usage.
It is not yet a full production runtime, but it is already a working demo/proto self-healing repair engine.

Roadmap
Near-term
real sandbox verification
stronger shell_runtime remediation
environment-aware dependency validation
better retrieval-based ranking
native orchestrator components without adapter shims

Mid-term
project-aware patch ranking
patch confidence calibration
richer diff safety scoring
patch application policies by error class

Longer-term
continuous terminal observation
command learning memory
retrieval from prior successful local repairs
LLM fallback with repair policy controls

Demo flow
A typical successful repair loop looks like this:

1. broken file or shell log is provided
2. error is parsed into RepairContext
3. router selects an expert
4. expert emits structured candidate(s)
5. best candidate is verified
6. if requested:
   - file patch is applied with backup
   - or whitelisted shell actions are executed
7. outcome is written to repair_events.jsonl

Quick demo
Create a broken Python file:

`def mul(a, b)
    return a * b`

Run:
`./termorganism demo/broken_syntax.py --auto-apply`

Expected behavior:
selects python_syntax
generates patched code
verifies with AST
writes backup
applies fix
logs event to memory

Why this project exists
Modern terminal workflows still treat failures as passive output.

TermOrganism treats failures as repair opportunities.
It is an attempt to move from:

`run -> fail -> manual fix`

toward:
`run -> classify -> repair -> verify -> learn`

