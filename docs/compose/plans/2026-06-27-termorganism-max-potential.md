# TermOrganism — Maximum Potential Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical bugs, add structured logging, refactor the daemon monolith, harden security, improve test coverage, and clean up dependency management — bringing TermOrganism to production-quality.

**Architecture:** The plan is organized into 6 phases, each producing a self-contained, testable improvement. Phase 1 fixes P0 critical bugs. Phase 2 adds logging infrastructure. Phase 3 refactors the daemon. Phase 4 hardens security. Phase 5 improves test coverage. Phase 6 cleans up code quality.

**Tech Stack:** Python 3.10+, asyncio, Unix sockets, SQLite, Rich, httpx, pytest

---

## Phase 1: Critical Fixes (P0)

### Task 1: Fix pyproject.toml Dependencies

**Covers:** Dependency alignment, installability

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Fix pyproject.toml dependencies**

```toml
# In pyproject.toml [project] dependencies, replace:
dependencies = [
    "rich>=13.7.0",
    "httpx>=0.27.0",
    "pyyaml>=6.0",
]
```

Remove `aiohttp` (unused). Add `httpx` (actual HTTP client used by all LLM providers).

- [ ] **Step 2: Clean requirements.txt**

```
rich>=13.7.0
httpx>=0.27.0
pyyaml>=6.0
```

Remove `requests` (unused), `yfinance`, `numpy`, `pandas`, `websocket-client` (only used by optional scalpbot plugin, should be in optional deps).

- [ ] **Step 3: Add optional scalpbot dependencies to pyproject.toml**

```toml
[project.optional-dependencies]
scalpbot = [
    "yfinance>=0.2.36",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
]
```

- [ ] **Step 4: Verify installation works**

Run: `pip install -e .`
Expected: Installs without errors, `httpx` is available.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "fix: align dependencies — add httpx, remove unused aiohttp/requests"
```

---

### Task 2: Fix PluginLoader/PluginRegistry Type Mismatch

**Covers:** Plugin system correctness

**Files:**
- Modify: `core/plugins/loader.py`
- Modify: `core/plugins/registry.py`
- Modify: `tests/test_plugin_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plugin_registry.py — add at end
def test_registry_register_manifest_rejected():
    """PluginRegistry.register() must reject non-Plugin objects."""
    from core.plugins.registry import PluginRegistry
    from core.plugins.manifest import PluginManifest
    registry = PluginRegistry()
    manifest = PluginManifest(name="test", version="1.0", description="t", entry_point="x:y")
    try:
        registry.register(manifest)
        assert False, "Should have raised TypeError"
    except TypeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_plugin_registry.py::test_registry_register_manifest_rejected -v`
Expected: FAIL (currently no TypeError raised)

- [ ] **Step 3: Fix PluginRegistry.register() to validate type**

```python
# core/plugins/registry.py — in register() method, add type check at top:
def register(self, plugin: Plugin) -> None:
    if not isinstance(plugin, Plugin):
        raise TypeError(f"Expected Plugin instance, got {type(plugin).__name__}")
    # ... rest of existing code
```

- [ ] **Step 4: Fix PluginLoader.load_into() to import and instantiate Plugin**

```python
# core/plugins/loader.py — fix load_into() to:
# 1. Import the entry_point string
# 2. Instantiate the Plugin subclass
# 3. Pass the Plugin instance to registry.register()
import importlib

def load_into(self, registry: 'PluginRegistry') -> None:
    for manifest in self._discover():
        try:
            module_path, attr = manifest.entry_point.rsplit(":", 1)
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, attr)
            plugin_instance = plugin_cls()
            registry.register(plugin_instance)
        except Exception as e:
            print(f"Warning: Failed to load plugin {manifest.name}: {e}", file=sys.stderr)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_plugin_registry.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add core/plugins/loader.py core/plugins/registry.py tests/test_plugin_registry.py
git commit -m "fix: PluginLoader/PluginRegistry type mismatch — validate Plugin type"
```

---

### Task 3: Fix git.py Command Injection

**Covers:** Security — command injection

**Files:**
- Modify: `core/mimo/tools/git.py`
- Modify: `tests/test_tool_git.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tool_git.py — add:
import pytest
from core.mimo.tools.git import GitTool

@pytest.mark.asyncio
async def test_git_tool_rejects_shell_injection(tmp_path):
    tool = GitTool()
    tool._cwd = str(tmp_path)
    # Attempt command injection via git command parameter
    result = await tool.execute({"command": "status; rm -rf /"})
    # Should NOT execute the injected command
    assert "rm" not in str(result).lower() or "error" in str(result).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_tool_git.py::test_git_tool_rejects_shell_injection -v`
Expected: FAIL (injected command may execute)

- [ ] **Step 3: Fix git.py to use shell=False with argument list**

```python
# core/mimo/tools/git.py — replace shell=True with shell=False:
import shlex

