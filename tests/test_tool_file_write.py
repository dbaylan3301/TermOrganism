from __future__ import annotations
import pytest
from pathlib import Path
from core.mimo.tools.file_write import FileWriteTool

@pytest.mark.asyncio
async def test_file_write_tool_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    tool = FileWriteTool()
    result = await tool.execute(file_path=str(test_file), content="hello")
    assert "success" in result.lower() or "written" in result.lower()
    assert test_file.read_text() == "hello"

@pytest.mark.asyncio
async def test_file_write_tool_rejects_outside_working_directory():
    tool = FileWriteTool()
    result = await tool.execute(file_path="/tmp/outside_sandbox.txt", content="test")
    assert "error" in result.lower() or "outside" in result.lower()
