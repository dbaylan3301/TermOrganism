from __future__ import annotations

import difflib


def unified_diff(old: str, new: str, old_name: str = "before", new_name: str = "after") -> str:
    if old == new:
        return ""
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=old_name,
            tofile=new_name,
            lineterm="",
        )
    )
