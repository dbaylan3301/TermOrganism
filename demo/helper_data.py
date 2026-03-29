from pathlib import Path

def read_payload():
    return Path("data/payload.json").read_text()
