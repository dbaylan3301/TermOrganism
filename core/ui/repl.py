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


async def repl_entry(session_id: str = "termorganism") -> int:
    os.system("clear" if os.name != "nt" else "cls")

    console.print()
    console.print(Panel(
        f"[{STYLE['primary']}]TermOrganism[/{STYLE['primary']}]\\n"
        f"[{STYLE['muted']}]Yapay zeka destekli professional code assistant[/{STYLE['muted']}]\\n"
        f"[{STYLE['muted']}]Powered by MiMo · v0.2.0[/{STYLE['muted']}]",
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

        intent = "general"
        if file_content:
            intent = "repair"
        elif any(w in message.lower() for w in ["merhaba", "selam", "hey"]):
            intent = "greeting"
        elif any(w in message.lower() for w in ["repo özeti", "proje ne", "bu ne"]):
            intent = "repo_summary"
        elif any(w in message.lower() for w in ["repo durumu", "git status"]):
            intent = "repo_status"

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
