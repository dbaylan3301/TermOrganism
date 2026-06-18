from __future__ import annotations

from typing import Any

from . import Tool


class TaskTool(Tool):
    def name(self) -> str:
        return "task"

    def description(self) -> str:
        return "Manage persistent tasks. Create, list, update, complete tasks."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "get", "update", "complete", "delete"],
                    "description": "Action to perform",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for get/update/complete/delete)",
                },
                "summary": {
                    "type": "string",
                    "description": "Task summary (for create)",
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "done", "blocked"],
                    "description": "Task status (for update)",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str = "list", task_id: str | None = None,
                      summary: str | None = None, status: str | None = None,
                      notes: str | None = None, **kwargs: Any) -> str:
        from ..tasks.tracker import get_tracker
        tracker = get_tracker()

        if action == "create":
            if not summary:
                return "Error: summary is required for create"
            tid = tracker.create(summary, notes=notes)
            return f"Task created: {tid}"

        elif action == "list":
            tasks = tracker.list_all()
            if not tasks:
                return "No tasks."
            lines = []
            for t in tasks:
                marker = {"todo": "○", "in_progress": "●", "done": "✓", "blocked": "✗"}.get(t["status"], "?")
                lines.append(f"  {marker} {t['id']}: {t['summary']}")
            return "\n".join(lines)

        elif action == "get":
            if not task_id:
                return "Error: task_id required"
            t = tracker.get(task_id)
            if not t:
                return f"Task {task_id} not found"
            return f"ID: {t['id']}\nSummary: {t['summary']}\nStatus: {t['status']}\nNotes: {t.get('notes', '-')}"

        elif action == "update":
            if not task_id:
                return "Error: task_id required"
            tracker.update(task_id, status=status, notes=notes)
            return f"Task {task_id} updated"

        elif action == "complete":
            if not task_id:
                return "Error: task_id required"
            tracker.update(task_id, status="done")
            return f"Task {task_id} completed"

        elif action == "delete":
            if not task_id:
                return "Error: task_id required"
            tracker.delete(task_id)
            return f"Task {task_id} deleted"

        return f"Unknown action: {action}"
