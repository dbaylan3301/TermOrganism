from __future__ import annotations
import pytest
from core.mimo.tools.bash import BashTool

@pytest.mark.asyncio
async def test_bash_tool_executes_command():
    tool = BashTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result

@pytest.mark.asyncio
async def test_bash_tool_handles_error():
    tool = BashTool()
    result = await tool.execute(command="exit 1")
    assert "error" in result.lower() or "returncode" in result.lower() or "exit code" in result.lower() or "1" in result

@pytest.mark.asyncio
async def test_bash_tool_rejects_cd_command():
    tool = BashTool()
    result = await tool.execute(command="cd /tmp")
    assert "error" in result.lower() or "not allowed" in result.lower()

@pytest.mark.asyncio
async def test_bash_tool_rejects_cd_alone():
    tool = BashTool()
    result = await tool.execute(command="cd")
    assert "error" in result.lower() or "not allowed" in result.lower()
