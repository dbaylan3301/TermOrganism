# TermOrganism

**Conversational, context-aware, self-healing developer runtime with predictive whispers, route arbitration, editor integration, and safe auto-fixes.**

TermOrganism turns a shell from a passive command runner into a repair-capable runtime that can:

- detect failure patterns
- predict pre-failure risks before execution
- choose a repair route with explainable arbitration
- verify outcomes
- learn from past repairs
- expose structured runtime reasoning
- integrate with editors through LSP, sidebar whispers, and pre-save checks
- apply safe code actions for selected Python risks

---

## What it is

TermOrganism is a terminal-native runtime layer for repair, verification, and context-aware decision-making.

Instead of treating the terminal as a place that only executes commands, it treats failures and code smells as signals that can be:

1. observed
2. classified
3. routed
4. repaired
5. verified
6. remembered
7. explained

This makes the shell behave more like an adaptive runtime than a passive command prompt.

---

## Core capabilities

### 1. Repair runtime
TermOrganism inspects failures and routes them through layered repair paths.

### 2. Predictive diagnostics
Before execution, TermOrganism can detect likely issues such as:

- missing imports
- missing file paths
- bare except blocks
- mutable default arguments
- eval / exec risk
- wildcard import risk
- subprocess shell risk
- secret-inline risk
- missing `__main__` guard
- relative import fragility
- environment default handling risk

### 3. Context-aware routing
Route choice is not based on signature alone.

TermOrganism combines:

- planner suggestion
- intent-aware context
- predictive-to-repair bridge memory
- live whisper signals
- route arbitration

### 4. Explainable route selection
TermOrganism can explain why a route was chosen, including:

- planner suggested mode
- final effective mode
- bridge signal
- whisper signal
- arbitration winner

### 5. Editor-facing experience
TermOrganism includes:

- live file analysis
- sidebar whisper feed
- pre-save checks
- LSP diagnostics
- code actions / preview fixes

### 6. Safe auto-fixes
Selected Python issues can be auto-fixed safely, including:

- `bare-except-risk`
- `mutable-default-risk`
- `main-guard-risk`
- `path-risk`

### 7. Benchmarking and smoke tests
TermOrganism can benchmark proactive routing behavior across multiple synthetic cases and provide machine-readable JSON / CSV outputs.

---

## Architecture overview

TermOrganism currently consists of these major layers:

### Repair and routing
- planner
- verifier
- test runner
- fallback repair paths
- fast / fast_v2 / hot_force route selection

### Predictive layer
- `termorganism-watch`
- `termorganism-live`
- predictive runtime diagnostics
- pre-failure whispers
- sidebar feed
- pre-save gate

### Memory and bridge layer
- synaptic memory
- predictive-to-repair bridge
- route bias from historical outcomes

### Context layer
- intent-aware context
- preload routes
- safe preview bias
- verify-first bias

### Arbitration layer
- route candidates
- risk-adjusted scoring
- arbitration winner selection

### Editor layer
- LSP server
- VS Code integration
- Neovim integration
- fix preview / apply commands

---

## Why this is different

TermOrganism is not only a repair tool.

It is becoming a **context-aware runtime** that can:

- read code as it changes
- forecast likely breakage
- explain why it chose a route
- expose route reasoning as structured runtime state
- bridge terminal repair and editor diagnostics

---

## Main commands

### Conversational / repo interaction
```bash
./bin/termorganism-chat "Bu repo ne yapıyor?"
./bin/termorganism-chat "Testleri başlat"
./bin/termorganism-chat "Git ne alemde"
```

### Repair
```bash
./termorganism repair /tmp/target.py --json
./termorganism repair /tmp/target.py --pretty
```

### Predictive watch
```bash
./bin/termorganism-watch /tmp/file.py
./bin/termorganism-watch --modified --loop
```

### Live predictive analysis
```bash
./bin/termorganism-live /tmp/file.py
```

### Sidebar whisper feed
```bash
./bin/termorganism-sidebar /tmp/file.py --once
```

### Pre-save analysis
```bash
./bin/termorganism-pre-save /tmp/file.py --json
./bin/termorganism-pre-save /tmp/file.py --stdin --json --block-on-error
```

### Route explainability
```bash
./bin/termorganism-explain-route /tmp/file.py
./bin/termorganism-explain-route /tmp/file.py --json
```

### Benchmarking
```bash
./bin/termorganism-benchmark-proactive
./bin/termorganism-benchmark-proactive --json
./bin/termorganism-benchmark-proactive --csv /tmp/termorganism_benchmark.csv
```

### Smoke test
```bash
./bin/termorganism-smoke-full
```

### Fix preview / apply
```bash
./bin/termorganism-fix-preview /tmp/file.py
./bin/termorganism-fix-preview /tmp/file.py --json
./bin/termorganism-apply-fix /tmp/file.py --action-id <ACTION_ID>
```

### LSP
```bash
./bin/termorganism-lsp
```

---

## 30-second demo

```bash
cat > /tmp/live_demo.py <<'PY'
import definitely_missing_package_3301

def risky(a=[]):
    try:
        return eval("1+1")
    except:
        return None

with open("missing_file_3301.txt") as f:
    print(f.read())
PY

./bin/termorganism-live /tmp/live_demo.py
./bin/termorganism-pre-save /tmp/live_demo.py --json
./bin/termorganism-fix-preview /tmp/live_demo.py
./bin/termorganism-explain-route /tmp/live_demo.py
```

---

## Demo workflow

### 1. Predictive live analysis

Create a demo file:

```bash
cat > /tmp/live_demo.py <<'PY'
import definitely_missing_package_3301

def risky(a=[]):
    try:
        return eval("1+1")
    except:
        return None

with open("missing_file_3301.txt") as f:
    print(f.read())
PY
```

