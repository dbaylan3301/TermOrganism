# TermOrganism

**Semantic, self-healing terminal runtime with deterministic hot repair, fast fallback, daemon execution, and measurable workspace telemetry.**

TermOrganism turns a shell from a passive command runner into a repair-capable runtime.

It observes failure signals, classifies known signatures, routes them through deterministic hot paths when possible, falls back into fast repair when needed, and escalates to deeper repair flows when shortcuts are not enough.

---

## Core idea

TermOrganism is built around a layered repair model:

- **Hot Force**
  - deterministic, signature-based repair
  - very low latency
  - best for known high-confidence failures

- **Fast Path**
  - lightweight recovery path after hot-force misses
  - includes `fast_shortcut` and `fast_v2` style execution
  - optimized for lower-latency recovery than the full pipeline

- **Fallback Chain**
  - structured escalation:
  - `hot_force -> fast -> normal`

- **Verification**
  - syntax / lightweight verification on fast paths
  - richer verification and scoring on deeper paths

- **Workspace Pool Telemetry**
  - pooled workspaces
  - reuse / miss stats
  - measurable daemon-side latency and workspace allocation metadata

---

## What is currently validated

This milestone branch has working evidence for:

### 1. Hot-force runtime repair
Deterministic repair for file-read runtime failures such as missing log files.

Example signature:
- `filenotfounderror:open:runtime`

### 2. Hot-force import repair
Deterministic repair for simple missing-import cases.

Example signature:
- `importerror:no_module_named`

### 3. Hot-force miss -> fast fallback
If hot-force does not match, TermOrganism can fall through into a fast shortcut path.

Observed chain:
- `hot_force_failed -> fast`

### 4. Direct `fast_v2`
`TERMORGANISM_FAST_V2=1` routes into a minimal fast path with workspace pool telemetry.

### 5. Daemon-backed execution
Persistent Unix-socket daemon for lower-latency execution and measurable request timing.

### 6. Workspace pool telemetry
Measured workspace pool metadata is attached to relevant responses, including:

- workspace source
- acquire latency
- workspace id
- created / reused / missed counts
- hit rate

### 7. Integration coverage
Integration tests currently cover:

- Hot Force Runtime
- Hot Force Import
- Fallback Fast Shortcut
- Direct Fast V2 Import

---

## Architecture

### Daemon
A persistent Unix-socket daemon handles repair requests and keeps hot paths cheap.

### HotCacheForcePath
Deterministic rewrite layer for known signatures.

### FastV2Minimal
Minimal direct fast path for known signatures and import/runtime guard cases.

### FallbackOrchestrator
Explicit staged routing:

`hot_force -> fast -> normal`

### RealWorkspacePool
Measured pooled scratch workspaces with telemetry exposed in JSON output.

---

## Example commands

### Hot-force runtime
```bash
TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_runtime_hotforce.py --json

## License

MIT
