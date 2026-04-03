from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .session import ChatSessionState


def _run(cmd: str, cwd: str | None = None, timeout: int = 90) -> dict:
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": p.returncode == 0,
            "rc": p.returncode,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "timed_out": False,
            "command": cmd,
            "timeout_seconds": timeout,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "rc": 124,
            "stdout": (e.stdout.decode(errors="replace").strip() if isinstance(e.stdout, bytes) else (e.stdout or "").strip()),
            "stderr": (e.stderr.decode(errors="replace").strip() if isinstance(e.stderr, bytes) else (e.stderr or "").strip()),
            "timed_out": True,
            "command": cmd,
            "timeout_seconds": timeout,
        }


def _termorganism_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repair_with_termorganism(target: str) -> dict:
    root = _termorganism_root()
    cmd = f'TERMORGANISM_USE_DAEMON=1 ./termorganism repair "{target}" --json'
    res = _run(cmd, cwd=str(root), timeout=120)
    if not res["ok"]:
        return {
            "ok": False,
            "error": res["stderr"] or res["stdout"] or f"repair rc={res['rc']}",
            "command": cmd,
            "timed_out": res.get("timed_out", False),
        }
    try:
        return {"ok": True, "result": json.loads(res["stdout"]), "command": cmd}
    except Exception:
        return {"ok": False, "error": "json parse failed", "raw": res["stdout"], "command": cmd}


def _human_git_status(raw: str) -> str:
    lines = [x for x in raw.splitlines() if x.strip()]
    if not lines:
        return "Git durumunda değişiklik görünmüyor."

    branch = "-"
    if lines[0].startswith("## "):
        branch = lines[0][3:]

    modified = 0
    added = 0
    deleted = 0
    untracked = 0
    samples: list[str] = []

    for line in lines[1:]:
        if line.startswith("??"):
            untracked += 1
        if "M " in line or line.startswith(" M") or line.startswith("M "):
            modified += 1
        if "A " in line or line.startswith("A "):
            added += 1
        if "D " in line or line.startswith("D "):
            deleted += 1
        if len(samples) < 8:
            samples.append(line)

    out = [
        f"Branch: {branch}",
        f"Modified: {modified}",
        f"Added: {added}",
        f"Deleted: {deleted}",
        f"Untracked: {untracked}",
        "",
        "İlk değişiklikler:",
    ]
    out.extend(f"- {x}" for x in samples)
    return "\n".join(out)


def _command_missing(res: dict) -> bool:
    text = f"{res.get('stderr', '')}\n{res.get('stdout', '')}".lower()
    return (
        "command not found" in text
        or "not found" in text
        or "no module named pytest" in text
        or "pytest: not found" in text
    )


