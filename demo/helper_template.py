from pathlib import Path

def render_template():
    return Path("templates/main.txt").read_text()
