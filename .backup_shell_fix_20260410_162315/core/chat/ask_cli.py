from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .context import detect_context, infer_run_command, summarize_repo
from .intent import classify_intent

try:
    from rich import box
    from rich.columns import Columns
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAVE_RICH = True
except Exception:
    HAVE_RICH = False


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


def _build_test_strategy(ctx) -> tuple[str, str, int]:
    root = Path(ctx.repo_root or ctx.cwd)

    if ctx.repo_type == "python_cli":
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
        pkg = Path(ctx.repo_root or ctx.cwd) / "package.json"
        if pkg.exists():
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


def _run_test_strategy(ctx) -> dict:
    command, reason, timeout = _build_test_strategy(ctx)
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


def _plain_render(title: str, response: dict) -> None:
    body_lines = [
        f"İstek: {response['message']}",
        f"Niyet: {response['intent']} (confidence={response['confidence']})",
        "",
        "Plan:",
    ]
    body_lines.extend(f"{i+1}. {step}" for i, step in enumerate(response.get("plan", [])))
    body_lines.append("")
    if response.get("command"):
        body_lines.append(f"Komut: {response['command']}")
    if response.get("strategy_reason"):
        body_lines.append(f"Strateji: {response['strategy_reason']}")
    if response.get("inference_reason"):
        body_lines.append(f"Gerekçe: {response['inference_reason']}")
    body_lines.append("")
    body_lines.append("Sonuç:")
    body_lines.append(str(response.get("answer", "-")))

    print(f"{title}\n{'-' * len(title)}")
    print("\n".join(body_lines))


