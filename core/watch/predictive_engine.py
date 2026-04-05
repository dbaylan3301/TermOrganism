from __future__ import annotations

import ast
import importlib.util
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

from core.chat.context import detect_context
from core.context.intent_context import infer_intent_context


def _repo_root(cwd: str) -> Path:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if p.returncode == 0 and p.stdout.strip():
            return Path(p.stdout.strip()).resolve()
    except Exception:
        pass
    return Path(cwd).resolve()


def _predictive_db() -> Path:
    base = Path.home() / ".termorganism"
    base.mkdir(parents=True, exist_ok=True)
    return base / "predictive.db"


def _init_db() -> None:
    db = sqlite3.connect(_predictive_db())
    db.execute(
        """
        create table if not exists predictive_observations (
            id integer primary key autoincrement,
            ts real not null,
            file_path text not null,
            kind text not null,
            message text not null,
            confidence real not null,
            focus text
        )
        """
    )
    db.execute(
        """
        create table if not exists predictive_repair_bridge (
            id integer primary key autoincrement,
            ts real not null,
            file_path text,
            focus text,
            signature text,
            route text,
            success integer not null,
            warn_kind text,
            warn_message text,
            warn_priority real,
            synaptic_route text,
            synaptic_prior real,
            memory_matched integer not null default 0
        )
        """
    )
    db.commit()
    db.close()


def _record(file_path: str, kind: str, message: str, confidence: float, focus: str) -> None:
    db = sqlite3.connect(_predictive_db())
    db.execute(
        "insert into predictive_observations(ts, file_path, kind, message, confidence, focus) values (?, ?, ?, ?, ?, ?)",
        (time.time(), file_path, kind, message, float(confidence), focus),
    )
    db.commit()
    db.close()


def _warning_stats(file_path: str, kind: str, focus: str) -> dict[str, float]:
    now = time.time()
    day_1 = now - 86400
    day_7 = now - (86400 * 7)

    db = sqlite3.connect(_predictive_db())
    try:
        total = db.execute(
            "select count(*) from predictive_observations where file_path = ? and kind = ? and focus = ?",
            (file_path, kind, focus),
        ).fetchone()[0]

        recent_24h = db.execute(
            "select count(*) from predictive_observations where file_path = ? and kind = ? and focus = ? and ts >= ?",
            (file_path, kind, focus, day_1),
        ).fetchone()[0]

        recent_7d = db.execute(
            "select count(*) from predictive_observations where file_path = ? and kind = ? and focus = ? and ts >= ?",
            (file_path, kind, focus, day_7),
        ).fetchone()[0]

        last_seen = db.execute(
            "select max(ts) from predictive_observations where file_path = ? and kind = ? and focus = ?",
            (file_path, kind, focus),
        ).fetchone()[0]
    finally:
        db.close()

    return {
        "total": float(total or 0),
        "recent_24h": float(recent_24h or 0),
        "recent_7d": float(recent_7d or 0),
        "last_seen": float(last_seen or 0),
    }


def _priority_from_history(base_confidence: float, stats: dict[str, float]) -> float:
    total = stats.get("total", 0.0)
    recent_24h = stats.get("recent_24h", 0.0)
    recent_7d = stats.get("recent_7d", 0.0)

    score = (
        (base_confidence * 0.72)
        + min(0.16, total * 0.025)
        + min(0.08, recent_24h * 0.03)
        + min(0.06, recent_7d * 0.015)
    )
    return round(min(0.99, score), 4)


def _whisper_level(priority: float) -> str:
    if priority >= 0.90:
        return "critical whisper"
    if priority >= 0.80:
        return "strong whisper"
    if priority >= 0.68:
        return "soft whisper"
    return "faint whisper"


def _enrich_warnings(file_path: str, warnings: list[dict[str, Any]], focus: str) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for item in warnings:
        stats = _warning_stats(file_path, str(item["kind"]), focus)
        priority = _priority_from_history(float(item["confidence"]), stats)
        whisper = f"{_whisper_level(priority)} — {item['message']}"

        row = dict(item)
        row["priority"] = priority
        row["history_total"] = int(stats["total"])
        row["recent_24h"] = int(stats["recent_24h"])
        row["recent_7d"] = int(stats["recent_7d"])
        row["whisper"] = whisper
        enriched.append(row)

    enriched.sort(key=lambda x: (float(x.get("priority", 0.0)), float(x.get("confidence", 0.0))), reverse=True)
    return enriched


def _modified_python_files(repo_root: Path) -> list[Path]:
    try:
        p = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if p.returncode != 0:
            return []
        out = []
        for line in p.stdout.splitlines():
            if len(line) < 4:
                continue
            rel = line[3:].strip()
            path = (repo_root / rel).resolve()
            if path.suffix == ".py" and path.exists():
                out.append(path)
        return out[:20]
    except Exception:
        return []


