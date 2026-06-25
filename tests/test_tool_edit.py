from __future__ import annotations
import pytest
from pathlib import Path
from core.mimo.tools.edit import EditTool

@pytest.mark.asyncio
async def test_edit_tool_replaces_string(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    tool = EditTool()
    result = await tool.execute(file_path=str(test_file), old_string="hello", new_string="goodbye")
    assert "success" in result.lower() or "edited" in result.lower() or "replaced" in result.lower()
    assert test_file.read_text() == "goodbye world"
