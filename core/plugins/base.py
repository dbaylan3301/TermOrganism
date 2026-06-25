from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from core.experts.base import RepairExpert
from core.mimo.tools import Tool

class Plugin(ABC):
    name: str = "base"
    version: str = "0.1.0"
    description: str = ""

    def register_experts(self) -> list[RepairExpert]:
        return []

    def register_tools(self) -> list[Tool]:
        return []

    def on_repair_start(self, context: dict[str, Any]) -> None:
        pass

    def on_repair_complete(self, result: dict[str, Any]) -> None:
        pass
