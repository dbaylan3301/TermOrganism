from pathlib import Path
import json, time, os

db = Path.home()/".termorganism/memory/repairs.json"

def log_repair(file_path: str, strategy: str, confidence: str, success: bool, context: list, steps=None):
    try:
        data = json.loads(db.read_text(encoding="utf-8"))
    except Exception:
        data = []
    data.append({
        "ts": int(time.time()),
        "file": file_path,
        "strategy": strategy,
        "confidence": confidence,
        "success": success,
        "context": context,
        "steps": steps or [],
        "cwd": os.getcwd(),
    })
    data = data[-4000:]
    db.write_text(json.dumps(data, indent=2), encoding="utf-8")
