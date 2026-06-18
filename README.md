# TermOrganism

**AI-powered code repair engine with conversational assistant, predictive whispers, and semantic routing.**

TermOrganism is a terminal-native platform that combines:

- **Conversational AI Assistant** (`termorg`) — chat with your codebase, get explanations, fix bugs, write code
- **Self-healing Runtime** — detect failures, predict risks, auto-repair with verification
- **Predictive Whispers** — anticipate code issues before they break
- **Semantic Routing** — intelligently route repairs to the right expert

---

## Quick Start

### Installation

```bash
git clone https://github.com/dbaylan3301/TermOrganism.git
cd TermOrganism
pip install -r requirements.txt
```

### AI Assistant (termorg)

```bash
# Get free API key from https://console.groq.com (no credit card needed)
export GROQ_API_KEY="gsk_..."

# Start interactive AI assistant
python3 bin/termorg

# Or single message
python3 bin/termorg "Bu projeyi analiz et"
```

### Supported LLM Providers

| Provider | Model | Cost | Speed |
|----------|-------|------|-------|
| **Groq** (default) | Llama 3.3 70B | Free | Fast |
| OpenAI | GPT-4.1 | Paid | Fast |
| Anthropic | Claude 4 | Paid | Medium |
| Ollama | Local models | Free | Varies |

```bash
# Switch provider
python3 bin/termorg --provider openai
python3 bin/termorg --provider anthropic
python3 bin/termorg --provider ollama
```

### Configuration

```yaml
# ~/.termorganism/config.yaml
llm:
  default_provider: groq
  providers:
    groq:
      api_key: ${GROQ_API_KEY}
      model: llama-3.3-70b-versatile
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4.1
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-sonnet-4-20250514
    ollama:
      base_url: http://localhost:11434
      model: llama3.1:70b
```

---

## Features

### AI Assistant (`termorg`)

Interactive conversational coding assistant with:

- **10 built-in tools**: bash, read, write, edit, glob, grep, git, task, question, memory
- **Multi-provider LLM**: Groq (free), OpenAI, Anthropic, Ollama
- **MiMo-style UI**: Rich terminal interface with purple theme
- **Session memory**: Remembers conversation context
- **Project memory**: Stores learnings across sessions
- **Task tracking**: Persistent task management

```bash
$ python3 bin/termorg

╭─────────────────────────────────────────╮
│ TermOrganism AI                         │
│ Merhaba! Ben TermOrganism.              │
│ Projen hakkında nasıl yardımcı          │
│ olabilirim?                             │
╰─────────────────────────────────────────╯

termorg > Bu dosyadaki hataları bul ve düzelt

⚡ bash(command='python3 -m py_compile core/autofix.py')
⚡ read(file_path='core/autofix.py')
⚡ edit(file_path='core/autofix.py', old_string='...', new_string='...')

Düzeltmeler uygulandı. 3 hata bulundu ve düzeltildi.
```

### Predictive Whispers

Anticipates code issues before they break:

```bash
python3 -m core.watch.watch_cli core/myfile.py
```

Detects:
- Missing imports
- Broken file paths
- eval/exec usage
- Bare except clauses
- Mutable default arguments
- Secret/token leaks

### Self-healing Runtime

```bash
python3 termorganism repair broken_file.py
```

Automatic failure detection → expert routing → repair → verification.

### Watchdog Daemon

```bash
# Start background watcher
python3 -m core.watch.watch_ctl start --loop

# Check status
python3 -m core.watch.watch_ctl status

# Stop
python3 -m core.watch.watch_ctl stop
```

---

## Project Structure

```
TermOrganism/
├── core/
│   ├── mimo/              # AI Assistant (termorg)
│   │   ├── agent.py       # Think-Act-Observe loop
│   │   ├── repl.py        # Interactive REPL
│   │   ├── ui.py          # MiMo theme UI
│   │   ├── llm/           # Multi-provider LLM
│   │   ├── tools/         # 10 built-in tools
│   │   ├── memory/        # Session/project memory
│   │   └── tasks/         # Task tracking
│   ├── autofix.py         # Main repair engine
│   ├── chat/              # Chat system
│   ├── watch/             # Predictive watchdog
│   ├── verify/            # Verification sandbox
│   ├── models/            # Data schemas
│   └── bootstrap/         # Self-healing bootstrap
├── bin/                   # CLI entry points
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml         # Package config
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `termorg` | Interactive AI assistant |
| `termorganism-ask` | AI assistant (alias) |
| `termorganism-watch` | Run predictive analysis |
| `termorganism-live` | Live file monitoring |
| `termorganism-studio` | Visual editor integration |

---

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/

# Run specific test
python3 tests/test_safe_exec.py
```

---

## License

MIT