async def execute(self, args: dict) -> str:
    command = args.get("command", "")
    # Parse command into args list, prevent injection
    parts = shlex.split(command)
    if not parts:
        return "Error: empty command"
    
    cmd_list = ["git"] + parts
    
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            cwd=self._cwd or ".",
            timeout=30,
            shell=False,  # CRITICAL: never shell=True with user input
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Error: git command timed out"
    except Exception as e:
        return f"Error: {e}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_tool_git.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/mimo/tools/git.py tests/test_tool_git.py
git commit -m "fix: command injection in git.py — use shell=False with argument list"
```

---

### Task 4: Remove json.dumps Monkey-Patch

**Covers:** Daemon correctness, third-party compatibility

**Files:**
- Modify: `core/daemon/server.py`
- Modify: `core/daemon/json_safe.py`

- [ ] **Step 1: Read current monkey-patch code**

Read `core/daemon/server.py` lines 15-30 and `core/daemon/json_safe.py` to understand the current approach.

- [ ] **Step 2: Replace monkey-patch with a safe_json_dumps utility**

```python
# core/daemon/json_safe.py — add:
import json
from typing import Any

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """JSON dumps that handles non-serializable objects safely."""
    return json.dumps(to_json_safe(obj), **kwargs)
```

- [ ] **Step 3: Update server.py to use safe_json_dumps instead of monkey-patching**

Remove the global `json.dumps = _json_dumps_safe` line. Replace all `json.dumps(...)` calls in server.py with `safe_json_dumps(...)`.

- [ ] **Step 4: Run existing tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_plugin_registry.py tests/test_tool_git.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/daemon/server.py core/daemon/json_safe.py
git commit -m "fix: remove json.dumps monkey-patch — use safe_json_dumps utility"
```

---

## Phase 2: Structured Logging

### Task 5: Add Logging Framework

**Cffects:** All modules — replaces print-to-stderr with structured logging

**Files:**
- Create: `core/util/logging.py` (replace existing minimal version)
- Modify: `core/daemon/server.py` (replace print statements)
- Modify: `core/repair/engine.py` (add logging)
- Modify: `core/mimo/agent.py` (add logging)
- Modify: `core/plugins/registry.py` (log instead of silent except)

- [ ] **Step 1: Create logging configuration module**

```python
# core/util/logging.py
import logging
import sys
from typing import Optional

_CONFIGURED = False

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )

def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
```

- [ ] **Step 2: Add logging to daemon server**

Replace `print(..., file=sys.stderr)` calls in `core/daemon/server.py` with `logger.info(...)`, `logger.warning(...)`, `logger.error(...)`.

- [ ] **Step 3: Add logging to repair engine**

Add `logger = get_logger("termorganism.repair")` to `core/repair/engine.py` and log key events: repair start, candidate count, plan ranking, verification result.

- [ ] **Step 4: Add logging to plugin registry**

Replace silent `except Exception: pass` in `core/plugins/registry.py` with `logger.warning(...)` or `logger.error(...)`.

- [ ] **Step 5: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=30`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add core/util/logging.py core/daemon/server.py core/repair/engine.py core/plugins/registry.py
git commit -m "feat: add structured logging framework — replace print-to-stderr"
```

---

## Phase 3: Daemon Refactoring

### Task 6: Refactor handle_request Monolith

**Covers:** Daemon maintainability, duplicated logic

**Files:**
- Modify: `core/daemon/server.py`

- [ ] **Step 1: Extract routing logic into separate methods**

Break `handle_request` into focused methods:
- `_parse_request(data: bytes) -> dict`
- `_build_routing_context(file_path, request) -> dict`
- `_run_repair_pipeline(file_path, context) -> dict`
- `_build_response(result, context) -> dict`
- `_post_process(result, context) -> None`

- [ ] **Step 2: Remove duplicated calls**

The current code calls `build_proactive_signals()` twice and `enrich_planner_reason()` twice with identical arguments. Keep only the second call (which overwrites the first).

- [ ] **Step 3: Fix variable scope issues**

Replace `"routing_meta" in locals()` guard with explicit initialization:
```python
routing_meta = None
agent_results = None
# ... then use if routing_meta is not None: instead of "routing_meta" in locals()
```

- [ ] **Step 4: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=30`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/daemon/server.py
git commit -m "refactor: break handle_request monolith into focused methods"
```

---

### Task 7: Add LLM Retry Logic

**Covers:** LLM reliability, transient failure handling

**Files:**
- Create: `core/llm/retry.py`
- Modify: `core/mimo/llm/groq.py`
- Modify: `core/mimo/llm/openai.py`
- Modify: `core/mimo/llm/anthropic.py`
- Modify: `core/mimo/llm/ollama.py`

