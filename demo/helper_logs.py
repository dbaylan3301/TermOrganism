from pathlib import Path

def tail_log():
    return Path("logs/app.log").read_text()