def _render_pretty(response: dict) -> None:
    console = Console()

    ok = bool(response.get("ok"))
    intent = str(response.get("intent", "-"))
    confidence = response.get("confidence", "-")

    title = Text()
    title.append("TermOrganism Ask", style="bold magenta")
    title.append("  ")
    title.append("SUCCESS" if ok else "FAILED", style="bold green" if ok else "bold red")

    subtitle = Text()
    subtitle.append(f"intent={intent}", style="bright_cyan")
    subtitle.append("  ")
    subtitle.append(f"confidence={confidence}", style="bright_blue")

    header = Panel(
        Group(title, subtitle),
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    thinking_lines = []
    for i, step in enumerate(response.get("plan", []), start=1):
        thinking_lines.append(f"[bright_blue]{i}.[/] {step}")
    if response.get("strategy_reason"):
        thinking_lines.append("")
        thinking_lines.append(f"[rgb(210,175,120)]strategy[/]: {response['strategy_reason']}")
    if response.get("inference_reason"):
        thinking_lines.append(f"[rgb(210,175,120)]reason[/]: {response['inference_reason']}")
    if response.get("command"):
        thinking_lines.append(f"[grey70]command[/]: {response['command']}")

    thinking_panel = Panel(
        "\n".join(thinking_lines) if thinking_lines else "[grey62]no plan[/]",
        title="TermOrganism Thinking",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    ctx = response.get("context") or {}
    ctx_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
    ctx_table.add_column("k", style="grey62", width=16)
    ctx_table.add_column("v", style="white")
    ctx_table.add_row("cwd", str(ctx.get("cwd", "-")))
    ctx_table.add_row("repo_root", str(ctx.get("repo_root", "-")))
    ctx_table.add_row("branch", str(ctx.get("git_branch", "-")))
    ctx_table.add_row("repo_type", str(ctx.get("repo_type", "-")))
    ctx_table.add_row("target_hint", str(response.get("target_hint", "-")))
    context_panel = Panel(
        ctx_table,
        title="Context Snapshot",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    answer = str(response.get("answer", "-"))
    result_panel = Panel(
        answer,
        title="Result",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    repair = response.get("repair") or {}
    repair_result = repair.get("result") if isinstance(repair, dict) else None
    memory_panel = None
    if isinstance(repair_result, dict):
        syn = repair_result.get("synaptic") or {}
        upd = repair_result.get("synaptic_memory_update") or {}
        rows = []
        if syn:
            rows.extend([
                ("memory", "matched" if syn.get("matched") else "cold"),
                ("route", str(syn.get("route", "-"))),
                ("prior", str(syn.get("prior", "-"))),
                ("seen", str(syn.get("seen_total", "-"))),
            ])
        if upd:
            rows.extend([
                ("learning", str(upd.get("delta", "-"))),
                ("weight", str(upd.get("error_route_weight", "-"))),
            ])
        if rows:
            mem_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
            mem_table.add_column("k", style="grey62", width=16)
            mem_table.add_column("v", style="white")
            for k, v in rows:
                mem_table.add_row(k, v)
            memory_panel = Panel(
                mem_table,
                title="Synaptic Memory",
                border_style="rgb(110,90,180)",
                box=box.ROUNDED,
            )

    console.print(header)
    console.print()
    console.print(Columns([thinking_panel, context_panel], expand=True, equal=True))
    console.print()
    console.print(result_panel)
    if memory_panel is not None:
        console.print()
        console.print(memory_panel)


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-ask")
    parser.add_argument("message", help="Doğal dil isteği")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    intent = classify_intent(args.message)
    ctx = detect_context()

    response: dict = {
        "message": args.message,
        "intent": intent.intent,
        "confidence": intent.confidence,
        "target_hint": intent.target_hint,
        "flags": intent.flags,
        "context": {
            "cwd": ctx.cwd,
            "repo_root": ctx.repo_root,
            "git_branch": ctx.git_branch,
            "readme_path": ctx.readme_path,
            "repo_type": ctx.repo_type,
        },
    }

    if intent.intent == "repo_summary":
        summary = summarize_repo(ctx)
        response["ok"] = True
        response["plan"] = [
            "README ve üst seviye repo yapısını okuyacağım",
            "repo tipini çıkaracağım",
            "insan diliyle özet döneceğim",
        ]
        response["answer"] = summary

    elif intent.intent == "repo_status":
        res = _run("git status --short -b", cwd=ctx.cwd)
        response["ok"] = res["ok"]
        response["plan"] = [
            "git durumunu okuyacağım",
            "branch ve değişiklik özetini döneceğim",
        ]
        response["command"] = res["command"]
        response["answer"] = _human_git_status(res["stdout"]) if res["ok"] else (res["stderr"] or res["stdout"])

    elif intent.intent == "run_tests":
        response["plan"] = [
            "repo bağlamına göre kısa bir test stratejisi seçeceğim",
            "gerekirse pytest yerine python3 -m pytest fallback deneyeceğim",
            "timeout olursa temiz özet döneceğim",
        ]

        test_run = _run_test_strategy(ctx)
        res = test_run["result"]

        response["command"] = test_run["command"]
        response["strategy_reason"] = test_run["reason"]
        response["ok"] = res["ok"]

        if res.get("timed_out"):
            response["answer"] = (
                f"Seçtiğim kısa test koşusu {res.get('timeout_seconds', test_run['timeout'])} saniyede tamamlanmadı.\n\n"
                f"Strateji: {test_run['reason']}\n"
                f"Kullanılan komut: {test_run['command']}\n\n"
                f"Bu repo için test suite ağır veya takılıyor olabilir. "
                f"İstersen bir sonraki adımda sadece tek test dosyasını ya da -k filtresiyle daha dar koşu deneyebilirim.\n\n"
                f"Kısmi stdout:\n{(res['stdout'][:1200] if res['stdout'] else '-')}\n\n"
                f"Kısmi stderr:\n{(res['stderr'][:1200] if res['stderr'] else '-')}"
            )
        else:
            body = res["stdout"] if res["stdout"] else res["stderr"]
            if not body and res["ok"]:
                body = "Test komutu başarıyla tamamlandı, ek çıktı üretmedi."
            response["answer"] = (
                f"Strateji: {test_run['reason']}\n"
                f"Kullanılan komut: {test_run['command']}\n\n"
                f"{body}"
            )

    elif intent.intent == "run_project":
        command, reason = infer_run_command(ctx)
        response["plan"] = [
            "repo tipini ve giriş noktasını çıkaracağım",
            "uygun çalıştırma komutunu seçeceğim",
            "komutu çalıştırıp sonucu döneceğim",
        ]
        response["inference_reason"] = reason
        if not command:
            response["ok"] = False
            response["answer"] = reason
        else:
            res = _run(command, cwd=ctx.cwd, timeout=60)
            response["ok"] = res["ok"]
            response["command"] = command
            if res.get("timed_out"):
                response["answer"] = f"Komut timeout oldu: {command}"
            else:
                response["answer"] = res["stdout"] if res["stdout"] else res["stderr"]

    elif intent.intent in {"repair", "diagnose"}:
        response["plan"] = [
            "hedef dosya yolunu çıkaracağım",
            "termorganism repair hattına delege edeceğim",
            "sonucu insan diliyle özetleyeceğim",
        ]
        target = intent.target_hint
        if not target:
            response["ok"] = False
            response["answer"] = "Bu istek için bir dosya yolu lazım. Örnek: './bin/termorganism-ask \"Şu dosyayı düzelt /tmp/auto_import_case.py\"'"
        else:
            repair = _repair_with_termorganism(target)
            response["ok"] = bool(repair.get("ok"))
            response["repair"] = repair
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

    else:
        response["ok"] = True
        response["plan"] = [
            "niyeti sınıflandıracağım",
            "uygun komutu veya analizi seçeceğim",
            "sonucu açıklayacağım",
        ]
        response["answer"] = (
            "Şimdilik desteklenen konuşmalı görevler: "
            "repo özeti, repo durumu, test çalıştırma, proje çalıştırma, dosya repair."
        )

    if args.as_json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if response.get("ok") else 1

    if HAVE_RICH:
        _render_pretty(response)
    else:
        _plain_render("TermOrganism Ask", response)

    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