def snapshot_targets(paths: list[str] | None = None, *, cwd: str | None = None, modified_only: bool = False) -> dict[str, float]:
    base = Path(cwd or Path.cwd()).resolve()
    repo_root = _repo_root(str(base))

    if paths:
        chosen = [Path(p).expanduser().resolve() for p in paths]
    else:
        chosen = _modified_python_files(repo_root) if modified_only or not paths else []

    snap: dict[str, float] = {}
    for p in chosen:
        if p.exists() and p.suffix == ".py":
            try:
                snap[str(p)] = p.stat().st_mtime
            except Exception:
                continue
    return snap


def changed_targets(previous: dict[str, float], *, paths: list[str] | None = None, cwd: str | None = None, modified_only: bool = False) -> tuple[dict[str, float], list[str]]:
    current = snapshot_targets(paths, cwd=cwd, modified_only=modified_only)
    changed: list[str] = []

    for file_path, mtime in current.items():
        if file_path not in previous or previous[file_path] != mtime:
            changed.append(file_path)

    removed = [fp for fp in previous if fp not in current]
    for fp in removed:
        changed.append(fp)

    return current, sorted(set(changed))


def _is_local_module(top: str, repo_root: Path) -> bool:
    return (
        (repo_root / f"{top}.py").exists()
        or (repo_root / top / "__init__.py").exists()
        or (repo_root / top).is_dir()
    )


def _analyze_imports(tree: ast.AST, repo_root: Path) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        mod = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod and importlib.util.find_spec(mod) is None and not _is_local_module(mod, repo_root):
                    warnings.append({
                        "kind": "import-risk",
                        "message": f"`{mod}` modülü bu ortamda veya repo kökünde bulunamadı",
                        "confidence": 0.72,
                    })
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                mod = node.module.split(".")[0]
                if mod and importlib.util.find_spec(mod) is None and not _is_local_module(mod, repo_root):
                    warnings.append({
                        "kind": "import-risk",
                        "message": f"`{mod}` import zinciri kırılabilir görünüyor",
                        "confidence": 0.74,
                    })

    return warnings


def _analyze_open_calls(tree: ast.AST, file_path: Path, repo_root: Path) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                raw = node.args[0].value
                if raw.startswith(("http://", "https://")):
                    continue
                candidate_a = (file_path.parent / raw).resolve()
                candidate_b = (repo_root / raw).resolve()
                if not candidate_a.exists() and not candidate_b.exists():
                    warnings.append({
                        "kind": "path-risk",
                        "message": f"`open({raw!r})` hedefi dosya kaydedilmeden sonra kırılabilir",
                        "confidence": 0.68,
                    })
    return warnings


def analyze_file(file_path: str, *, cwd: str | None = None) -> dict[str, Any]:
    _init_db()

    path = Path(file_path).expanduser().resolve()
    repo_root = _repo_root(cwd or str(path.parent))
    ctx = detect_context(str(repo_root))
    intent_ctx = infer_intent_context(ctx)
    focus = str(intent_ctx.get("focus", "general_runtime"))

    result: dict[str, Any] = {
        "file": str(path),
        "repo_root": str(repo_root),
        "focus": focus,
        "warnings": [],
    }

    if not path.exists():
        item = {
            "kind": "missing-file",
            "message": "dosya bulunamadı",
            "confidence": 0.99,
        }
        result["warnings"].append(item)
        _record(str(path), item["kind"], item["message"], item["confidence"], focus)
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        item = {
            "kind": "syntax-risk",
            "message": f"syntax error: line {e.lineno}, offset {e.offset}",
            "confidence": 0.98,
        }
        result["warnings"].append(item)
        _record(str(path), item["kind"], item["message"], item["confidence"], focus)
        return result

    warnings = []
    warnings.extend(_analyze_imports(tree, repo_root))
    warnings.extend(_analyze_open_calls(tree, path, repo_root))

    if focus == "authentication":
        warnings.append({
            "kind": "intent-context",
            "message": "authentication odaklı bağlam algılandı; import ve token akışları dikkat istiyor",
            "confidence": 0.58,
        })

    dedup: set[tuple[str, str]] = set()
    deduped = []
    for item in warnings:
        key = (item["kind"], item["message"])
        if key in dedup:
            continue
        dedup.add(key)
        deduped.append(item)

    final_warnings = _enrich_warnings(str(path), deduped, focus)

    for item in final_warnings:
        _record(str(path), item["kind"], item["message"], item["confidence"], focus)

    result["warnings"] = final_warnings
    if final_warnings:
        result["top_whisper"] = final_warnings[0]["whisper"]
    return result


