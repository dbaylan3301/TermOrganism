
# TermOrganism

<<<<<<< HEAD
**Semantic self-healing terminal runtime with sandbox-verified repair, cross-file reasoning, and measurable benchmark performance.**
||||||| 6900d9a
**Context-aware, MoE-style self-healing repair runtime for terminal and Python workflows.**
=======
![Benchmark](https://img.shields.io/badge/benchmark-20%2F20%20passed-brightgreen)
![Success Rate](https://img.shields.io/badge/success_rate-100%25-brightgreen)
![False Positives](https://img.shields.io/badge/false_positives-0.0-success)
![Cross-File](https://img.shields.io/badge/cross--file-repair-blue)
![Sandbox Verified](https://img.shields.io/badge/sandbox-verified-purple)
>>>>>>> origin/main

<<<<<<< HEAD
TermOrganism turns a shell from a passive command runner into an adaptive repair-capable runtime.  
It localizes failures, proposes repairs, verifies them in an isolated workspace, and surfaces the highest-confidence fix.
||||||| 6900d9a
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
=======
**Semantic self-healing terminal runtime with sandbox-verified repair, cross-file reasoning, and benchmark-backed proof.**

TermOrganism does not stop at suggesting a fix.  
It localizes the fault, proposes a repair, executes that repair in an isolated workspace, checks behavior, and returns structured output that can be benchmarked.

---

## Demo recordings

### Runtime autofix
[![asciicast](https://asciinema.org/a/isHkYQFzEU3TUvyQ.svg)](https://asciinema.org/a/isHkYQFzEU3TUvyQ)

[▶ Open runtime demo](https://asciinema.org/a/isHkYQFzEU3TUvyQ)

Shows a runtime file-missing failure being repaired and verified.

### Cross-file semantic repair
[![asciicast](https://asciinema.org/a/4UOQ2vi8F8RS3l8P.svg)](https://asciinema.org/a/4UOQ2vi8F8RS3l8P)

[▶ Open cross-file demo](https://asciinema.org/a/4UOQ2vi8F8RS3l8P)

Shows provider/caller-aware repair under `--force-semantic`.

### Benchmark run
[![asciicast](https://asciinema.org/a/MqQzVRHnYmMnQWRo.svg)](https://asciinema.org/a/MqQzVRHnYmMnQWRo)

[▶ Open benchmark demo](https://asciinema.org/a/MqQzVRHnYmMnQWRo)

Shows the benchmark harness running on the bundled fixture suite.

## Why this matters

Most terminal tooling can *suggest*.

TermOrganism is built to **verify**.

That difference matters because a repair is only trustworthy if it can be:

- aimed at the right file
- evaluated in isolation
- checked against expected behavior
- ranked against competing plans
- emitted in machine-readable form

This repo is about **verification-first repair**, not just autocomplete for terminal mistakes.
>>>>>>> origin/main

---

## Proof at a glance

<<<<<<< HEAD
Most terminal repair tools can suggest patches. Far fewer can:
||||||| 6900d9a
Most terminal workflows still look like this:
=======
**Latest benchmark:** 20 / 20 passed
>>>>>>> origin/main

<<<<<<< HEAD
- repair across files
- verify candidate behavior in a sandbox
- preserve a zero-false-positive profile on a structured benchmark
- expose the full repair trail as machine-readable output
||||||| 6900d9a
```text
run -> fail -> manual fix
```
=======
- **Success rate:** 100%
- **False positive rate:** 0.0
- **Median fix time:** 9518.961 ms
- **Mean fix time:** 12920.998 ms
>>>>>>> origin/main

<<<<<<< HEAD
TermOrganism is built around that gap.
||||||| 6900d9a
TermOrganism aims to move them toward:

```text
run -> classify -> repair -> verify -> learn
```

The goal is to turn failures into repair opportunities rather than passive logs.
=======
### Category breakdown

| Category | Passed / Total | Success rate | Median time (ms) | Mean time (ms) |
|---|---:|---:|---:|---:|
| Runtime | 5 / 5 | 100% | 10245.425 | 10408.827 |
| Dependency | 5 / 5 | 100% | 8363.089 | 8352.092 |
| Shell | 5 / 5 | 100% | 7763.174 | 7860.569 |
| Cross-file | 5 / 5 | 100% | 25609.321 | 25062.505 |

### What the benchmark currently covers

- runtime file-missing failures
- dependency/import failures
- shell command-missing failures
- cross-file provider-side semantic repair
- sandbox-verified candidate evaluation
- zero false positives on the current 20-case suite
>>>>>>> origin/main

---

<<<<<<< HEAD
## Benchmark snapshot
||||||| 6900d9a
## Current capabilities
=======
## Demo in under a minute
>>>>>>> origin/main

<<<<<<< HEAD
**Latest verified benchmark run:** 20 / 20 passed

- **Success rate:** 100%
- **False positive rate:** 0.0
- **Median fix time:** 9518.961 ms
- **Mean fix time:** 12920.998 ms

### Category breakdown

| Category | Passed / Total | Success rate | Median time (ms) | Mean time (ms) |
|---|---:|---:|---:|---:|
| Runtime | 5 / 5 | 100% | 10245.425 | 10408.827 |
| Dependency | 5 / 5 | 100% | 8363.089 | 8352.092 |
| Shell | 5 / 5 | 100% | 7763.174 | 7860.569 |
| Cross-file | 5 / 5 | 100% | 25609.321 | 25062.505 |

### What this benchmark demonstrates

- recovery from runtime file-missing failures
- dependency failure classification and repair routing
- shell command failure detection and repair selection
- provider-side repair in cross-file semantic flows
- sandbox-verified repair evaluation
- zero false positives on the current 20-case suite

### Reproduce the benchmark
||||||| 6900d9a
### Python syntax repair

TermOrganism can detect Python syntax failures, generate a structured repair candidate, verify the patched code using AST parsing, and optionally apply the fix to disk with backup.

### Dependency repair suggestions

For missing imports such as `ModuleNotFoundError`, it extracts the missing package and emits a dependency-install candidate.

Example:
=======
### 1) Runtime file-missing repair
>>>>>>> origin/main

```bash
<<<<<<< HEAD
python3 -u benchmarks/runner.py
||||||| 6900d9a
pip install definitely_missing_package_12345
=======
python3 -u termorganism repair demo/broken_runtime.py --json
>>>>>>> origin/main
```

<<<<<<< HEAD
Generated artifacts:

- `benchmarks/results/case_results.json`
- `benchmarks/results/benchmark_summary.json`
- `benchmarks/reports/benchmark_report.md`

---

## Core capabilities

- **Execution-aware repair routing**
- **Runtime, dependency, shell, and cross-file repair coverage**
- **Sandbox-verified candidate evaluation**
- **Planner-first repair selection**
- **Force-semantic mode for deeper multi-file analysis**
- **Structured JSON output for automation and benchmarking**
- **Memory-guided ranking hooks**
- **Contract and behavioral verification hooks**

---

## Example commands

### Doctor

```bash
termorganism doctor
```

### Repair a failing Python file

```bash
termorganism repair demo/broken_runtime.py --json
```

### Force semantic repair on a cross-file case

```bash
termorganism repair demo/cross_file_dep.py --force-semantic --json
```

---

## Why it matters

TermOrganism is not just a command suggester. It is a **verification-first repair runtime**.

That distinction matters because a repair is only valuable if it can be:

1. localized to the right file or provider
2. executed in an isolated workspace
3. checked against expected behavior
4. ranked against competing repair plans
5. surfaced in a reproducible form

This repository is organized around those constraints.

---

## Output model

TermOrganism can emit structured JSON that includes fields such as:

- selected repair kind
- target file
- provider / caller metadata
- source plan
- branch execution result
- contract result
- behavioral verification result
- sandbox result
||||||| 6900d9a
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
=======
Expected shape of result:

```json
{
  "result": {
    "kind": "runtime_file_missing",
    "target_file": "/root/TermOrganismGitFork/demo/broken_runtime.py"
  },
  "sandbox": {
    "ok": true
  },
  "behavioral_verify": {
    "ok": true
  },
  "contract_result": {
    "ok": true
  }
}
```

### 2) Cross-file semantic repair

```bash
python3 -u termorganism repair demo/cross_file_dep.py --force-semantic --json
```

What this demonstrates:

- caller/provider separation
- provider-side repair targeting
- multi-file semantic localization
- verified branch execution before trust
>>>>>>> origin/main

<<<<<<< HEAD
That makes it usable both as a CLI tool and as a benchmarking substrate.
||||||| 6900d9a
This memory layer is the foundation for future:

- retrieval-augmented repair
- confidence reweighting
- repeated failure adaptation
- project-aware remediation ranking
=======
### 3) Full benchmark reproduction

```bash
python3 -u benchmarks/runner.py
```

Artifacts generated by the benchmark runner:

- `benchmarks/results/case_results.json`
- `benchmarks/results/benchmark_summary.json`
- `benchmarks/reports/benchmark_report.md`
>>>>>>> origin/main

---

## Current benchmark-backed positioning

<<<<<<< HEAD
TermOrganism currently demonstrates:
||||||| 6900d9a
### 1. Analyze a broken file
=======
### Repo-local run
>>>>>>> origin/main

<<<<<<< HEAD
- **sandbox-verified repair**
- **cross-file-aware repair selection**
- **planner-based repair ranking**
- **machine-readable verification output**
- **zero false positives on the current benchmark suite**
||||||| 6900d9a
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
=======
```bash
git clone https://github.com/dbaylan3301/TermOrganism.git
cd TermOrganism
python3 -u termorganism doctor
python3 -u termorganism repair demo/broken_runtime.py --json
```

### Benchmark run

```bash
python3 -u benchmarks/runner.py
```

The bundled demo fixtures and benchmark suite are already enough to see the core value of the system.

---

## What makes TermOrganism different

| Capability | TermOrganism |
|---|---|
| Cross-file repair targeting | Yes |
| Sandbox-verified candidate evaluation | Yes |
| Structured JSON repair output | Yes |
| Planner-first repair ranking | Yes |
| Contract / behavioral verification hooks | Yes |
| Benchmark-backed evidence in repo | Yes |

---

## Core capabilities

- **Execution-aware repair routing**
- **Runtime, dependency, shell, and cross-file repair coverage**
- **Sandbox-verified candidate evaluation**
- **Planner-first repair selection**
- **Force-semantic mode for deeper multi-file analysis**
- **Structured JSON output for automation and benchmarking**
- **Memory-guided ranking hooks**
- **Contract and behavioral verification hooks**

---

## Example commands

### Doctor

```bash
python3 -u termorganism doctor
```

### Repair a failing Python file

```bash
python3 -u termorganism repair demo/broken_runtime.py --json
```

### Repair a shell failure

```bash
python3 -u termorganism repair demo/broken_shell_bat.txt --json
```

### Force semantic analysis on a cross-file case

```bash
python3 -u termorganism repair demo/cross_file_dep.py --force-semantic --json
```
>>>>>>> origin/main

---

<<<<<<< HEAD
## Repository focus
||||||| 6900d9a
## Current status
=======
## Machine-readable output
>>>>>>> origin/main

<<<<<<< HEAD
This repo currently emphasizes:
||||||| 6900d9a
TermOrganism is currently in an **operational prototype** phase.
=======
TermOrganism can emit structured JSON with fields such as:
>>>>>>> origin/main

<<<<<<< HEAD
- Python-centered repair flows
- shell/runtime/dependency failure handling
- cross-file semantic provider repair
- benchmarkability and reproducibility
||||||| 6900d9a
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
=======
- selected repair kind
- target file
- provider / caller metadata
- source plan
- branch execution result
- contract result
- behavioral verification result
- sandbox result

That makes it usable both as a CLI tool and as a benchmarking substrate.

---

## Current positioning

TermOrganism currently demonstrates:

- **benchmark-backed repair behavior**
- **sandbox-verified execution**
- **cross-file-aware repair selection**
- **planner-based repair ranking**
- **structured output for tooling and evaluation**
- **zero false positives on the current benchmark suite**

---

## Suggested mental model

Think of TermOrganism as:

> a self-healing terminal runtime that tries to validate repairs before trusting them.

---

## Roadmap direction

Highest-leverage next moves:

- add terminal GIFs / short demos to the README
- expand the benchmark suite beyond 20 cases
- reduce cross-file latency
- harden sandbox isolation and execution speed
- improve logical-error and regression-guard coverage
- polish doctor and force-semantic UX
- add a low-friction install flow

---

## Status

TermOrganism is no longer just an experimental fixer.  
It now has a green multi-category benchmark, reproducible repair outputs, cross-file semantic repair coverage, and a verification-first runtime story.

If you care about terminal-native repair systems, semantic debugging, cross-file fault localization, or verifiable developer tooling, this is the layer to watch.


# TermOrganism

**Semantic repair runtime for terminal and Python failures.**

TermOrganism is a repair-first execution layer that turns failures into structured semantic repair workflows. Instead of stopping at shallow patch suggestions, it analyzes broken behavior, localizes likely fault boundaries across files, synthesizes competing repair strategies, verifies them in isolated workspaces, and selects a winner using behavioral, contractual, and semantic signals.

It is designed for developers who want a terminal-native system that can reason about failures, not just react to them.

## Why TermOrganism

- Most developer tooling can detect that something failed. Very little tooling can answer the harder questions. Where is the real fault boundary?
- Is the visible failure only a caller symptom?
- Which repair is operationally safe but semantically weak?
- Which repair actually improves behavior instead of hiding the exception?
- Can the fix be verified before touching the working tree?

TermOrganism is built around those questions.

## What TermOrganism does

TermOrganism transforms a failure into a structured repair loop:

```text
failure
-> context build
-> semantic localization
-> route selection
-> expert candidate synthesis
-> multi-hypothesis repair planning
-> sandbox execution
-> behavioral verification
-> regression guard synthesis
-> contract propagation
-> semantic ranking
-> best-plan selection
-> apply / exec / remember
```

This makes it possible to move from something broke to this is the most semantically credible repair plan, verified in an isolated workspace, with explicit reasoning and bounded blast radius.

## Core capabilities

### Cross-file semantic fault localization

TermOrganism does not assume the crashing file is the real source of failure. It can separate caller, provider, runtime boundary, and underlying invariant violation. This is critical for failures where the visible exception is raised in one file but the correct repair belongs in another.

### Provider and caller separation

For multi-file failures, TermOrganism can distinguish the file that triggers a failure from the file that should actually be repaired. Instead of patching the caller blindly, it can identify the provider-side unsafe boundary and target the semantic fix there.

```text
cross_file_dep.py -> helper_mod.py -> FileNotFoundError
```

### Multi-hypothesis repair synthesis

TermOrganism can generate multiple competing repair candidates for the same failure. These may include operational path creation, guarded existence checks, explicit exception recovery, syntax remediation, dependency remediation, or shell and runtime guidance. It does not treat the first plausible fix as the best fix.

### Behavioral verification

Candidates can be executed against reproduced failure scenarios to measure whether the original failure signature disappears and whether the repaired behavior remains acceptable. This helps separate patches that merely silence symptoms from patches that actually change program behavior in the intended direction.

### Project-wide isolated sandboxing

Instead of mutating the original working tree immediately, TermOrganism can create isolated temporary workspaces and evaluate repairs there first. That enables safe replay, static validation, runtime verification, and branch-level plan testing.

### Synthesized regression guards

TermOrganism can derive regression checks from observed failures and repaired behavior, then use them to score candidate quality. This allows the system to ask whether the prior failure signature disappeared, whether the previous exception family is absent, and whether the replay now completes successfully.

### Contract-backed repair planning

Repairs are not only scored by whether they run. They are also scored by whether they satisfy explicit expected behavior, such as exception absence, clean exit code, replay success, and multifile propagation consistency.

### Memory-guided ranking

Historical success patterns can influence ranking so that repairs that consistently work in similar contexts receive stronger prior support, while weaker strategies do not dominate only because they are simpler.

### Force-semantic analysis for healthy targets

TermOrganism can run semantic analysis even when the target is currently healthy. This makes it possible to detect latent unsafe IO boundaries, provider-side risk in imported modules, cross-file fragility, and future runtime hazards.

### Winner selection by semantic quality

Operational fixes are not automatically preferred over better code repairs. TermOrganism can prefer a verified provider-side semantic repair over a weaker operational workaround when the semantic repair targets the right file, removes the failure cleanly, preserves behavior, passes sandbox and contract checks, and has acceptable blast radius.

## Current architecture

At a high level, the system contains several layers.

### Semantic and Repro Layer

- failure reproduction harnesses
- traceback-aware localization
- latent semantic analysis
- and provider-caller inference

### Expert Layer

- file runtime expertise
- shell runtime expertise
- dependency expertise
- syntax expertise
- and fallback expert pathways

### Planning Layer

- candidate normalization
- multi-hypothesis plan construction
- multi-file plan expansion
- plan family ranking
- and canonical winner selection

### Verification Layer
>>>>>>> origin/main

- static validation
- isolated runtime replay
- behavioral verification
- synthesized regression guards
- and contract propagation

<<<<<<< HEAD
## Suggested mental model
||||||| 6900d9a
## Roadmap
=======
### Memory and Ranking Layer
>>>>>>> origin/main

<<<<<<< HEAD
Think of TermOrganism as:
||||||| 6900d9a
### Near-term
=======
- historical priors
- winner-only success propagation
- semantic strategy weighting
- and blast radius and risk balancing
>>>>>>> origin/main

<<<<<<< HEAD
> a self-healing terminal runtime that does not stop at proposing fixes, but attempts to validate them before trusting them.

---

## Roadmap direction

Near-term leverage points:
||||||| 6900d9a
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
=======
## Flagship behavior

A representative TermOrganism workflow now supports this pattern:
>>>>>>> origin/main

<<<<<<< HEAD
- expand benchmark coverage from 20 cases to larger public suites
- reduce cross-file latency
- harden sandbox isolation and execution speed
- improve logical-error and regression-guard coverage
- polish doctor and force-semantic UX
- produce reproducible demo flows and public benchmark comparisons
||||||| 6900d9a
```text
error -> route -> expert -> structured candidate -> verify -> apply/exec -> memory
```

That loop is already working end-to-end across multiple repair classes.
=======
```text
healthy target
-> force semantic analysis
-> provider discovery
-> latent IO invariant extraction
-> cross-file repair synthesis
-> multifile contract propagation
-> semantic winner selection
```

This is a major step beyond simple autofix systems that only react after a failure has already crashed visibly.
>>>>>>> origin/main

## Example use cases

<<<<<<< HEAD
## Status
||||||| 6900d9a
## Demo
=======
TermOrganism can repair a broken Python file, analyze a shell or runtime failure, run semantic analysis even if the target currently passes, and evaluate execution suggestions without actually running them.
>>>>>>> origin/main

<<<<<<< HEAD
TermOrganism is no longer just an experimental terminal fixer.  
It now has a green multi-category benchmark with measurable repair behavior and reproducible outputs.
||||||| 6900d9a
Create a broken Python file:
=======
## Example output themes
>>>>>>> origin/main

<<<<<<< HEAD
If you are interested in terminal-native repair systems, semantic debugging, cross-file fault localization, or verification-first developer tooling, this is the layer to watch.
||||||| 6900d9a
```python
def mul(a, b)
    return a * b
```
=======
Depending on the failure class, TermOrganism can return structured information such as selected expert, semantic localization summary, competing candidates, chosen plan, sandbox result, behavioral verification result, regression guard result, contract propagation result, semantic rank tuple, and target provider and caller files.
>>>>>>> origin/main

<<<<<<< HEAD
||||||| 6900d9a
Then run:
=======
This is useful both for direct automated flows and for human-in-the-loop debugging.

## Design philosophy

TermOrganism is built on a few core principles.

Repair is not the same as patching. A patch may remove an exception without improving the underlying behavior. TermOrganism treats repair as a semantic process, not merely a text rewrite.

The crashing file is often not the real repair site. Many failures are caller-visible but provider-caused. Cross-file reasoning is essential.

Verification must precede confidence. A candidate is not strong because it looks plausible. It becomes strong when replay, sandbox, and contract checks support it.

Operational fixes and semantic fixes are different classes. Creating a missing file path can be useful. But if the real issue is an unsafe boundary, a semantic code repair may be the stronger winner.

Healthy code can still hide latent failure risk. A target that currently passes may still deserve semantic analysis. This is why force-semantic mode exists.

## Current strengths

TermOrganism is now strongest in terminal-native failure handling, Python runtime repair flows, shell and runtime issue interpretation, multi-hypothesis candidate generation, cross-file provider targeting, sandbox-backed semantic repair ranking, and latent failure analysis for healthy targets.

## Current limitations

TermOrganism is advancing quickly, but it is still an evolving system. Its strongest support is centered on Python and terminal-oriented workflows. Some experts are richer than others. Broader language coverage is still less mature. Deep semantic correctness is always harder than syntax and runtime recovery. Contract synthesis quality depends on what can be inferred from observed behavior.

In other words, TermOrganism already goes far beyond naive autofix, but it is still being pushed toward a more general semantic repair runtime.

## Roadmap direction

The direction is clear:

- Deeper cross-file semantic planning
- Stronger latent invariant detection
- Richer contract synthesis
- Broader expert specialization
- Memory-backed repair priors
- Safer automatic application pipelines
- Stronger semantic ranking under uncertainty

The long-term goal is not just autofix. It is a failure-intelligence runtime.

## Repository structure

The repository is centered around core orchestration, expert proposals, sandbox verification, planning, ranking, semantic analysis, and demo targets.

## Installation

Clone the repository:
>>>>>>> origin/main

<<<<<<< HEAD
## Demo recordings
||||||| 6900d9a
```bash
./termorganism demo/broken_syntax.py --auto-apply
```
=======
```bash
git clone https://github.com/dbaylan3301/TermOrganism.git
cd TermOrganism
```
>>>>>>> origin/main

<<<<<<< HEAD
### Runtime autofix
||||||| 6900d9a
Expected result:
=======
## Running
>>>>>>> origin/main

<<<<<<< HEAD
[![asciicast](https://asciinema.org/a/REPLACE_RUNTIME_CAST_ID.svg)](https://asciinema.org/a/REPLACE_RUNTIME_CAST_ID)
||||||| 6900d9a
- `python_syntax` selected
- patch generated
- AST verification passes
- backup created
- file rewritten
- repair event stored in memory
=======
General pattern:
>>>>>>> origin/main

<<<<<<< HEAD
Shows a runtime file-missing failure being repaired and verified.

### Cross-file semantic repair

[![asciicast](https://asciinema.org/a/REPLACE_CROSSFILE_CAST_ID.svg)](https://asciinema.org/a/REPLACE_CROSSFILE_CAST_ID)

Shows provider/caller-aware repair under `--force-semantic`.

### Benchmark run
||||||| 6900d9a
---

## Philosophy

TermOrganism treats failure as a first-class runtime signal.

Instead of:

```text
run -> fail -> inspect manually
```
=======
```bash
./termorganism <target> [options]
```
>>>>>>> origin/main

<<<<<<< HEAD
[![asciicast](https://asciinema.org/a/REPLACE_BENCHMARK_CAST_ID.svg)](https://asciinema.org/a/REPLACE_BENCHMARK_CAST_ID)

Shows the benchmark harness running on the bundled fixture suite.
||||||| 6900d9a
it moves toward:
=======
## Who this is for
>>>>>>> origin/main

<<<<<<< HEAD
||||||| 6900d9a
```text
run -> classify -> repair -> verify -> remember
```
=======
TermOrganism is for developers who want more than linter-style feedback, more than one-shot patch suggestions, a terminal-native repair workflow, verifiable semantic repair plans, and cross-file reasoning about broken behavior.

It is especially relevant if you care about program behavior, fault boundaries, and repair credibility rather than just error suppression.

## Positioning

TermOrganism is not trying to be just another code assistant. It is moving toward a different layer. Not only code generation. Not only static linting. Not only deployment tooling. But runtime-aware semantic repair.

That is the layer this project is building into.

## Contributing

Contributions are welcome in areas such as new repair experts, stronger verification strategies, better semantic localization, broader language and runtime support, stronger ranking and memory models, and clearer demos and benchmarks.

If you contribute, prefer changes that improve repair quality, verification credibility, or semantic targeting rather than only expanding output volume.

## Status

TermOrganism is already capable of verified cross-file semantic repair planning and forced semantic analysis for healthy targets, and is actively evolving toward a more general repair runtime.

## License

MIT
>>>>>>> origin/main
