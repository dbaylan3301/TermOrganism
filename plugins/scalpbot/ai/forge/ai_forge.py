"""AI Forge - Interactive Coding & Monitoring Environment."""

import os
import datetime
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class AIForge:
    """
    Interactive environment for the bot to code, monitor, and explain itself.
    """

    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "ai_workspace"
        )
        self.modules_dir = os.path.join(self.workspace, "modules")
        self.logs_dir = os.path.join(self.workspace, "logs")
        self.decisions_dir = os.path.join(self.workspace, "decisions")

        self._ensure_dirs()
        self.connect()

    def _ensure_dirs(self):
        """Ensure all directories exist."""
        for d in [self.workspace, self.modules_dir, self.logs_dir, self.decisions_dir]:
            os.makedirs(d, exist_ok=True)

    def connect(self):
        """Initialize connection."""
        self.log("[AI FORGE] System connected.")
        self.log(f"Time: {datetime.datetime.now()}")
        self.log(f"Workspace: {self.workspace}")

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        log_file = os.path.join(self.logs_dir, f"forge_{datetime.date.today()}.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def create_module(self, name: str, content: str) -> str:
        """Create a Python module dynamically."""
        filename = f"{name.lower().replace(' ', '_')}.py"
        path = os.path.join(self.modules_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        self.log(f"Module created: {filename}")
        return path

    def edit_module(self, filename: str, old_str: str, new_str: str) -> bool:
        """Edit an existing module."""
        path = os.path.join(self.modules_dir, filename)

        if not os.path.exists(path):
            self.log(f"File not found: {filename}", "ERROR")
            return False

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace(old_str, new_str)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        self.log(f"Module edited: {filename}")
        return True

    def log_decision(self, decision: Any, explanation: str):
        """Log a trading decision with explanation."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "decision": str(decision),
            "explanation": explanation
        }

        filename = f"decision_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.decisions_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

        self.log(f"Decision recorded: {decision}")

    def show_status(self) -> Dict:
        """Show current system status."""
        status = {
            "forge_active": True,
            "workspace": self.workspace,
            "modules": len(os.listdir(self.modules_dir)) if os.path.exists(self.modules_dir) else 0,
            "logs_today": self._count_today_logs(),
            "decisions_today": self._count_today_decisions()
        }

        self.log("System Status:")
        for k, v in status.items():
            self.log(f"   - {k}: {v}")

        return status

    def _count_today_logs(self) -> int:
        """Count today's log entries."""
        log_file = os.path.join(self.logs_dir, f"forge_{datetime.date.today()}.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                return len(f.readlines())
        return 0

    def _count_today_decisions(self) -> int:
        """Count today's decisions."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        count = 0
        if os.path.exists(self.decisions_dir):
            for f in os.listdir(self.decisions_dir):
                if f.startswith(f"decision_{today}"):
                    count += 1
        return count
