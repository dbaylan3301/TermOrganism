from __future__ import annotations
import pytest
from core.mimo.tools.git import GitTool

@pytest.mark.asyncio
async def test_git_tool_status():
    tool = GitTool()
    result = await tool.execute(command="status")
    assert isinstance(result, str)
