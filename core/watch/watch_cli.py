from __future__ import annotations

import argparse
import time

from core.watch.predictive_engine import analyze_targets, changed_targets, snapshot_targets

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    HAVE_RICH = True
except Exception:
    HAVE_RICH = False

console = Console() if HAVE_RICH else None


def _render(report: dict, *, changed: list[str] | None = None) -> None:
    if not HAVE_RICH:
        print(report)
        return

    summary = Table(show_header=False, expand=True)
    summary.add_column("k", style="grey62", width=18)
    summary.add_column("v", style="white")
    summary.add_row("repo_root", str(report.get("repo_root", "-")))
    summary.add_row("focus", str(report.get("focus", "-")))
    summary.add_row("preload_routes", ", ".join(report.get("preload_routes", [])[:4]) or "-")
    summary.add_row("files_scanned", str(report.get("files_scanned", 0)))
    summary.add_row("files_with_signals", str(report.get("files_with_signal_count", 0)))
    summary.add_row("quiet_files", str(report.get("quiet_file_count", 0)))

    top_whispers = report.get("top_whispers") or []
    if top_whispers:
        summary.add_row("top_whisper", str(top_whispers[0].get("whisper", "-")))

    if changed is not None:
        summary.add_row("changed", ", ".join(changed[:4]) or "-")

    console.print(Panel(summary, title="termorganism-watch", border_style="blue"))

    files = report.get("files_with_signals") or []
    if not files:
        quiet = report.get("quiet_files") or []
        body = "Belirgin pre-failure sinyali yok."
        if quiet:
            body += f"\nSessiz dosyalar: {', '.join(quiet[:4])}"
            if len(quiet) > 4:
                body += f" ... (+{len(quiet)-4})"
        console.print(Panel(body, title="Predictive Summary", border_style="yellow"))
        return

    for item in files:
        rows = Table(show_header=False, expand=True)
        rows.add_column("k", style="grey62", width=14)
        rows.add_column("v", style="white")
        rows.add_row("file", str(item.get("file", "-")))
        warnings = item.get("warnings") or []
        for idx, w in enumerate(warnings, start=1):
            rows.add_row(
                f"warn_{idx}",
                f"{w.get('kind')}: {w.get('message')} | p={w.get('priority', '-')} | seen={w.get('history_total', 0)} | 24h={w.get('recent_24h', 0)}"
            )
            rows.add_row(f"whisper_{idx}", str(w.get("whisper", "-")))
        console.print(Panel(rows, title="Predictive Signals", border_style="magenta"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-watch")
    parser.add_argument("paths", nargs="*", help="İzlenecek Python dosyaları")
    parser.add_argument("--modified", action="store_true", help="Sadece git status içindeki Python dosyalarını tara")
    parser.add_argument("--loop", action="store_true", help="Döngüsel watch modu")
    parser.add_argument("--interval", type=float, default=2.0, help="Loop aralığı saniye")
    args = parser.parse_args()

    if not args.loop:
        report = analyze_targets(args.paths, modified_only=args.modified)
        _render(report)
        return 0

    previous = snapshot_targets(args.paths, modified_only=args.modified)
    if HAVE_RICH:
        console.print(Panel("Watch mode aktif. Sadece dosya değişince konuşacağım.", border_style="green"))

    try:
        while True:
            current, changed = changed_targets(previous, paths=args.paths, modified_only=args.modified)
            previous = current

            if changed:
                report = analyze_targets(changed, modified_only=False)
                _render(report, changed=changed)

            time.sleep(max(0.5, args.interval))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
