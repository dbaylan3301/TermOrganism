from __future__ import annotations

import asyncio
import os
import sys
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box
from core.ui.theme import COLORS, STYLE, PANEL_BOX

from core.commands.enhanced import get_repo_summary, get_repo_status
from core.llm.mimo_brain import _run_mimo
from core.ui.animations import (
    ThinkingPhase,
    run_with_thinking,
    phases_for_goal,
)


console = Console()


def _extract_file_path(message: str) -> str | None:
    for pat in [r'(/[\w./\-]+\.py)', r'(/[\w./\-]+\.\w+)', r'(\./[\w./\-]+)']:
        m = re.search(pat, message)
        if m:
            path = m.group(1)
            if path.startswith("~"):
                path = os.path.expanduser(path)
            return path
    return None


def _read_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def _render_response(content: str):
    console.print()
    console.print(Panel(
        content,
        title=f"[{STYLE['primary']}]TermOrganism[/{STYLE['primary']}]",
        border_style=COLORS["primary"],
        box=PANEL_BOX,
        width=min(console.width, 80),
        padding=(0, 1),
    ))
    console.print()


def _run_trading(message: str) -> str:
    """Run scalpbot analysis."""
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "plugins.scalpbot", "scan"],
            capture_output=True, text=True, timeout=120,
            cwd=str(Path(__file__).resolve().parents[2])
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        elif result.stderr:
            return f"Hata: {result.stderr[:500]}"
        else:
            return "Trading analizi tamamlandı ancak sinyal bulunamadı."
    except subprocess.TimeoutExpired:
        return "Trading analizi zaman aşımına uğradı (120s)."
    except Exception as e:
        return f"Trading hatası: {e}"


def _run_doctor() -> str:
    """Run system health check."""
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "core.cli.autofix_cli", "doctor"],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parents[2])
        )
        output = result.stdout or result.stderr
        return output[:2000] if output else "Doctor çalıştırılamadı."
    except Exception as e:
        return f"Doctor hatası: {e}"


def _run_watch() -> str:
    """Run predictive watch analysis."""
    try:
        from core.watch.predictive_engine import analyze_targets
        report = analyze_targets(["."])
        files = report.get("files_with_signals") or []
        if not files:
            return "Tahmini sinyal bulunamadı. Her şey normal görünüyor."
        lines = ["Tahmini Sinyaller:"]
        for f in files[:5]:
            lines.append(f"  • {f.get('file', '?')}: {len(f.get('warnings', []))} uyarı")
        return "\n".join(lines)
    except Exception as e:
        return f"Watch hatası: {e}"


def _show_help() -> str:
    """Show available commands."""
    return """Komutlar ve Yetenekler:

  [bold]Trading/Kripto:[/bold]
    trading, sinyal, tara, scalp    → Kripto piyasası tarama
    analiz [coin]                   → Tek coin analizi

  [bold]Kod Onarımı:[/bold]
    [dosya_yolu]                    → Dosyayı analiz et
    onar, fix, tamir                → Kod onarımı

  [bold]Sistem:[/bold]
    doctor, sağlık, kontrol         → Sistem sağlık kontrolü
    watch, izle, tahmin             → Tahmini analiz

  [bold]Proje:[/bold]
    repo özeti, proje hakkında      → Proje bilgisi
    repo durumu, git status         → Değişiklikler

  [bold]Diğer:[/bold]
    help, yardım                    → Bu ekran
    clear                           → Ekranı temizle
    exit, quit                      → Çık"""


