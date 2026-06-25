from __future__ import annotations
from core.mimo.tools.question import QuestionTool

def test_question_tool_has_name():
    tool = QuestionTool()
    assert tool.name()
