from __future__ import annotations
import pytest
from core.mimo.tools.task import TaskTool

@pytest.mark.asyncio
async def test_task_tool_creates_task():
    tool = TaskTool()
    result = await tool.execute(operation="create", summary="Test task")
    assert isinstance(result, str)