- [ ] **Step 1: Create retry utility**

```python
# core/llm/retry.py
import asyncio
import logging
from typing import Callable, TypeVar

logger = logging.getLogger("termorganism.llm.retry")
T = TypeVar("T")

async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> T:
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM call failed after {max_retries} attempts: {e}")
    raise last_exception
```

- [ ] **Step 2: Wrap LLM provider chat methods with retry**

In each provider's `chat()` method, wrap the httpx call with `retry_with_backoff`.

- [ ] **Step 3: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=30`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add core/llm/retry.py core/mimo/llm/groq.py core/mimo/llm/openai.py core/mimo/llm/anthropic.py core/mimo/llm/ollama.py
git commit -m "feat: add LLM retry with exponential backoff"
```

---

## Phase 4: Security Hardening

### Task 8: Add Daemon Socket Permissions

**Covers:** Daemon security

**Files:**
- Modify: `core/daemon/server.py`

- [ ] **Step 1: Set restrictive socket permissions**

```python
# In daemon start(), after creating the socket:
import os
os.chmod(sock_path, 0o600)  # Only owner can read/write
```

- [ ] **Step 2: Add request size limit**

```python
# In handle_request(), add:
MAX_REQUEST_SIZE = 1_048_576  # 1MB
if len(data) > MAX_REQUEST_SIZE:
    response = {"status": "error", "error": "Request too large"}
    writer.write(json.dumps(response).encode() + b"\n")
    await writer.drain()
    return
```

- [ ] **Step 3: Commit**

```bash
git add core/daemon/server.py
git commit -m "feat: daemon security — socket permissions + request size limit"
```

---

### Task 9: Add Tool Sandboxing Boundaries

**Covers:** Tool security

**Files:**
- Modify: `core/mimo/tools/bash.py`
- Modify: `core/mimo/tools/file_write.py`

- [ ] **Step 1: Add working directory restriction to BashTool**

```python
# In BashTool, validate that command doesn't escape working directory
# for cd commands:
if "cd " in command:
    return "Error: cd commands are not allowed in sandboxed mode"
```

- [ ] **Step 2: Add path validation to FileWriteTool**

```python
# In FileWriteTool.execute(), validate write path is within allowed directories
import os
real_path = os.path.realpath(path)
# Check against allowed base directories
```

- [ ] **Step 3: Commit**

```bash
git add core/mimo/tools/bash.py core/mimo/tools/file_write.py
git commit -m "feat: tool sandboxing — restrict cd commands and validate write paths"
```

---

## Phase 5: Test Coverage

### Task 10: Add Agent Loop Tests

**Covers:** core/mimo/agent.py test coverage

**Files:**
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write agent loop tests**

```python
# tests/test_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.mimo.agent import Agent

@pytest.mark.asyncio
async def test_agent_process_message():
    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.model = "test-model"
    agent.config.system_prompt = "You are a test agent."
    agent.tools = MagicMock()
    agent.tools.list_tools.return_value = []
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = []
    agent.llm = AsyncMock()
    agent.llm.chat.return_value = MagicMock(
        content="I'll help you with that.",
        tool_calls=None
    )
    
    result = await agent.process_message("Hello")
    assert result is not None
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_agent_handles_tool_call():
    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.model = "test-model"
    agent.config.system_prompt = "test"
    agent.tools = MagicMock()
    tool = MagicMock()
    tool.name = "bash"
    tool.execute = AsyncMock(return_value="output")
    agent.tools.get_tool.return_value = tool
    agent.tools.list_tools.return_value = [tool]
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = []
    agent.llm = AsyncMock()
    
    # First call returns tool call, second returns text
    from core.mimo.llm.base import LLMResponse, LLMToolCall
    tool_call = LLMToolCall(id="1", name="bash", arguments={"command": "ls"})
    agent.llm.chat.side_effect = [
        MagicMock(content=None, tool_calls=[tool_call]),
        MagicMock(content="Done", tool_calls=None),
    ]
    
    result = await agent.process_message("list files")
    assert result is not None
```

- [ ] **Step 2: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_agent.py
git commit -m "test: add agent loop tests"
```

---

### Task 11: Add LLM Provider Tests

**Covers:** core/mimo/llm/ test coverage

**Files:**
- Create: `tests/test_llm_providers.py`

- [ ] **Step 1: Write provider tests**

```python
# tests/test_llm_providers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.mimo.llm.base import LLMMessage

@pytest.mark.asyncio
async def test_groq_provider_chat():
    from core.mimo.llm.groq import GroqProvider
    provider = GroqProvider(api_key="test-key", model="test-model")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello!"}}]
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.chat([LLMMessage(role="user", content="Hi")])
        assert result.content == "Hello!"

