from pathlib import Path

print(Path(".env.local").read_text())