async def repl_entry(session_id: str = "termorganism") -> int:
    os.system("clear" if os.name != "nt" else "cls")

    console.print()
    console.print(Panel(
        f"[{STYLE['primary']}]TermOrganism[/{STYLE['primary']}]\\n"
        f"[{STYLE['muted']}]Yapay zeka destekli professional code assistant[/{STYLE['muted']}]",
        border_style=COLORS["primary"],
        box=box.DOUBLE,
        width=50,
    ))
    console.print()
    console.print(f"[{STYLE['muted']}]Yaz ve devam et. Çıkmak için: exit / quit[/{STYLE['muted']}]")
    console.print()

    history: list[dict[str, str]] = []

    while True:
        try:
            message = console.input(f"[{STYLE['primary']}]chat>[/{STYLE['primary']}] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            console.print("[dim]Hoşça kal![/dim]")
            return 0

        if not message:
            continue

        if message.lower() in {"exit", "quit", ":q", "/exit", "/quit"}:
            console.print("[dim]Hoşça kal![/dim]")
            return 0

        if message.lower() == "/help":
            console.print()
            console.print("[bold]Komutlar:[/bold]")
            console.print("  /help     Bu ekranı göster")
            console.print("  /clear    Ekranı temizle")
            console.print("  /history  Son mesajları göster")
            console.print("  exit      Çık")
            console.print()
            continue

        if message.lower() == "/clear":
            os.system("clear" if os.name != "nt" else "cls")
            continue

        if message.lower() == "/history":
            if not history:
                console.print(f"[{STYLE['muted']}]Henüz mesaj yok[/{STYLE['muted']}]")
            else:
                for h in history[-8:]:
                    role = h["role"]
                    content = h["content"][:70]
                    if role == "user":
                        console.print(f"  [{STYLE['primary']}]sen:[/{STYLE['primary']}] {content}")
                    else:
                        console.print(f"  [{STYLE['accent']}]to:[/{STYLE['accent']}] {content}")
            console.print()
            continue

        history.append({"role": "user", "content": message})

        file_path = _extract_file_path(message)
        file_content = _read_file(file_path) if file_path else None
        msg_lower = message.lower()

        # Intent detection
        intent = "general"
        if file_content:
            intent = "repair"
        elif any(w in msg_lower for w in ["merhaba", "selam", "hey", "nasılsın"]):
            intent = "greeting"
        elif any(w in msg_lower for w in ["repo özeti", "proje ne", "bu ne", "proje hakkında"]):
            intent = "repo_summary"
        elif any(w in msg_lower for w in ["repo durumu", "git status", "değişiklikler"]):
            intent = "repo_status"
        elif any(w in msg_lower for w in ["trading", "sinyal", "tara", "analiz", "scalp", "kripto", "coin", "long", "short"]):
            intent = "trading"
        elif any(w in msg_lower for w in ["doctor", "sağlık", "kontrol", "test", "testler"]):
            intent = "doctor"
        elif any(w in msg_lower for w in ["watch", "izle", "tahmin", "predict"]):
            intent = "watch"
        elif any(w in msg_lower for w in ["onar", "fix", "tamir", "hata", "bug", "error"]):
            intent = "repair"
        elif any(w in msg_lower for w in ["yardım", "help", "ne yapabilirsin", "komutlar"]):
            intent = "help"

        # Direct action handlers
        if intent == "trading":
            _render_response(_run_trading(message))
            history.append({"role": "assistant", "content": "Trading analizi başlatıldı."})
            continue
        elif intent == "doctor":
            _render_response(_run_doctor())
            history.append({"role": "assistant", "content": "Sistem kontrolü tamamlandı."})
            continue
        elif intent == "watch":
            _render_response(_run_watch())
            history.append({"role": "assistant", "content": "Watch modu başlatıldı."})
            continue
        elif intent == "repo_summary":
            _render_response(get_repo_summary())
            history.append({"role": "assistant", "content": "Repo özeti gösterildi."})
            continue
        elif intent == "repo_status":
            _render_response(get_repo_status())
            history.append({"role": "assistant", "content": "Repo durumu gösterildi."})
            continue
        elif intent == "help":
            _render_response(_show_help())
            history.append({"role": "assistant", "content": "Yardım gösterildi."})
            continue

        phases = phases_for_goal(intent)

        if file_content:
            phases = [
                ThinkingPhase("Dosya okunuyor", f"{file_path} inceleniyor", ("Dosya içeriği okunuyor.",), dwell=0.4),
                ThinkingPhase("Kod analiz ediliyor", "yapı ve sorunlar tespit ediliyor", ("Sınıflar, fonksiyonlar taranıyor.", "Eksikler ve hatalar aranıyor."), dwell=0.6),
                ThinkingPhase("Teşhis hazırlanıyor", "sonuç oluşturuluyor", ("Anlaşılır rapor hazırlanıyor.",), dwell=0.5),
            ]

        async def _process():
            if file_content:
                truncated = file_content[:2000]
                prompt = f"Bu dosyayı analiz et ve Türkçe açıkla:\n{truncated}"
                return _run_mimo(prompt, timeout=40)
            else:
                return _run_mimo(message, timeout=30)

        response = await run_with_thinking(
            _process(),
            title="TermOrganism Thinking",
            phases=phases,
        )

        if not response:
            try:
                from core.chat.semantic_interpreter import interpret_message as interpret_task
                from core.chat.semantic_router import build_semantic_response
                task = interpret_task(message)
                resp = build_semantic_response(message, task, repo_root=".")
                if resp and resp.get("answer"):
                    response = resp["answer"]
                else:
                    response = "Şu an yanıt üretemiyorum. Lütfen tekrar dene."
            except Exception:
                response = "Şu an yanıt üretemiyorum."

        history.append({"role": "assistant", "content": response})

        _render_response(response)


def run_repl():
    asyncio.run(repl_entry())


if __name__ == "__main__":
    run_repl()
