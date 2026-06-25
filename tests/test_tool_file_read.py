from __future__ import annotations
import pytest
from pathlib import Path
from core.mimo.tools.file_read import FileReadTool

@pytest.mark.asyncio
async def test_file_read_tool_reads_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    tool = FileReadTool()
    result = await tool.execute(file_path=str(test_file))
    assert "hello world" in result

@pytest.mark.asyncio
async def test_file_read_tool_missing_file():
    tool = FileReadTool()
    result = await tool.execute(file_path="/tmp/nonexistent_file_12345.txt")
    assert "error" in result.lower() or "not found" in result.lower()
