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

- static validation
- isolated runtime replay
- behavioral verification
- synthesized regression guards
- and contract propagation

### Memory and Ranking Layer

- historical priors
- winner-only success propagation
- semantic strategy weighting
- and blast radius and risk balancing

## Flagship behavior

A representative TermOrganism workflow now supports this pattern:

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

## Example use cases

TermOrganism can repair a broken Python file, analyze a shell or runtime failure, run semantic analysis even if the target currently passes, and evaluate execution suggestions without actually running them.

## Example output themes

Depending on the failure class, TermOrganism can return structured information such as selected expert, semantic localization summary, competing candidates, chosen plan, sandbox result, behavioral verification result, regression guard result, contract propagation result, semantic rank tuple, and target provider and caller files.

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

```bash
git clone https://github.com/dbaylan3301/TermOrganism.git
cd TermOrganism
```

## Running

General pattern:

```bash
./termorganism <target> [options]
```

## Who this is for

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
