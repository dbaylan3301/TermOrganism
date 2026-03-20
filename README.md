# TermOrganism

**Semantic self-healing terminal runtime with sandbox-verified repair, cross-file reasoning, and measurable benchmark performance.**

TermOrganism turns a shell from a passive command runner into an adaptive repair-capable runtime.  
It localizes failures, proposes repairs, verifies them in an isolated workspace, and surfaces the highest-confidence fix.

---

## Why this project exists

Most terminal repair tools can suggest patches. Far fewer can:

- repair across files
- verify candidate behavior in a sandbox
- preserve a zero-false-positive profile on a structured benchmark
- expose the full repair trail as machine-readable output

TermOrganism is built around that gap.

---

## Benchmark snapshot

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

```bash
python3 -u benchmarks/runner.py
```

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

That makes it usable both as a CLI tool and as a benchmarking substrate.

---

## Current benchmark-backed positioning

TermOrganism currently demonstrates:

- **sandbox-verified repair**
- **cross-file-aware repair selection**
- **planner-based repair ranking**
- **machine-readable verification output**
- **zero false positives on the current benchmark suite**

---

## Repository focus

This repo currently emphasizes:

- Python-centered repair flows
- shell/runtime/dependency failure handling
- cross-file semantic provider repair
- benchmarkability and reproducibility

---

## Suggested mental model

Think of TermOrganism as:

> a self-healing terminal runtime that does not stop at proposing fixes, but attempts to validate them before trusting them.

---

## Roadmap direction

Near-term leverage points:

- expand benchmark coverage from 20 cases to larger public suites
- reduce cross-file latency
- harden sandbox isolation and execution speed
- improve logical-error and regression-guard coverage
- polish doctor and force-semantic UX
- produce reproducible demo flows and public benchmark comparisons

---

## Status

TermOrganism is no longer just an experimental terminal fixer.  
It now has a green multi-category benchmark with measurable repair behavior and reproducible outputs.

If you are interested in terminal-native repair systems, semantic debugging, cross-file fault localization, or verification-first developer tooling, this is the layer to watch.


## Demo recordings

### Runtime autofix

[![asciicast](https://asciinema.org/a/REPLACE_RUNTIME_CAST_ID.svg)](https://asciinema.org/a/REPLACE_RUNTIME_CAST_ID)

Shows a runtime file-missing failure being repaired and verified.

### Cross-file semantic repair

[![asciicast](https://asciinema.org/a/REPLACE_CROSSFILE_CAST_ID.svg)](https://asciinema.org/a/REPLACE_CROSSFILE_CAST_ID)

Shows provider/caller-aware repair under `--force-semantic`.

### Benchmark run

[![asciicast](https://asciinema.org/a/REPLACE_BENCHMARK_CAST_ID.svg)](https://asciinema.org/a/REPLACE_BENCHMARK_CAST_ID)

Shows the benchmark harness running on the bundled fixture suite.

