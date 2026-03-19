#!/usr/bin/env python3
from core.util.safe_exec import execute_safe_suggestions

cases = [
    ("mkdir -p demo_exec && touch demo_exec/sample.txt", True),
    ("chmod +x demo_exec/sample.txt", True),
    ("echo $PATH", True),
    ("sudo apt install bat", False),
    ("rm -rf demo_exec", False),
]

for cmd, should_be_allowed in cases:
    out = execute_safe_suggestions(cmd, dry_run=True)
    print("=" * 72)
    print(cmd)
    print(out)