def predictive_whispers_for_target(
    *,
    target_path: str | None = None,
    cwd: str | None = None,
    focus: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    _init_db()

    path = Path(target_path).expanduser().resolve() if target_path else None
    repo_root = _repo_root(cwd or str(path.parent if path else Path.cwd()))
    ctx = detect_context(str(repo_root))
    inferred_focus = focus or str(infer_intent_context(ctx).get("focus", "general_runtime"))

    db = sqlite3.connect(_predictive_db())
    try:
        if path and path.exists():
            rows = db.execute(
                """
                select file_path, kind, message, max(confidence) as conf, count(*) as total, max(ts) as last_seen
                from predictive_observations
                where file_path = ? and focus = ?
                group by file_path, kind, message
                order by total desc, conf desc, last_seen desc
                limit ?
                """,
                (str(path), inferred_focus, limit),
            ).fetchall()
        else:
            rows = db.execute(
                """
                select file_path, kind, message, max(confidence) as conf, count(*) as total, max(ts) as last_seen
                from predictive_observations
                where focus = ?
                group by file_path, kind, message
                order by total desc, conf desc, last_seen desc
                limit ?
                """,
                (inferred_focus, limit),
            ).fetchall()
    finally:
        db.close()

    out = []
    for file_path, kind, message, conf, total, last_seen in rows:
        priority = round(min(0.99, float(conf or 0.0) * 0.75 + min(0.24, int(total or 0) * 0.04)), 4)
        out.append({
            "file": str(file_path),
            "kind": str(kind),
            "message": str(message),
            "confidence": float(conf or 0.0),
            "total": int(total or 0),
            "last_seen": float(last_seen or 0.0),
            "priority": priority,
            "whisper": f"{_whisper_level(priority)} — {message}",
        })
    return out


def record_predictive_repair_bridge(
    *,
    target_path: str | None,
    cwd: str | None = None,
    focus: str | None = None,
    signature: str | None = None,
    route: str | None = None,
    success: bool,
    predictive_whispers: list[dict[str, Any]] | None = None,
    synaptic_route: str | None = None,
    synaptic_prior: float | None = None,
    memory_matched: bool = False,
) -> None:
    _init_db()

    path = str(Path(target_path).expanduser().resolve()) if target_path else None
    repo_root = _repo_root(cwd or str(Path.cwd()))
    ctx = detect_context(str(repo_root))
    inferred_focus = focus or str(infer_intent_context(ctx).get("focus", "general_runtime"))

    rows = predictive_whispers[:6] if predictive_whispers else []
    if not rows:
        rows = [{
            "kind": "no-whisper",
            "message": "repair öncesi belirgin predictive whisper yok",
            "priority": 0.0,
        }]

    db = sqlite3.connect(_predictive_db())
    try:
        for item in rows:
            db.execute(
                """
                insert into predictive_repair_bridge(
                    ts, file_path, focus, signature, route, success,
                    warn_kind, warn_message, warn_priority,
                    synaptic_route, synaptic_prior, memory_matched
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    path,
                    inferred_focus,
                    str(signature or "-"),
                    str(route or "-"),
                    1 if success else 0,
                    str(item.get("kind", "-")),
                    str(item.get("message", "-")),
                    float(item.get("priority", 0.0) or 0.0),
                    str(synaptic_route or "-"),
                    float(synaptic_prior or 0.0),
                    1 if memory_matched else 0,
                ),
            )
        db.commit()
    finally:
        db.close()


def predictive_bridge_summary(
    *,
    target_path: str | None = None,
    cwd: str | None = None,
    focus: str | None = None,
    signature: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    _init_db()

    path = str(Path(target_path).expanduser().resolve()) if target_path else None
    repo_root = _repo_root(cwd or str(Path.cwd()))
    ctx = detect_context(str(repo_root))
    inferred_focus = focus or str(infer_intent_context(ctx).get("focus", "general_runtime"))

    query_variants: list[tuple[str, list[Any]]] = []

    # 1) exact path + focus + signature
    if path and signature:
        query_variants.append((
            """
            select
                warn_kind,
                warn_message,
                count(*) as total,
                avg(success) as success_rate,
                avg(warn_priority) as avg_priority,
                max(route) as route_hint,
                max(synaptic_route) as synaptic_route_hint,
                avg(synaptic_prior) as avg_syn_prior,
                avg(memory_matched) as memory_match_rate
            from predictive_repair_bridge
            where focus = ? and file_path = ? and signature = ?
            group by warn_kind, warn_message
            order by total desc, avg_priority desc, avg(success) desc
            limit ?
            """,
            [inferred_focus, path, signature, limit],
        ))

    # 2) focus + signature
    if signature:
        query_variants.append((
            """
            select
                warn_kind,
                warn_message,
                count(*) as total,
                avg(success) as success_rate,
                avg(warn_priority) as avg_priority,
                max(route) as route_hint,
                max(synaptic_route) as synaptic_route_hint,
                avg(synaptic_prior) as avg_syn_prior,
                avg(memory_matched) as memory_match_rate
            from predictive_repair_bridge
            where focus = ? and signature = ?
            group by warn_kind, warn_message
            order by total desc, avg_priority desc, avg(success) desc
            limit ?
            """,
            [inferred_focus, signature, limit],
        ))

    # 3) focus + path
    if path:
        query_variants.append((
            """
            select
                warn_kind,
                warn_message,
                count(*) as total,
                avg(success) as success_rate,
                avg(warn_priority) as avg_priority,
                max(route) as route_hint,
                max(synaptic_route) as synaptic_route_hint,
                avg(synaptic_prior) as avg_syn_prior,
                avg(memory_matched) as memory_match_rate
            from predictive_repair_bridge
            where focus = ? and file_path = ?
            group by warn_kind, warn_message
            order by total desc, avg_priority desc, avg(success) desc
            limit ?
            """,
            [inferred_focus, path, limit],
        ))

    # 4) focus only
    query_variants.append((
        """
        select
            warn_kind,
            warn_message,
            count(*) as total,
            avg(success) as success_rate,
            avg(warn_priority) as avg_priority,
            max(route) as route_hint,
            max(synaptic_route) as synaptic_route_hint,
            avg(synaptic_prior) as avg_syn_prior,
            avg(memory_matched) as memory_match_rate
        from predictive_repair_bridge
        where focus = ?
        group by warn_kind, warn_message
        order by total desc, avg_priority desc, avg(success) desc
        limit ?
        """,
        [inferred_focus, limit],
    ))

    rows = []
    db = sqlite3.connect(_predictive_db())
    try:
        for sql, params in query_variants:
            rows = db.execute(sql, params).fetchall()
            if rows:
                break
    finally:
        db.close()

    out = []
    for warn_kind, warn_message, total, success_rate, avg_priority, route_hint, syn_route_hint, avg_syn_prior, memory_match_rate in rows:
        out.append({
            "kind": str(warn_kind or "-"),
            "message": str(warn_message or "-"),
            "total": int(total or 0),
            "success_rate": round(float(success_rate or 0.0), 4),
            "avg_priority": round(float(avg_priority or 0.0), 4),
            "route_hint": str(route_hint or "-"),
            "synaptic_route_hint": str(syn_route_hint or "-"),
            "avg_syn_prior": round(float(avg_syn_prior or 0.0), 4),
            "memory_match_rate": round(float(memory_match_rate or 0.0), 4),
        })
    return out

def analyze_targets(paths: list[str] | None = None, *, cwd: str | None = None, modified_only: bool = False) -> dict[str, Any]:
    base = Path(cwd or Path.cwd()).resolve()
    repo_root = _repo_root(str(base))
    ctx = detect_context(str(repo_root))
    intent_ctx = infer_intent_context(ctx)

    chosen: list[Path] = []
    if paths:
        chosen = [Path(p).expanduser().resolve() for p in paths]
    elif modified_only:
        chosen = _modified_python_files(repo_root)
    else:
        chosen = _modified_python_files(repo_root)

    results = [analyze_file(str(p), cwd=str(repo_root)) for p in chosen if p.suffix == ".py"]

    top_whispers = []
    for item in results:
        for w in (item.get("warnings") or [])[:2]:
            top_whispers.append({
                "file": str(item.get("file", "-")),
                "kind": str(w.get("kind", "-")),
                "priority": float(w.get("priority", 0.0)),
                "message": str(w.get("message", "-")),
                "whisper": str(w.get("whisper", "-")),
            })

    top_whispers.sort(key=lambda x: x["priority"], reverse=True)

    files_with_signals = [item for item in results if item.get("warnings")]
    quiet_files = [str(item.get("file", "-")) for item in results if not item.get("warnings")]

    return {
        "repo_root": str(repo_root),
        "focus": intent_ctx.get("focus", "general_runtime"),
        "preload_routes": intent_ctx.get("preload_routes", []),
        "files": results,
        "files_with_signals": files_with_signals,
        "quiet_files": quiet_files,
        "files_scanned": len(results),
        "files_with_signal_count": len(files_with_signals),
        "quiet_file_count": len(quiet_files),
        "top_whispers": top_whispers[:6],
    }
