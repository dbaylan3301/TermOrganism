from __future__ import annotations
import pytest
from core.mimo.tools.glob import GlobTool

@pytest.mark.asyncio
async def test_glob_tool_finds_files(tmp_path):
    (tmp_path / "test.py").write_text("")
    tool = GlobTool()
    result = await tool.execute(pattern="*.py", path=str(tmp_path))
    assert "test.py" in result
