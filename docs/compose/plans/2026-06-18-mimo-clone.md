# TermOrganism AI Asistan - MiMo Klonu Implementation Plan

> **For agentic workers:** Use compose:subagent or compose:execute to implement this plan.

**Goal:** Turn TermOrganism into a full conversational AI coding assistant (MiMo clone) with REPL, multi-backend LLM, tool system, memory, tasks, skills, and workflows.

**Architecture:** 5-layer architecture: REPL → Agent Loop → Tools → LLM Backend → Memory. Each layer communicates through well-defined interfaces.

**Tech Stack:** Python 3.10+, Rich (terminal UI), httpx (async HTTP), OpenAI/Anthropic/Ollama APIs

---

## File Structure

```
core/
├── mimo/                    # New AI assistant package
│   ├── __init__.py
│   ├── repl.py              # Interactive REPL loop
│   ├── ui.py                # Rich terminal UI (MiMo theme)
│   ├── agent.py             # Think-Act-Observe agent loop
│   ├── context.py           # Context window management
│   ├── parser.py            # Tool call parsing from LLM output
│   ├── config.py            # Configuration management
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── session.py       # Session memory
│   │   ├── project.py       # Project memory
│   │   └── global.py        # Global preferences
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py          # Base LLM provider
│   │   ├── openai.py        # OpenAI/compatible provider
│   │   ├── anthropic.py     # Anthropic Claude provider
│   │   ├── ollama.py        # Local Ollama provider
│   │   ├── router.py        # Provider selection
│   │   └── stream.py        # Streaming support
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py      # Tool registry
│   │   ├── bash.py          # Shell execution
│   │   ├── file_read.py     # Read files
│   │   ├── file_write.py    # Write files
│   │   ├── edit.py          # Edit files
│   │   ├── glob.py          # File search
│   │   ├── grep.py          # Content search
│   │   ├── git.py           # Git operations
│   │   ├── task.py          # Task management
│   │   ├── question.py      # Ask user
│   │   ├── memory.py        # Memory operations
│   │   └── skill.py         # Skill loading
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── tracker.py       # Persistent task tracking
│   └── skills/
│       ├── __init__.py
│       └── loader.py        # Skill loading system
```

---

## Task 1: Configuration System

**Files:**
- Create: `core/mimo/config.py`
- Create: `~/.termorganism/config.yaml` (default)

## Task 2: LLM Backend (Multi-Provider)

**Files:**
- Create: `core/mimo/llm/base.py`
- Create: `core/mimo/llm/openai.py`
- Create: `core/mimo/llm/anthropic.py`
- Create: `core/mimo/llm/ollama.py`
- Create: `core/mimo/llm/router.py`
- Create: `core/mimo/llm/stream.py`

## Task 3: Tool System

**Files:**
- Create: `core/mimo/tools/registry.py`
- Create: `core/mimo/tools/bash.py`
- Create: `core/mimo/tools/file_read.py`
- Create: `core/mimo/tools/file_write.py`
- Create: `core/mimo/tools/edit.py`
- Create: `core/mimo/tools/glob.py`
- Create: `core/mimo/tools/grep.py`
- Create: `core/mimo/tools/git.py`
- Create: `core/mimo/tools/task.py`
- Create: `core/mimo/tools/question.py`
- Create: `core/mimo/tools/memory.py`
- Create: `core/mimo/tools/skill.py`

## Task 4: Agent Loop

**Files:**
- Create: `core/mimo/agent.py`
- Create: `core/mimo/context.py`
- Create: `core/mimo/parser.py`

## Task 5: Memory System

**Files:**
- Create: `core/mimo/memory/session.py`
- Create: `core/mimo/memory/project.py`
- Create: `core/mimo/memory/global.py`

## Task 6: Task Tracking

**Files:**
- Create: `core/mimo/tasks/tracker.py`

## Task 7: REPL & UI (MiMo Theme)

**Files:**
- Create: `core/mimo/repl.py`
- Create: `core/mimo/ui.py`
- Create: `bin/termorg` (entry point)
