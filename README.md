# TermOrganism

**Context-aware, self-healing, memory-backed developer terminal runtime.**

TermOrganism turns a shell from a passive command runner into an adaptive repair-capable runtime.

It watches terminal workflows, predicts failure, applies local or AI-assisted repair, verifies fixes in sandbox, learns from outcomes, and adapts suggestions to project context.

---

## What it does

Core capabilities:

- Execution guard
- Local repair engine
- AI repair engine
- Sandbox verification
- Confidence labels
- Repair memory
- Command learning brain
- Project-aware suggestions

---

## Install

1. Install dependency:

    pip install requests

2. Set Groq API key:

    echo 'export GROQ_API_KEY="YOUR_GROQ_KEY"' >> ~/.zshrc
    source ~/.zshrc

3. Install TermOrganism:

    bash install.sh

---

## Commands

    omega-autofix broken.py
    omega-stats
    bash doctor.sh
    bash proof.sh

---

## Project structure

    TermOrganism/
    ├── README.md
    ├── LICENSE
    ├── .gitignore
    ├── install.sh
    ├── doctor.sh
    ├── proof.sh
    ├── bin/
    ├── core/
    ├── zsh/
    ├── memory/
    ├── examples/
    └── demo/

---

## Status

Active prototype.
Core repair, memory, and shell integration are working.
terminal
zsh
python
ai
groq
shell
cli
automation
developer-tools
productivity
