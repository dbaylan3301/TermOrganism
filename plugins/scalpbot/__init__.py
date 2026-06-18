"""5x Scalp Bot - Crypto futures signal generator and position tracker."""

from .config import ScalpConfig
from .scanner import CoinScanner
from .tracker import PositionTracker
from .signals import SignalResult
from .display import display_signal, console

__all__ = [
    "ScalpConfig",
    "CoinScanner",
    "PositionTracker",
    "SignalResult",
    "display_signal",
    "console",
]

def main():
    """Entry point for the scalp bot."""
    import argparse
    parser = argparse.ArgumentParser(description="5x Scalp Bot")
    parser.add_argument("command", choices=["scan", "track"],
                       help="scan: tara sinyaller, track: pozisyon takip et")
    parser.add_argument("--symbol", help="Pozisyon sembolü (track modu)")
    parser.add_argument("--direction", choices=["LONG", "SHORT"],
                       help="Pozisyon yönü (track modu)")
    parser.add_argument("--entry", type=float, help="Giriş fiyatı (track modu)")
    parser.add_argument("--sl", type=float, help="Stop-loss fiyatı (track modu)")
    parser.add_argument("--tp", type=float, help="Take-profit fiyatı (track modu)")

    args = parser.parse_args()
    config = ScalpConfig()

    if args.command == "scan":
        scanner = CoinScanner(config)
        scanner.run()
    elif args.command == "track":
        if not all([args.symbol, args.direction, args.entry, args.sl, args.tp]):
            parser.error("track modu için --symbol, --direction, --entry, --sl, --tp gerekli")
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
