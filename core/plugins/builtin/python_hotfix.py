from __future__ import annotations
from typing import Any
from core.plugins.base import Plugin
from core.experts.base import RepairExpert
from core.mimo.tools import Tool

class PythonHotfixExpert(RepairExpert):
    name = "python_hotfix"
    supported_languages = {"python"}
    def score(self, ctx: Any) -> tuple[float, list[str]]:
        return 0.5, ["python-hotfix plugin"]
    def propose(self, ctx: Any) -> list[dict[str, Any]]:
        return []

class PythonHotfixPlugin(Plugin):
    name = "python-hotfix"
    version = "1.0.0"
    description = "Built-in Python hotfix plugin"
    def register_experts(self) -> list[RepairExpert]:
        return [PythonHotfixExpert()]
    def register_tools(self) -> list[Tool]:
        return []
