from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, Static


class Groupish:
    def __init__(self, *renderables):
        self.renderables = renderables

    def __rich_console__(self, console, options):
        for idx, renderable in enumerate(self.renderables):
            yield renderable
            if idx != len(self.renderables) - 1:
                yield Text("")


class TermOrganismStudio(App):
    TITLE = "🧬 TermOrganism Studio"
    SUB_TITLE = "fixed bottom bar • output flows upward"

    CSS = """
    Screen {
        background: #1f2329;
        color: #d7d7d7;
    }

    #body {
        height: 1fr;
    }

    #output_wrap {
        width: 3fr;
        border: round #d68667;
        padding: 0 1;
    }

    #mind_wrap {
        width: 2fr;
        border: round #d68667;
        padding: 0 1;
    }

    #output {
        height: 1fr;
    }

    #mind {
        height: 1fr;
    }

    #command_bar {
        height: 3;
        border-top: solid #d68667;
        padding: 0 1;
        background: #181c20;
    }

    Input {
        border: none;
        background: transparent;
        color: #d7d7d7;
    }

    Footer {
        background: #181c20;
        color: #d7d7d7;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_output", "Clear"),
    ]

    cwd = reactive(str(Path.cwd()))
    last_command = reactive("")
    last_status = reactive("idle")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="output_wrap"):
                yield RichLog(id="output", wrap=True, highlight=True, markup=True)
            with Vertical(id="mind_wrap"):
                yield Static(id="mind")
        with Vertical(id="command_bar"):
            yield Input(placeholder="🧬 organism :: type a command and press Enter", id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        self.output = self.query_one("#output", RichLog)
        self.mind = self.query_one("#mind", Static)
        self.command_input = self.query_one("#command_input", Input)
        self.command_input.focus()
        self._write_banner()
        self._refresh_mind()

    def action_clear_output(self) -> None:
        self.output.clear()
        self._write_banner()
        self._refresh_mind()

    def _write_banner(self) -> None:
        self.output.write(
            Panel(
                "[bold #d68667]TermOrganism Studio[/]\n[#d7d7d7]Output stays above. Command bar stays fixed below.[/]",
                border_style="#d68667",
            )
        )

    def _git(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=self.cwd,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            return "-"
        except Exception:
            return "-"

    def _daemon_on(self) -> str:
        if Path("/tmp/termorganism.sock").exists():
            return "ON"
        try:
            proc = subprocess.run(
                ["pgrep", "-f", "python3 -m core.daemon.server"],
                capture_output=True,
                text=True,
            )
            return "ON" if proc.returncode == 0 and proc.stdout.strip() else "OFF"
        except Exception:
            return "OFF"

    def _mind_renderable(self):
        branch = self._git("symbolic-ref", "--quiet", "--short", "HEAD")
        head = self._git("rev-parse", "--short", "HEAD")
        daemon = self._daemon_on()

        tree = Tree(Text("organism.core", style="bold #d68667"))
        daemon_node = tree.add(Text("daemon", style="#d2af78"))
        daemon_node.add(Text("online" if daemon == "ON" else "offline", style="#d7d7d7"))
        daemon_node.add(Text("socket alive" if daemon == "ON" else "socket missing", style="#d7d7d7"))

        repo_node = tree.add(Text("repo", style="#d2af78"))
        repo_node.add(Text(f"cwd = {self.cwd}", style="#d7d7d7"))
        repo_node.add(Text(f"branch = {branch}", style="#d7d7d7"))
        repo_node.add(Text(f"head = {head}", style="#d7d7d7"))

        shell_node = tree.add(Text("shell", style="#d2af78"))
        shell_node.add(Text(f"last_status = {self.last_status}", style="#d7d7d7"))
        shell_node.add(Text(f"last_command = {self.last_command or '-'}", style="#d7d7d7"))

        quick = Table.grid(padding=(0, 1))
        quick.add_column(style="grey70")
        quick.add_column(style="#d7d7d7")
        quick.add_row("cwd", self.cwd)
        quick.add_row("daemon", daemon)
        quick.add_row("branch", branch)
        quick.add_row("head", head)

        return Panel(
            Groupish(tree, quick),
            title="[bold #d68667]Mind Map (Live)[/]",
            border_style="#d68667",
        )

    def _refresh_mind(self) -> None:
        self.sub_title = self.cwd
        self.mind.update(self._mind_renderable())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        self.command_input.value = ""
        if not cmd:
            return

        self.last_command = cmd
        self.output.write(Text("╭─ 🧬 organism", style="#d68667"))
        self.output.write(Text(f"╰─➤ {cmd}", style="#d7d7d7"))

        if cmd in {"exit", "quit", ":q"}:
            self.exit()
            return

        if cmd == "clear":
            self.action_clear_output()
            return

        if cmd.startswith("cd "):
            await self._handle_cd(cmd)
            return

        await self._run_shell_command(cmd)

    async def _handle_cd(self, cmd: str) -> None:
        try:
            parts = shlex.split(cmd)
        except ValueError as e:
            self.last_status = "parse-error"
            self.output.write(Text(str(e), style="#d76a6a"))
            self._refresh_mind()
            return

        target = Path(parts[1]).expanduser() if len(parts) > 1 else Path.home()
        if not target.is_absolute():
            target = (Path(self.cwd) / target).resolve()

        if target.exists() and target.is_dir():
            self.cwd = str(target)
            self.last_status = "cd-ok"
            self.output.write(Text(f"changed directory to {self.cwd}", style="#9cbf82"))
        else:
            self.last_status = "cd-failed"
            self.output.write(Text(f"cd: no such directory: {target}", style="#d76a6a"))
        self._refresh_mind()

    async def _pump_stream(self, stream, *, stderr: bool = False) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(errors="replace").rstrip("\n")
            if stderr:
                self.output.write(Text(text, style="#d76a6a"))
            else:
                self.output.write(Text.from_ansi(text))

    async def _run_shell_command(self, cmd: str) -> None:
        env = os.environ.copy()
        env["CLICOLOR_FORCE"] = "1"
        env["FORCE_COLOR"] = "1"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=self.cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.gather(
            self._pump_stream(proc.stdout, stderr=False),
            self._pump_stream(proc.stderr, stderr=True),
        )
        rc = await proc.wait()
        self.last_status = f"rc={rc}"
        self.output.write(Text(f"[done] rc={rc}", style="#9cbf82" if rc == 0 else "#d76a6a"))
        self._refresh_mind()


def main() -> None:
    TermOrganismStudio().run()
