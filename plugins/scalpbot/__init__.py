"""5x Scalp Bot - Crypto futures signal generator and position tracker."""

from .config import ScalpConfig
from .scanner import CoinScanner
from .tracker import PositionTracker
from .signals import SignalResult
from .display import display_signal, display_banner, console
from rich import box

__all__ = [
    "ScalpConfig",
    "CoinScanner",
    "PositionTracker",
    "SignalResult",
    "display_signal",
    "display_banner",
    "console",
]

def main():
    """Entry point for the scalp bot."""
    import argparse
    from rich.panel import Panel

    parser = argparse.ArgumentParser(
        description="5x Scalp Bot - Crypto Futures Signal Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
[bold #00D4AA]Örnekler:[/bold #00D4AA]

  [bold]Tarama:[/bold]     python -m plugins.scalpbot scan
  [bold]Pozisyon:[/bold]   python -m plugins.scalpbot track --symbol BTC --direction LONG --entry 65000 --sl 64000 --tp 67000

[bold #7C3AED]Modüller:[/bold #7C3AED]
  scan    - Piyasayı tarar, sinyal üretir
  track   - Pozisyonu canlı takip eder
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Komut")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Piyasayı tara ve sinyal üret")
    scan_parser.add_argument("--mock", action="store_true", help="Mock veri ile test et")

    # Track command
    track_parser = subparsers.add_parser("track", help="Pozisyonu canlı takip et")
    track_parser.add_argument("--symbol", required=True, help="Coin sembolü (ör: BTC)")
    track_parser.add_argument("--direction", required=True, choices=["LONG", "SHORT"], help="Pozisyon yönü")
    track_parser.add_argument("--entry", required=True, type=float, help="Giriş fiyatı")
    track_parser.add_argument("--sl", required=True, type=float, help="Stop-loss fiyatı")
    track_parser.add_argument("--tp", required=True, type=float, help="Take-profit fiyatı")

    args = parser.parse_args()

    if not args.command:
        display_banner()
        console.print()
        console.print(Panel(
            "[bold #F59E0B]⚠ Komut belirtin[/bold #F59E0B]\n\n"
            "[#6B7280]Kullanım:[/#6B7280]\n"
            "  [bold]python -m plugins.scalpbot scan[/bold]     # Tarama\n"
            "  [bold]python -m plugins.scalpbot track[/bold]   # Pozisyon takibi\n\n"
            "[#6B7280]Yardım için: python -m plugins.scalpbot --help[/#6B7280]",
            border_style="#F97316",
            box=box.ROUNDED
        ))
        return

    config = ScalpConfig()

    if args.command == "scan":
        scanner = CoinScanner(config, mock=args.mock)
        scanner.run()
    elif args.command == "track":
        tracker = PositionTracker(config)
        tracker.start_tracking(
            symbol=args.symbol,
            direction=args.direction,
            entry_price=args.entry,
            sl_price=args.sl,
            tp_price=args.tp,
            leverage=config.leverage,
        )
        tracker.run()

if __name__ == "__main__":
    main()
