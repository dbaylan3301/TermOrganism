from datetime import datetime

def log_event(message: str):
    print(f"[TermOrganism {datetime.utcnow().isoformat()}] {message}")
