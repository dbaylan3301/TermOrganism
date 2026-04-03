from pathlib import Path

log_path = Path("logs/app.log")
if log_path.exists():
    print(log_path.read_text())
else:
    print("")
