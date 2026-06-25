# TermOrganism v2.0.0 Changelog

## Breaking Changes
- `core/autofix.py` is now a backward-compatibility shim. All logic lives in `core/repair/`.
- Plugin API is now the official way to extend experts and tools.

## New Features
- **Plugin API v2**: Plugins can register custom experts and tools via `core/plugins/base.py`
- **Modular repair engine**: `core/repair/` package with separate modules for candidates, planning, verification, hot cache, and events
- **CI/CD**: GitHub Actions for lint (ruff), test (pytest), typecheck (mypy)
- **Expanded test coverage**: ~70+ tests across repair, experts, tools, and plugins

## Improvements
- Version bumped to 0.2.0
- Added `termorg` and `termorganism-watch` entry points to pyproject.toml
- Added ruff and mypy configuration
- Removed legacy migration scripts (`restructure_termorganism.sh`, `relocate_from_core.sh`)

## Internal
- `core/repair/engine.py` — main orchestration loop
- `core/repair/candidates.py` — expert candidate generation
- `core/repair/planner.py` — plan building and ranking
- `core/repair/verify.py` — sandbox verification helpers
- `core/repair/hot_cache.py` — hot cache boost logic
- `core/repair/events.py` — thought event emission
- `core/repair/utils.py` — shared utilities
- `core/plugins/` — plugin base class and registry