def _find_single_test_target(root: Path) -> str | None:
    ignore_parts = {
        ".git", ".venv", "venv", "env", ".studio-venv",
        "site-packages", "node_modules", "dist", "build", "__pycache__"
    }

    def allowed(path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(root.resolve())
        except Exception:
            return False
        parts = set(rel.parts)
        if parts & ignore_parts:
            return False
        if any(part.startswith(".") and part not in {"tests", "test"} for part in rel.parts):
            return False
        return path.is_file()

    search_roots = []
    if (root / "tests").exists():
        search_roots.append(root / "tests")
    if (root / "test").exists():
        search_roots.append(root / "test")
    if not search_roots:
        search_roots = [root]

    patterns = ("test_*.py", "*_test.py", "**/test_*.py", "**/*_test.py")
    candidates = []
    for base in search_roots:
        for pat in patterns:
            candidates.extend(base.glob(pat))

    for c in sorted({x.resolve() for x in candidates}):
        if allowed(c):
            return str(c)
    return None


def _build_test_strategy(ctx, *, narrow: bool = False) -> tuple[str, str, int]:
    root = Path(ctx.repo_root or ctx.cwd)

    if ctx.repo_type == "python_cli":
        if narrow:
            single = _find_single_test_target(root)
            if single:
                return (
                    f'pytest -q "{single}" -x --maxfail=1',
                    "önceki test koşusu ağır olduğu için tek test dosyasına indim",
                    35,
                )
            return (
                "python3 -m pytest -q -x --maxfail=1 -k import or memory",
                "tek test dosyası bulunmadı; daha dar bir -k filtresiyle koşu seçtim",
                35,
            )

        if (root / "tests").exists():
            return (
                "pytest -q tests -x --maxfail=1",
                "tests/ klasörü bulundu; önce dar kapsamlı ve ilk kırılanı bulan koşu seçtim",
                45,
            )
        if (root / "test").exists():
            return (
                "pytest -q test -x --maxfail=1",
                "test/ klasörü bulundu; önce dar kapsamlı ve ilk kırılanı bulan koşu seçtim",
                45,
            )
        if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists() or (root / "tox.ini").exists():
            return (
                "pytest -q -x --maxfail=1",
                "pytest yapılandırması bulundu; full suite yerine ilk kırılan testi hedefleyen kısa koşu seçtim",
                60,
            )
        return (
            "python3 -m pytest -q -x --maxfail=1",
            "Python projesi algılandı; modül tabanlı kısa test koşusu seçtim",
            60,
        )

    if ctx.repo_type == "node_app":
        return (
            "npm test -- --runInBand",
            "Node projesi algılandı; sıralı test koşusu seçtim",
            60,
        )

    return (
        "pytest -q -x --maxfail=1",
        "genel test stratejisi olarak kısa pytest koşusu seçtim",
        60,
    )


def _run_test_strategy(ctx, *, narrow: bool = False) -> dict:
    command, reason, timeout = _build_test_strategy(ctx, narrow=narrow)
    res = _run(command, cwd=ctx.cwd, timeout=timeout)

    if (not res["ok"]) and _command_missing(res) and command.startswith("pytest "):
        alt = f"python3 -m {command}"
        res = _run(alt, cwd=ctx.cwd, timeout=timeout)
        command = alt
        reason += " + pytest binary bulunamadığı için python3 -m pytest fallback kullandım"

    return {
        "command": command,
        "reason": reason,
        "timeout": timeout,
        "result": res,
    }


def execute_plan(intent, plan: dict[str, Any], ctx, session: ChatSessionState) -> dict[str, Any]:
    goal = plan["goal"]
    response: dict[str, Any] = {
        "ok": True,
        "goal": goal,
        "plan": plan.get("steps", []),
        "context": {
            "cwd": ctx.cwd,
            "repo_root": ctx.repo_root,
            "git_branch": ctx.git_branch,
            "readme_path": ctx.readme_path,
            "repo_type": ctx.repo_type,
        },
        "target_hint": intent.target_hint,
    }

    if goal == "cancel_pending":
        response["answer"] = "Bekleyen eylemi iptal ettim."
        response["clear_pending"] = True
        response["session_note"] = "pending action cancelled"
        return response

    if goal == "confirm_pending":
        pending = session.pending_action or {}
        kind = pending.get("kind")
        if kind == "repair_apply":
            target = str(pending.get("target") or "")
            repair = _repair_with_termorganism(target)
            response["ok"] = bool(repair.get("ok"))
            response["repair"] = repair
            response["command"] = repair.get("command")
            response["clear_pending"] = True
            if repair.get("ok"):
                result = repair["result"]
                syn = result.get("synaptic") or {}
                response["answer"] = (
                    f"Onaylanan fix uygulandı. mode={result.get('mode')} "
                    f"strategy={result.get('strategy')} verify_ok={((result.get('verify') or {}).get('ok'))} "
                    f"memory_prior={syn.get('prior', '-')}"
                )
            else:
                response["answer"] = repair.get("error", "repair başarısız")
            return response

        if kind == "run_tests_narrow":
            test_run = _run_test_strategy(ctx, narrow=True)
            res = test_run["result"]
            response["command"] = test_run["command"]
            response["strategy_reason"] = test_run["reason"]
            response["ok"] = res["ok"]
            response["clear_pending"] = True
            response["timed_out"] = bool(res.get("timed_out"))

            if res.get("timed_out"):
                response["answer"] = (
                    f"Daha dar test koşusu bile {res.get('timeout_seconds', test_run['timeout'])} saniyede tamamlanmadı.\n\n"
                    f"Strateji: {test_run['reason']}\n"
                    f"Komut: {test_run['command']}"
                )
            else:
                body = res["stdout"] if res["stdout"] else res["stderr"]
                if not body and res["ok"]:
                    body = "Daha dar test koşusu başarıyla tamamlandı, ek çıktı üretmedi."
                response["answer"] = f"Strateji: {test_run['reason']}\nKomut: {test_run['command']}\n\n{body}"
            return response

        response["ok"] = False
        response["answer"] = "Onaylanacak bekleyen eylem bulunamadı."
        response["clear_pending"] = True
        return response

    if goal == "repo_summary":
        from .context import summarize_repo
        response["answer"] = summarize_repo(ctx)
        return response

    if goal == "repo_status":
        res = _run("git status --short -b", cwd=ctx.cwd)
        response["ok"] = res["ok"]
        response["command"] = res["command"]
        response["answer"] = _human_git_status(res["stdout"]) if res["ok"] else (res["stderr"] or res["stdout"])
        return response

    if goal in {"run_tests", "run_tests_narrow"}:
        narrow = goal == "run_tests_narrow"
        test_run = _run_test_strategy(ctx, narrow=narrow)
        res = test_run["result"]

        response["command"] = test_run["command"]
        response["strategy_reason"] = test_run["reason"]
        response["ok"] = res["ok"]
        response["timed_out"] = bool(res.get("timed_out"))
        if narrow:
            response["clear_pending"] = True

        if res.get("timed_out"):
            response["answer"] = (
                f"Seçtiğim {'daha dar ' if narrow else ''}test koşusu "
                f"{res.get('timeout_seconds', test_run['timeout'])} saniyede tamamlanmadı.\n\n"
                f"Strateji: {test_run['reason']}\n"
                f"Kullanılan komut: {test_run['command']}\n\n"
                f"Bu repo için test suite ağır veya takılıyor olabilir."
            )
            if not narrow:
                response["pending_action"] = {
                    "kind": "run_tests_narrow",
                    "risk": "low",
                    "target": ctx.cwd,
                }
                response["answer"] += "\n\nİstersen 'daha dar koş' ya da sadece 'tamam' diyerek daha dar stratejiye geçebilirim."
                response["session_note"] = "tests timed out; narrow run is pending"
            return response

        body = res["stdout"] if res["stdout"] else res["stderr"]
        if not body and res["ok"]:
            body = "Test komutu başarıyla tamamlandı, ek çıktı üretmedi."
        response["answer"] = f"Strateji: {test_run['reason']}\nKullanılan komut: {test_run['command']}\n\n{body}"
        return response

    if goal == "run_project":
        from .context import infer_run_command
        command, reason = infer_run_command(ctx)
        response["inference_reason"] = reason
        if not command:
            response["ok"] = False
            response["answer"] = reason
            return response

        res = _run(command, cwd=ctx.cwd, timeout=60)
        response["ok"] = res["ok"]
        response["command"] = command
        response["timed_out"] = bool(res.get("timed_out"))
        if res.get("timed_out"):
            response["answer"] = f"Komut timeout oldu: {command}"
        else:
            response["answer"] = res["stdout"] if res["stdout"] else res["stderr"]
        return response

    if goal in {"repair", "diagnose"}:
        target = intent.target_hint
        if not target:
            response["ok"] = False
            response["answer"] = "Bu istek için bir dosya yolu lazım. Örnek: termorganism chat \"Şu dosyayı düzelt /tmp/auto_import_case.py\""
            return response

        if plan.get("preview_only"):
            response["preview_only"] = True
            response["pending_action"] = {
                "kind": "repair_apply",
                "target": target,
                "risk": "medium",
            }
            response["answer"] = (
                f"Bunu güvenli repair isteği olarak yorumladım.\n\n"
                f"Hedef: {target}\n"
                f"Repo tipi: {ctx.repo_type}\n"
                f"Bekleyen işlem: termorganism repair {target}\n\n"
                f"Uygulamamı istersen sadece 'tamam uygula' ya da kısaca 'tamam' de. "
                f"İptal etmek için 'iptal' yaz."
            )
            response["session_note"] = f"repair preview pending for {target}"
            return response

        repair = _repair_with_termorganism(target)
        response["ok"] = bool(repair.get("ok"))
        response["repair"] = repair
        response["command"] = repair.get("command")
        if repair.get("ok"):
            result = repair["result"]
            syn = result.get("synaptic") or {}
            response["answer"] = (
                f"Fix uygulandı. mode={result.get('mode')} strategy={result.get('strategy')} "
                f"verify_ok={((result.get('verify') or {}).get('ok'))} "
                f"memory_prior={syn.get('prior', '-')}"
            )
        else:
            response["answer"] = repair.get("error", "repair başarısız")
        return response

    response["ok"] = True
    response["answer"] = (
        "Şimdilik desteklenen konuşmalı görevler: repo özeti, repo durumu, test çalıştırma, "
        "proje çalıştırma, dosya repair ve follow-up onay akışları."
    )
    return response
