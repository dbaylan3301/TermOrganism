from __future__ import annotations

from fnmatch import fnmatch


def path_matches(path: str, pattern: str) -> bool:
    return fnmatch(path, pattern)
