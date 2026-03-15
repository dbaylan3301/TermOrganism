# TermOrganism

![license](https://img.shields.io/github/license/dbaylan3301/TermOrganism)
![version](https://img.shields.io/github/v/tag/dbaylan3301/TermOrganism)
![stars](https://img.shields.io/github/stars/dbaylan3301/TermOrganism)

Context-aware, self-healing terminal runtime with local + AI repair.


**Context-aware, self-healing terminal runtime with local + AI repair.**

## Demo — Autofix

[![asciicast](https://asciinema.org/a/A5DXhtQFKL7iclc5.svg)](https://asciinema.org/a/A5DXhtQFKL7iclc5)

---


## Quick Example

Broken code:

```python
print(Hello, World")

python test1.py

output:
[organism] predicted failure
[organism] consulting model
[organism] AI repair success
[organism] confidence: medium
[organism] sandbox passed
Hello, World

---
One-Line =>

git clone https://github.com/dbaylan3301/TermOrganism.git
cd TermOrganism && bash install.sh

## Philosophy

Most terminals are passive.

They execute commands, print errors, and stop.

TermOrganism explores a different idea:

> The terminal should observe, predict, repair, verify, remember, and adapt.

Instead of just running commands, the shell becomes an intelligent runtime layer.

## Overview

**TermOrganism** is a context-aware, self-healing developer terminal runtime.

It transforms a shell from a passive command runner into an adaptive system capable of:

- predicting failures
- repairing broken code
- verifying fixes in a sandbox
- learning from developer workflows

---

## Roadmap

Planned improvements:

- multi-language repair
- plugin architecture
- rule registry for local repair
- smarter workflow learning
- local LLM fallback

## Contributing

Contributions are welcome.

If you have ideas for repair rules, context detection, or workflow learning improvements, feel free to open an issue or submit a pull request.


## Core Capabilities

- Execution guard
- Local repair engine
- AI repair engine (Groq)
- Sandbox verification
- Confidence labels
- Repair memory
- Command learning brain
- Project-aware suggestions

---

## Installation

### 1. Install dependency

```bash

pip install requests
---
Set Groq API key

echo 'export GROQ_API_KEY="YOUR_GROQ_KEY"' >> ~/.zshrc

source ~/.zshrc


Install TermOrganism

bash install.sh

Commands

omega-autofix broken.py
omega-stats
bash doctor.sh
bash proof.sh

Project Structure

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

Status

*Active prototype.
Core repair, memory, and shell integration are working.*

---

