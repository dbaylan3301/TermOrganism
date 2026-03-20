from pathlib import Path

def read_log():
    return Path("logs/app.log").read_text() if Path("logs/app.log").exists() else ""
