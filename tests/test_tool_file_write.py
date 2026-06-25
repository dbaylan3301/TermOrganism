from __future__ import annotations
import pytest
from pathlib import Path
from core.mimo.tools.file_write import FileWriteTool

@pytest.mark.asyncio
async def test_file_write_tool_creates_file(tmp_path):
    test_file = tmp_path / "test.txt"
    tool = FileWriteTool()
    result = await tool.execute(file_path=str(test_file), content="hello")
    assert "success" in result.lower() or "written" in result.lower()
    assert test_file.read_text() == "hello"