@pytest.mark.asyncio
async def test_openai_provider_chat():
    from core.mimo.llm.openai import OpenAIProvider
    provider = OpenAIProvider(api_key="test-key", model="test-model")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hi there!"}}]
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.chat([LLMMessage(role="user", content="Hello")])
        assert result.content == "Hi there!"
```

- [ ] **Step 2: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_llm_providers.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_llm_providers.py
git commit -m "test: add LLM provider tests"
```

---

### Task 12: Convert Script-Style Phase Tests to Proper Pytest

**Covers:** Test quality improvement

**Files:**
- Modify: `tests/test_phase101_cross_file.py` (example — apply pattern to others)

- [ ] **Step 1: Convert one phase test as template**

```python
# tests/test_phase101_cross_file.py — convert from script to pytest:
import pytest
from unittest.mock import patch
from core.autofix import run_autofix

def test_cross_file_repair():
    """Test cross-file repair capability."""
    result = run_autofix(
        file_path="demo/broken_cross_import.py",
        mode="fast",
    )
    assert result is not None
    assert "status" in result
    # Don't assert specific fix — just verify pipeline runs
```

- [ ] **Step 2: Run converted test**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_phase101_cross_file.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_phase101_cross_file.py
git commit -m "test: convert phase101 test from script to proper pytest"
```

---

## Phase 6: Code Quality Cleanup

### Task 13: Remove Unused Imports and Dead Code

**Covers:** Code cleanliness

**Files:**
- Modify: `core/ui/repl.py`
- Modify: `core/watch/watch_ctl.py`
- Modify: `core/autofix.py`

- [ ] **Step 1: Remove unused imports from core/ui/repl.py**

Remove: `Group`, `Text`, `Live` from rich imports. Remove `suppress` from contextlib. Remove `TermOrganismAnimator` import.

- [ ] **Step 2: Replace re-implemented contextlib.suppress in watch_ctl.py**

Replace custom `contextlib_suppress` class with `from contextlib import suppress`.

- [ ] **Step 3: Remove dead finalize_repair_payload from autofix.py**

Delete the no-op `finalize_repair_payload()` function.

- [ ] **Step 4: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=30`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/ui/repl.py core/watch/watch_ctl.py core/autofix.py
git commit -m "cleanup: remove unused imports, dead code, re-implemented stdlib"
```

---

### Task 14: Fix Hardcoded Paths

**Cffects:** Portability

**Files:**
- Modify: `core/llm/mimo_brain.py`

- [ ] **Step 1: Replace hardcoded paths with env/config-based defaults**

```python
# core/llm/mimo_brain.py — replace hardcoded defaults:
MIMO_BIN = os.getenv("MIMO_BIN", shutil.which("mimo") or "mimo")
TERMORGANISM_CWD = os.getenv("TERMORGANISM_CWD", os.getcwd())
```

- [ ] **Step 2: Run tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=30`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add core/llm/mimo_brain.py
git commit -m "fix: replace hardcoded paths with env-based defaults"
```

---

### Task 15: Expand CI Matrix and Add Coverage

**Cffects:** CI/CD quality

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Update CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check core/ tests/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pip install pytest-cov
      - run: pytest tests/ -v --cov=core --cov-report=xml --timeout=30
      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.12'

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: mypy core/ --ignore-missing-imports
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: expand test matrix (3.10-3.12), add coverage reporting"
```

---

### Task 16: Final Verification

**Covers:** All changes verified

**Files:** (none — verification only)

- [ ] **Step 1: Run full test suite**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `cd /home/craftzzdog/TermOrganism && ruff check core/ tests/`
Expected: No errors (or only pre-existing warnings)

- [ ] **Step 3: Run type checker**

Run: `cd /home/craftzzdog/TermOrganism && mypy core/ --ignore-missing-imports`
Expected: No new errors

- [ ] **Step 4: Verify package installs cleanly**

Run: `cd /home/craftzzdog/TermOrganism && pip install -e .`
Expected: Installs without errors

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final verification — all tests pass, linter clean"
```

---

## Summary

| Phase | Tasks | Impact |
|-------|-------|--------|
| 1: Critical Fixes | Tasks 1-4 | P0 bugs fixed, project installable, plugins work, no injection |
| 2: Logging | Task 5 | Structured logging across all modules |
| 3: Daemon | Tasks 6-7 | Maintainable daemon, LLM reliability |
| 4: Security | Tasks 8-9 | Socket permissions, tool sandboxing |
| 5: Tests | Tasks 10-12 | Agent, LLM, phase test coverage |
| 6: Cleanup | Tasks 13-16 | Code quality, CI, verification |

**Total: 16 tasks across 6 phases**
