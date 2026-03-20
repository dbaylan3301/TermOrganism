from pathlib import Path

def load_cfg():
    return Path("cfg/app.toml").read_text()