Run live analysis:

```bash
./bin/termorganism-live /tmp/live_demo.py
```

Expected output includes signals such as:

- `eval-risk`
- `import-risk`
- `bare-except-risk`
- `path-risk`
- `mutable-default-risk`

---

### 2. Pre-save gate

```bash
./bin/termorganism-pre-save /tmp/live_demo.py --json
```

This returns structured JSON containing:

- top whisper
- diagnostics
- `allow_save`
- `has_error`
- `has_warning`

---

### 3. Explain route selection

```bash
./bin/termorganism-explain-route /tmp/whisper_demo.py
```

Typical explanation includes:

- planner suggested route
- final effective route
- bridge bias
- live whisper
- intent-aware context
- arbitration winner

This is one of the main debugging and demo commands.

---

### 4. Benchmark proactive routing

```bash
./bin/termorganism-benchmark-proactive
```

This runs multiple synthetic cases and shows:

- total cases
- successful cases
- planner changed count
- whisper cases
- bridge-scored cases

For machine-readable output:

```bash
./bin/termorganism-benchmark-proactive --json
./bin/termorganism-benchmark-proactive --csv /tmp/termorganism_benchmark.csv
```

---

### 5. Fix preview and safe apply

Create a small example:

```bash
cat > /tmp/action_demo.py <<'PY'
def x(a=[]):
    try:
        return 1
    except:
        return 0
PY
```

Preview fixes:

```bash
./bin/termorganism-fix-preview /tmp/action_demo.py
```

Apply the first auto-fix:

```bash
ACTION_ID=$(./bin/termorganism-fix-preview /tmp/action_demo.py --json | python3 -c 'import json,sys; j=json.load(sys.stdin); print(next(a["action_id"] for a in j["actions"] if a["auto_apply"]))')
./bin/termorganism-apply-fix /tmp/action_demo.py --action-id "$ACTION_ID"
```

This safely upgrades:

```python
except:
```

to:

```python
except Exception:
```

---

## Safe auto-fixes currently implemented

### Auto-apply
- bare except -> `except Exception`
- mutable default -> `None` + body initialization
- append `__main__` guard
- path existence guard for simple literal `open(...)`

### Preview-only
- guarded import strategy
- eval replacement strategy
- exec replacement strategy
- shell=False subprocess strategy
- explicit import list suggestion
- package-safe import strategy
- env default / fail-fast strategy
- secret externalization strategy

---

## Route selection model

Route choice is layered.

### Inputs
- signature-guided planner suggestion
- intent-aware context
- predictive-to-repair bridge memory
- live runtime whisper
- arbitration logic

### Output
TermOrganism exposes:

- planner suggested mode
- final effective mode
- arbitration winner
- bridge score
- whisper kind / priority
- reason string

This makes route choice inspectable rather than opaque.

---

## Example explain-route output

A typical route explain flow looks like this:

```text
planner_suggested: hot_force
final_effective: fast_v2
intent_reason: intent-aware context avoided hot_force
bridge_route: fast
whisper_kind: path-risk
arbitration_winner: fast_v2
```

This means:

- planner wanted an aggressive route
- context and runtime whispers softened it
- arbitration picked a safer final route

---

## Editor integration

### VS Code
TermOrganism includes a local VS Code extension scaffold with:

- LSP diagnostics
- sidebar whispers
- pre-save checks
- preview fixes command

Key files:
- `editor/vscode/termorganism-vscode/package.json`
- `editor/vscode/termorganism-vscode/extension.js`

### Neovim
TermOrganism includes a Neovim integration module with:

- LSP setup
- pre-save gate
- sidebar command
- preview fixes command

Key file:
- `editor/nvim/termorganism.lua`

Commands in Neovim:
- `:TermOrganismSidebar`
- `:TermOrganismPreSave`
- `:TermOrganismPreviewFixes`

---

## Smoke test

The project includes a full smoke script:

```bash
./bin/termorganism-smoke-full
```

This runs:

1. live predictive analysis
2. pre-save analysis
3. explain-route
4. proactive benchmark
5. fix-preview

This is the quickest full-system demonstration path.

---

## Benchmark interpretation

The benchmark is useful for checking whether:

- planner and final route differ
- whisper signals are influencing route choice
- bridge memory is scoring routes
- arbitration is selecting the safest effective route

High-value indicators:
- non-zero `planner_changed_count`
- non-zero `whisper_cases`
- non-zero `bridge_scored_cases`

---

## Current maturity

TermOrganism is currently a **showable product prototype**.

It already has:

- predictive diagnostics
- repair routing
- intent-aware context
- bridge memory
- live whisper signals
- route arbitration
- editor integration
- safe auto-fixes
- benchmark tooling
- route explainability

---

## Current limitations

Some areas are still early:

- full LSP capability set is still limited
- code actions are intentionally conservative
- many fix types are preview-only
- deeper auto-repair synthesis still needs expansion
- swarm / federated memory is not implemented
- ontological health / bio-inspired runtime model is still roadmap-level

---

## Roadmap direction

Near-term high-value work:

- expand safe auto-fix repertoire
- broaden predictive signature coverage
- improve benchmark coverage and regression tracking
- polish VS Code / Neovim integration
- harden daemon serialization and payload normalization further
- enrich route candidate export and scoring visibility

Longer-term directions:

- temporal / fermented memory
- dynamic route generation
- mutation lab
- distributed / federated repair intelligence
- health / homeostasis style project reporting

---

## Philosophy

TermOrganism is built around the idea that the terminal should not only execute.

It should also:

- notice
- warn
- explain
- suggest
- repair
- verify
- remember

The long-term goal is a runtime that behaves less like a command launcher and more like an adaptive engineering organism.
