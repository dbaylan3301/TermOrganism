from __future__ import annotations
import pytest
from core.mimo.tools.git import GitTool

@pytest.mark.asyncio
async def test_git_tool_status():
    tool = GitTool()
    result = await tool.execute(command="status")
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_git_tool_blocks_shell_injection():
    tool = GitTool()
    malicious = "status; rm -rf /"
    result = await tool.execute(command=malicious)
    assert "rm" in result.lower() or "error" in result.lower() or "fatal" in result.lower()
