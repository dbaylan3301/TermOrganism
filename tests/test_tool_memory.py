from __future__ import annotations
from core.mimo.tools.memory import MemoryTool

def test_memory_tool_has_name():
    tool = MemoryTool()
    assert tool.name()
