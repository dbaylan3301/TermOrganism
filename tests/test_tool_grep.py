from __future__ import annotations
import pytest
from pathlib import Path
from core.mimo.tools.grep import GrepTool

@pytest.mark.asyncio
async def test_grep_tool_finds_pattern(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    pass")
    tool = GrepTool()
    result = await tool.execute(pattern="hello", path=str(tmp_path))
    assert "hello" in result
