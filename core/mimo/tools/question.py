from __future__ import annotations

from typing import Any

from . import Tool


class QuestionTool(Tool):
    def name(self) -> str:
        return "question"

    def description(self) -> str:
        return "Ask the user a question with options. Use when you need user input or approval."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask",
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                    "description": "Answer options",
                },
            },
            "required": ["question"],
        }

    async def execute(self, question: str = "", options: list[dict] | None = None,
                      **kwargs: Any) -> str:
        from ..ui import print_question
        return await print_question(question, options)
