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
```

### Hot-force import
```bash
TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_import_hotforce.py --json
```

### Direct fast_v2
```bash
TERMORGANISM_FAST_V2=1 TERMORGANISM_USE_DAEMON=1 ./termorganism repair /tmp/broken_import_hotforce.py --json
```

### Default daemon-backed routing
```bash
TERMORGANISM_USE_DAEMON=1 ./termorganism repair demo/broken_runtime.py --json
```

---

## Example output fields

Representative JSON fields include:

- `mode`
- `success`
- `signature`
- `strategy`
- `verify`
- `confidence`
- `fast_v2`
- `fallback_chain`
- `workspace_pool`
- `daemon`

Example:

```json
{
  "mode": "fast_v2",
  "success": true,
  "signature": "importerror:no_module_named",
  "strategy": "import_guard",
  "fast_v2": {
    "used": true,
    "path": "dynamic_import_guard",
    "signature": "importerror:no_module_named"
  },
  "workspace_pool": {
    "source": "pool",
    "latency_ms": 2.926,
    "id": "ws_000"
  },
  "daemon": {
    "socket": "/tmp/termorganism.sock",
    "request_ms": 56.282
  }
}
```

---

## Integration test

Run the integration suite with:

```bash
python3 scripts/integration_test.py
```

Expected coverage:

- Hot Force Runtime
- Hot Force Import
- Fallback Fast Shortcut
- Direct Fast V2 Import

---

## Current strengths

TermOrganism is currently strongest in:

- deterministic hot repair
- daemon-backed low-latency routing
- fast fallback paths
- measurable workspace reuse
- explicit repair telemetry
- branch-verified integration coverage

---

## Current limits

Areas still under active development:

- deeper cross-file performance
- broader multi-language maturity
- stronger production ergonomics
- richer normal-path planning and verification
- wider benchmark coverage beyond current validated paths

---

## Why this exists

Most terminal tooling either runs commands, suggests fixes, or edits files.

TermOrganism is aiming at a stricter loop:

**observe -> classify -> route -> repair -> verify -> score**

The goal is to make repair execution itself a first-class terminal runtime behavior.

---

## Branch note

This README reflects the active milestone branch:

`milestone/4of4-benchmark-green`

That branch contains the currently validated daemon, hot-force, fast fallback, fast_v2, workspace pool telemetry, and integration coverage work.

---

## License

MIT
