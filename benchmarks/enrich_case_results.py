from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
CASES_PATH = RESULTS_DIR / "case_results.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _extract_case_list(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]

    if isinstance(obj, dict):
        for key in ("cases", "results", "items"):
            v = obj.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]

        if obj and all(isinstance(v, dict) for v in obj.values()):
            out = []
            for k, v in obj.items():
                item = dict(v)
                item.setdefault("case_name", str(k))
                out.append(item)
            return out

    return []


def _replace_case_list(obj: Any, new_cases: list[dict[str, Any]]) -> Any:
    if isinstance(obj, list):
        return new_cases

    if isinstance(obj, dict):
        for key in ("cases", "results", "items"):
            if isinstance(obj.get(key), list):
                obj[key] = new_cases
                return obj

        if obj and all(isinstance(v, dict) for v in obj.values()):
            rebuilt = {}
            for case in new_cases:
                name = str(case.get("case_name") or case.get("name") or case.get("id") or f"case_{len(rebuilt)+1}")
                rebuilt[name] = case
            return rebuilt

    return new_cases


def _first_present(d: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in d:
            return d.get(key)
    return None


def _extract_case_name(case: dict[str, Any], index: int) -> str:
    name = _first_present(
        case,
        "case_name",
        "name",
        "id",
        "case_id",
        "slug",
        "title",
        "target",
        "target_file",
        "file_path",
    )
    if name is not None:
        return str(name)
    return f"case_{index+1}"


def _json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return [_json_safe(v) for v in sorted(obj, key=lambda x: str(x))]
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return _json_safe(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {"_type": obj.__class__.__name__, **{str(k): _json_safe(v) for k, v in vars(obj).items()}}
        except Exception:
            pass
    return repr(obj)


def _walk_confidence(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        conf = obj.get("confidence")
        if isinstance(conf, dict) and isinstance(conf.get("score"), (int, float)):
            return _json_safe(conf)
        for v in obj.values():
            got = _walk_confidence(v)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for item in obj:
            got = _walk_confidence(item)
            if got is not None:
                return got
    return None


def _walk_metrics(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        metrics = obj.get("metrics")
        if isinstance(metrics, dict):
            keys = {"total_ms", "semantic_ms", "planning_ms", "selection_ms", "mode", "fast"}
            if any(k in metrics for k in keys):
                return _json_safe(metrics)
        for v in obj.values():
            got = _walk_metrics(v)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for item in obj:
            got = _walk_metrics(item)
            if got is not None:
                return got
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _extract_last_json_object(text: str) -> Any:
    text = text.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    decoder = json.JSONDecoder()
    best = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch not in "{[":
            i += 1
            continue
        try:
            obj, end = decoder.raw_decode(text[i:])
            best = obj
            i += max(1, end)
        except Exception:
            i += 1
    return best


def _find_stdout_payload(case_name: str) -> Any:
    exact = RESULTS_DIR / f"{case_name}.stdout.txt"
    if exact.exists():
        return _extract_last_json_object(_read_text(exact))

    # fallback: prefix / normalized matching
    norm = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_name)
    cands = sorted(RESULTS_DIR.glob("*.stdout.txt"))
    for cand in cands:
        stem = cand.name[:-11]  # strip .stdout.txt
        if stem == case_name or stem == norm or case_name in stem or norm in stem:
            payload = _extract_last_json_object(_read_text(cand))
            if payload is not None:
                return payload
    return None


def enrich_case_results() -> int:
    obj = _load_json(CASES_PATH)
    if obj is None:
        print("[enrich] no case_results.json found", file=sys.stderr)
        return 1

    cases = _extract_case_list(obj)
    updated = 0

    for i, case in enumerate(cases):
        name = _extract_case_name(case, i)
        payload = _find_stdout_payload(name)
        if payload is None:
            continue

        conf = _walk_confidence(payload)
        metrics = _walk_metrics(payload)

        changed = False
        if conf is not None and "confidence" not in case:
            case["confidence"] = conf
            changed = True

        if metrics is not None:
            cur = case.get("metrics")
            if not isinstance(cur, dict):
                case["metrics"] = metrics
                changed = True
            else:
                merged = dict(cur)
                for k, v in metrics.items():
                    if k not in merged:
                        merged[k] = v
                        changed = True
                case["metrics"] = merged

        if changed:
            updated += 1

    obj = _replace_case_list(obj, cases)
    _dump_json(CASES_PATH, obj)
    print(f"[enrich] updated cases: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(enrich_case_results())
