from typing import Tuple, Dict, Optional
import numpy as np

class RiskManager:
    """Gelişmiş Risk ve Pozisyon Yönetimi"""
    
    def __init__(self, 
                 initial_balance: float = 1000.0,
                 max_risk_per_trade: float = 1.0,      # %1
                 max_daily_risk: float = 3.0,          # %3
                 leverage: int = 5,
                 default_sl_mult: float = 1.5,
                 default_tp_mult: float = 2.0):
        
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.leverage = leverage
        self.default_sl_mult = default_sl_mult
        self.default_tp_mult = default_tp_mult
        self.daily_loss = 0.0
        self.trades_today = 0

    def calculate_sl_tp(self, entry: float, atr: float, direction: str,
                       sl_mult: Optional[float] = None,
                       tp_mult: Optional[float] = None) -> Tuple[float, float]:
        """ATR bazlı Stop Loss ve Take Profit"""
        sl_mult = sl_mult or self.default_sl_mult
        tp_mult = tp_mult or self.default_tp_mult
        
        if direction.upper() == "LONG":
            sl = entry - (atr * sl_mult)
            tp = entry + (atr * tp_mult)
        else:
            sl = entry + (atr * sl_mult)
            tp = entry - (atr * tp_mult)
        
        return round(sl, 6), round(tp, 6)

    def calculate_position_size(self, entry: float, sl: float, 
                              balance: Optional[float] = None) -> float:
        """Risk bazlı pozisyon büyüklüğü"""
        balance = balance or self.current_balance
        risk_amount = balance * (self.max_risk_per_trade / 100)
        price_risk = abs(entry - sl)
        
        if price_risk == 0:
            return 0.0
        
        # Base position value
        position_value = (risk_amount / price_risk) * entry
        # Leverage ile çarp
        return position_value * self.leverage

    def calculate_pnl(self, entry: float, current: float, direction: str,
                     leverage: Optional[int] = None, fees: float = 0.04) -> Dict:
        """Detaylı PNL hesaplaması"""
        leverage = leverage or self.leverage
        
        if direction.upper() == "LONG":
            price_change = (current - entry) / entry
        else:
            price_change = (entry - current) / entry
        
        gross_pnl = price_change * leverage * 100
        net_pnl = gross_pnl - fees
        
        return {
            "gross_pnl_pct": round(gross_pnl, 4),
            "net_pnl_pct": round(net_pnl, 4),
            "direction": direction.upper()
        }

    def check_exit(self, entry: float, current: float, sl: float, tp: float,
                   direction: str, trailing_stop: Optional[float] = None) -> Optional[str]:
        """Exit kontrolü + Trailing Stop"""
        direction = direction.upper()
        
        if direction == "LONG":
            if current <= sl:
                return "STOP_LOSS"
            if current >= tp:
                return "TAKE_PROFIT"
            # Trailing Stop
            if trailing_stop and current < trailing_stop:
                return "TRAILING_STOP"
        else:  # SHORT
            if current >= sl:
                return "STOP_LOSS"
            if current <= tp:
                return "TAKE_PROFIT"
            if trailing_stop and current > trailing_stop:
                return "TRAILING_STOP"
        
        return None

    def update_trailing_stop(self, current: float, direction: str,
                            atr: float, multiplier: float = 2.0) -> float:
        """Dinamik Trailing Stop"""
        if direction.upper() == "LONG":
            return current - (atr * multiplier)
        else:
            return current + (atr * multiplier)

    def can_trade(self) -> Tuple[bool, str]:
        """Günlük risk limit kontrolü"""
        if self.daily_loss >= self.max_daily_risk:
            return False, "DAILY_RISK_LIMIT_EXCEEDED"
        if self.trades_today >= 15:  # max trade sınırı
            return False, "MAX_TRADES_PER_DAY_REACHED"
        return True, "OK"

    def update_after_trade(self, pnl_pct: float):
        """Trade sonrası bilanço güncelle"""
        self.current_balance *= (1 + pnl_pct / 100)
        self.daily_loss = max(0, self.daily_loss - pnl_pct) if pnl_pct < 0 else self.daily_loss
        self.trades_today += 1

    def reset_daily(self):
        """Yeni gün başlangıcı"""
        self.daily_loss = 0.0
        self.trades_today = 0

    def get_risk_summary(self) -> Dict:
        """Risk durumu özeti"""
        return {
            "current_balance": round(self.current_balance, 2),
            "daily_loss_pct": round(self.daily_loss, 2),
            "trades_today": self.trades_today,
            "balance_change_pct": round((self.current_balance - self.initial_balance) / 
                                      self.initial_balance * 100, 2)
        }


# Basit fonksiyonlar (eski tarz sevenler için)
def calculate_sl_tp(entry: float, atr: float, direction: str,
                   sl_mult: float = 1.5, tp_mult: float = 2.0) -> Tuple[float, float]:
    rm = RiskManager()
    return rm.calculate_sl_tp(entry, atr, direction, sl_mult, tp_mult)


def calculate_position_size(balance: float, entry: float, sl: float,
                           risk_pct: float = 1.0) -> float:
    rm = RiskManager(max_risk_per_trade=risk_pct)
    return rm.calculate_position_size(entry, sl, balance)


def calculate_pnl(entry: float, current: float, direction: str,
                  leverage: int = 5, fees: float = 0.04) -> float:
    rm = RiskManager(leverage=leverage)
    result = rm.calculate_pnl(entry, current, direction, leverage, fees)
    return result["net_pnl_pct"]


def check_exit(entry: float, current: float, sl: float, tp: float,
               direction: str) -> Optional[str]:
    rm = RiskManager()
    return rm.check_exit(entry, current, sl, tp, direction)
