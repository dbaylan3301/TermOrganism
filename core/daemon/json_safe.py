from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def to_json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(x) for x in obj]

    if is_dataclass(obj):
        return to_json_safe(asdict(obj))

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return to_json_safe(obj.to_dict())
        except Exception:
            pass

    if hasattr(obj, "__dict__"):
        try:
            return {
                str(k): to_json_safe(v)
                for k, v in vars(obj).items()
                if not str(k).startswith("_")
            }
        except Exception:
            pass

    return repr(obj)
