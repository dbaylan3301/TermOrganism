"""Paper Trading Sistemi - Pozisyon takibi."""

import time
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from rich.console import Console

console = Console()

@dataclass
class Position:
    symbol: str
    direction: str  # LONG, SHORT
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    leverage: int
    entry_time: float
    status: str = "OPEN"  # OPEN, CLOSED_SL, CLOSED_TP, CLOSED_TIMEOUT
    exit_price: float = 0.0
    exit_time: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    exit_reason: str = ""
    
    @property
    def duration(self) -> float:
        end = self.exit_time if self.exit_time else time.time()
        return end - self.entry_time
    
    @property
    def is_profit(self) -> bool:
        return self.pnl_pct > 0

class PaperTrader:
    """Paper trading sistemi."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.max_open_positions: int = 3
        self.max_daily_trades: int = 10
        self.daily_trades: int = 0
        self.last_trade_date: str = ""
        self.trades_file = "paper_trades.json"
        self._load_trades()
    
    def _load_trades(self):
        """İşlem geçmişini yükle."""
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, 'r') as f:
                    data = json.load(f)
                self.trade_history = data.get("history", [])
                self.balance = data.get("balance", self.initial_balance)
            except Exception:
                pass
    
    def _save_trades(self):
        """İşlem geçmişini kaydet."""
        with open(self.trades_file, 'w') as f:
            json.dump({
                "balance": self.balance,
                "history": self.trade_history[-100:]  # Son 100 işlem
            }, f, indent=2)
    
    def can_open_position(self) -> bool:
        """Yeni pozisyon açabilir miyim?"""
        # Açık pozisyon kontrolü
        open_count = sum(1 for p in self.positions.values() if p.status == "OPEN")
        if open_count >= self.max_open_positions:
            return False
        
        # Günlük trade limiti
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
        
        if self.daily_trades >= self.max_daily_trades:
            return False
        
        return True
    
    def open_position(self, signal) -> Optional[Position]:
        """Yeni pozisyon aç."""
        symbol = signal.symbol
        
        # Zaten açık pozisyon var mı?
        if symbol in self.positions and self.positions[symbol].status == "OPEN":
            return None
        
        if not self.can_open_position():
            return None
        
        position = Position(
            symbol=symbol,
            direction=signal.signal,
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            tp1_price=signal.tp1_price,
            tp2_price=signal.tp2_price,
            tp3_price=signal.tp3_price,
            leverage=signal.leverage,
            entry_time=time.time()
        )
        
        self.positions[symbol] = position
        self.daily_trades += 1
        
        console.print(f"[#10B981]📈 POZİSYON AÇILDI: {symbol} {signal.signal} @ ${signal.entry_price:.4f}[/#10B981]")
        
        return position
    
    def update_positions(self, prices: Dict[str, float]) -> List[Position]:
        """Pozisyonları güncelle ve kapatılmış olanları döndür."""
        closed = []
        
        for symbol, pos in list(self.positions.items()):
            if pos.status != "OPEN":
                continue
            
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]
            
            # SL/TP kontrolü
            exit_reason = self._check_exit(pos, current_price)
            
            if exit_reason:
                self._close_position(pos, current_price, exit_reason)
                closed.append(pos)
        
        return closed
    
    def _check_exit(self, pos: Position, current_price: float) -> Optional[str]:
        """Çıkış koşullarını kontrol et."""
        if pos.direction == "LONG":
            if current_price <= pos.sl_price:
                return "STOP_LOSS"
            if current_price >= pos.tp1_price:
                return "TAKE_PROFIT_1"
            if current_price >= pos.tp2_price:
                return "TAKE_PROFIT_2"
            if current_price >= pos.tp3_price:
                return "TAKE_PROFIT_3"
        else:  # SHORT
            if current_price >= pos.sl_price:
                return "STOP_LOSS"
            if current_price <= pos.tp1_price:
                return "TAKE_PROFIT_1"
            if current_price <= pos.tp2_price:
                return "TAKE_PROFIT_2"
            if current_price <= pos.tp3_price:
                return "TAKE_PROFIT_3"
        
        # Timeout - 4 saat
        if pos.duration > 3600 * 4:
            return "TIMEOUT"
        
        return None
    
    def _close_position(self, pos: Position, exit_price: float, reason: str):
        """Pozisyonu kapat."""
        pos.exit_price = exit_price
        pos.exit_time = time.time()
        pos.exit_reason = reason
        
        # PnL hesapla
        if pos.direction == "LONG":
            price_change = (exit_price - pos.entry_price) / pos.entry_price
        else:
            price_change = (pos.entry_price - exit_price) / pos.entry_price
        
        pos.pnl_pct = price_change * pos.leverage * 100
        
        # Bakiyeyi güncelle
        trade_amount = self.balance * 0.1  # Her işlemde %10
        pos.pnl_usd = trade_amount * (pos.pnl_pct / 100)
        self.balance += pos.pnl_usd
        
        # Durum belirle
        if "STOP_LOSS" in reason:
            pos.status = "CLOSED_SL"
        elif "TAKE_PROFIT" in reason:
            pos.status = "CLOSED_TP"
        else:
            pos.status = "CLOSED_TIMEOUT"
        
        # Geçmişe ekle
        self.trade_history.append({
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.entry_price,
            "exit_price": pos.exit_price,
            "pnl_pct": pos.pnl_pct,
            "pnl_usd": pos.pnl_usd,
            "reason": reason,
            "duration": pos.duration,
            "time": datetime.now().isoformat()
        })
        
        self._save_trades()
        
        # Konsola yazdır
        emoji = "✅" if pos.is_profit else "❌"
        console.print(f"[{'#10B981' if pos.is_profit else '#EF4444'}]{emoji} POZİSYON KAPATILDI: {pos.symbol} {pos.direction}[/]")
        console.print(f"   Giriş: ${pos.entry_price:.4f} → Çıkış: ${exit_price:.4f}")
        console.print(f"   PnL: {'+' if pos.pnl_pct >= 0 else ''}{pos.pnl_pct:.2f}% (${pos.pnl_usd:.2f})")
        console.print(f"   Sebep: {reason} | Süre: {pos.duration/60:.0f}dk")
    
    def get_status(self) -> Dict:
        """Paper trading durumu."""
        open_positions = [p for p in self.positions.values() if p.status == "OPEN"]
        closed_positions = [p for p in self.positions.values() if p.status != "OPEN"]
        
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t["pnl_pct"] > 0)
        losing_trades = sum(1 for t in self.trade_history if t["pnl_pct"] <= 0)
        
        return {
            "balance": self.balance,
            "pnl_total": self.balance - self.initial_balance,
            "pnl_pct": (self.balance - self.initial_balance) / self.initial_balance * 100,
            "open_positions": len(open_positions),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": winning_trades / total_trades * 100 if total_trades > 0 else 0,
        }
    
    def format_status(self) -> str:
        """Durum özeti formatla."""
        status = self.get_status()
        
        pnl_emoji = "🟢" if status["pnl_total"] >= 0 else "🔴"
        
        msg = f"""📊 <b>PAPER TRADING DURUMU</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Bakiye:</b> ${status['balance']:,.2f}
{pnl_emoji} <b>Toplam PnL:</b> ${status['pnl_total']:+,.2f} ({status['pnl_pct']:+.1f}%)
📈 <b>Açık Pozisyon:</b> {status['open_positions']}
🎯 <b>Toplam İşlem:</b> {status['total_trades']}
✅ <b>Kazanılan:</b> {status['winning_trades']}
❌ <b>Kayıp:</b> {status['losing_trades']}
📊 <b>Win Rate:</b> %{status['win_rate']:.1f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return msg


# Global paper trader instance
import sys
_paper_trader = None

def get_paper_trader() -> PaperTrader:
    global _paper_trader
    if _paper_trader is None:
        _paper_trader = PaperTrader()
    return _paper_trader
