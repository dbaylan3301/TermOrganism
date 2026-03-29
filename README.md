# TermOrganism

**Semantic, self-healing terminal runtime for deterministic hot-fix, fast fallback, and verified repair workflows.**

 ○ TermOrganism turns a shell from a passive command runner into a repair-capable runtime that can:

- detect failure signatures
- route known failures through deterministic hot paths
- fall back into fast repair
- escalate into deeper repair flows when needed
- verify and score outcomes
- expose measurable telemetry for daemon latency and workspace reuse

---

## What it is

● TermOrganism is a repair-oriented terminal runtime and daemon.

○ It is built around a layered execution model:

   **Hot Force Path**
   - deterministic repair for known signatures
   - extremely low-latency path
   - ideal for repeated and high-confidence failures

   **Fast Path**
   - fast shortcut / fast_v2 style repair path
   - lighter than the full pipeline
   - intended for low-latency recovery after hot-force misses

  **Fallback Chain**
   - `hot_force -> fast -> normal`
   - explicit stage reporting
   - timeout-aware behavior

   **Verification + Confidence**
   - syntax / behavioral checks
   - confidence scoring
   - contract-oriented repair result payloads

  **Workspace Pool Telemetry**
   - pooled workspaces
   - reuse / miss stats
   - measurable daemon-side execution.  metadata

---

● Current validated capabilities

The current milestone branch has working evidence for:

- **Hot-force runtime repair**
  - example: `FileNotFoundError` style file-read guard repair

- **Hot-force import repair**
  - example: missing import guarded through deterministic rewrite

- **Fallback into fast shortcut**
  - example flow: `hot_force_failed -> fast`

- **Direct fast_v2 path**
  - explicit `TERMORGANISM_FAST_V2=1` route
  - workspace pool telemetry attached to output

- **Daemon telemetry**
  - per-request timing
  - socket-aware daemon output

- **Integration coverage**
  - hot-force runtime
  - hot-force import
  - fallback fast shortcut
  - direct fast_v2 import

---

● Architecture

● Daemon
Persistent Unix-socket daemon for low-latency repair requests.

● HotCacheForcePath
Deterministic rewrite layer for known signatures.

● FastV2Minimal
Minimal fast path with direct signature-to-repair planning.

● FallbackOrchestrator
Structured escalation:

`hot_force -> fast -> normal`

● RealWorkspacePool
Measured pooled scratch workspaces with telemetry such as:

- source
- acquire latency
- workspace id
- created / reused / missed
- hit rate

---

● Example modes

● Hot-force runtime
```bash
TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_runtime_hotforce.py --json

---
● Hot-force import
```TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_import_hotforce.py --json

---
● Fast v2
```TERMORGANISM_FAST_V2=1 TERMORGANISM_USE_DAEMON=1 ./termorganism repair /tmp/broken_import_hotforce.py --json

---
● Daemon-backed default route
```TERMORGANISM_USE_DAEMON=1 ./termorganism repair demo/broken_runtime.py --json
---

● Example output fields
  ○ *Representative JSON fields include:*
   → mode
   → success
   → signature
   → strategy
   → verify
   → confidence
   → fast_v2
   → fallback_chain
   → workspace_pool
   → daemon

 ● Example telemetry:
   ```{
  "mode": "fast_v2",
  "success": true,
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
    "request_ms": 56.282
  }
}

---
● Integration test
  ○ Run the current integration suite:

`python3 scripts/integration_test.py`

● Expected coverage includes:
 - Hot Force Runtime >
 - Hot Force Import >
 - Fallback Fast Shortcut >
 - Direct Fast V2 Import >
---
● Project status
  °This project is currently strongest in:
  • deterministic hot repair
  • low-latency daemon routing
  • fast fallback paths
  • measured workspace reuse
  • repair telemetry
  • Areas still under active evolution:
  • deeper cross-file performance
  • broader multi-language maturity
  • stronger production ergonomics
  • wider benchmark coverage
  • richer repair planning beyond shortcut-style fast paths
---
  ● Why this project exists
  ○ Most terminal tooling either:
  - runs commands
  - suggests fixes
  - or edits code
  - TermOrganism is aimed at a stricter loop:
  - observe -> classify -> route -> repair -> verify -> score
  - The long-term goal is not only to suggest fixes, but to make repair execution itself a first-class terminal runtime behavior.
---
  ● Repository notes
  ○ The active development surface is the.     → milestone branch:
    → milestone/4of4-benchmark-green
  ● That branch reflects the currently validated daemon, hot-force, fallback, fast_v2, telemetry, and integration-test work.
---









## License

MIT
