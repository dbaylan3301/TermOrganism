from typing import Optional, Tuple


def calculate_sl_tp(entry: float, atr: float, direction: str,
                    sl_mult: float = 1.5, tp_mult: float = 1.7) -> Tuple[float, float]:
    if direction == "LONG":
        sl = entry - (atr * sl_mult)
        tp = entry + (atr * tp_mult)
    else:
        sl = entry + (atr * sl_mult)
        tp = entry - (atr * tp_mult)
    return sl, tp


def calculate_pnl(entry: float, current: float, direction: str,
                  leverage: int = 5) -> float:
    if direction == "LONG":
        price_change = (current - entry) / entry
    else:
        price_change = (entry - current) / entry
    return price_change * leverage * 100


def check_exit(entry: float, current: float, sl: float, tp: float,
               direction: str) -> Optional[str]:
    if direction == "LONG":
        if current <= sl:
            return "SL"
        if current >= tp:
            return "TP"
    else:
        if current >= sl:
            return "SL"
        if current <= tp:
            return "TP"
    return None


def calculate_position_size(balance: float, leverage: int, risk_pct: float,
                           entry: float, sl: float) -> float:
    risk_amount = balance * (risk_pct / 100)
    price_risk = abs(entry - sl)
    if price_risk == 0:
        return 0.0
    position_value = (risk_amount / price_risk) * entry
    return position_value * leverage
