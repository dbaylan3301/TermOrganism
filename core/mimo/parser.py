from __future__ import annotations

import json
import re
from typing import Any


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse tool calls from LLM output. Supports JSON code blocks and inline JSON."""
    tool_calls = []
    clean_text = text

    pattern = r'```(?:tool_call|json)?\s*\n?(\{[^`]+\})\n?```'
    for match in re.finditer(pattern, text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if "tool" in data or "function" in data or "name" in data:
                tool_calls.append(data)
                clean_text = clean_text.replace(match.group(0), "")
        except json.JSONDecodeError:
            continue

    pattern2 = r'<tool_call>(.*?)</tool_call>'
    for match in re.finditer(pattern2, text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            tool_calls.append(data)
            clean_text = clean_text.replace(match.group(0), "")
        except json.JSONDecodeError:
            continue

    return clean_text.strip(), tool_calls
