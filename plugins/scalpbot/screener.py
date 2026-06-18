import numpy as np
import pandas as pd
from typing import List, Dict
from .config import ScalpConfig
from .indicators import calc_ema, calc_rsi, calc_atr, calc_volume_spike, check_crossover
from .patterns import full_analysis, multi_timeframe_score

class MarketScreener:
    def __init__(self, config: ScalpConfig):
        self.config = config

    def calculate_indicators(self, closes: np.ndarray, highs: np.ndarray,
                            lows: np.ndarray, volumes: np.ndarray) -> Dict:
        ema_fast = calc_ema(closes, 8)
        ema_slow = calc_ema(closes, 13)
        rsi = calc_rsi(closes, 14)
        atr = calc_atr(highs, lows, closes, 7)
        vol_spike, vol_ratio = calc_volume_spike(volumes)

        ema_diff = 0
        if not np.isnan(ema_fast[-1]) and not np.isnan(ema_slow[-1]) and ema_slow[-1] != 0:
            ema_diff = abs(ema_fast[-1] - ema_slow[-1]) / ema_slow[-1] * 100

        return {
            "ema_fast": float(ema_fast[-1]) if not np.isnan(ema_fast[-1]) else 0,
            "ema_slow": float(ema_slow[-1]) if not np.isnan(ema_slow[-1]) else 0,
            "ema_diff": ema_diff,
            "rsi": float(rsi[-1]) if not np.isnan(rsi[-1]) else 50,
            "atr": float(atr[-1]) if not np.isnan(atr[-1]) else 0,
            "atr_pct": float((atr[-1] / closes[-1]) * 100) if not np.isnan(atr[-1]) and closes[-1] > 0 else 0,
            "vol_spike": vol_spike,
            "vol_ratio": float(vol_ratio),
        }

    def analyze_coin(self, symbol: str, data: pd.DataFrame) -> Dict:
        if data.empty or len(data) < 50:
            return {"symbol": symbol, "score": 0, "reasons": ["yetersiz veri"]}

        closes = data["close"].values
        highs = data["high"].values
        lows = data["low"].values
        opens = data["open"].values
        volumes = data["volume"].values

        ind = self.calculate_indicators(closes, highs, lows, volumes)
        patterns = full_analysis(opens, highs, lows, closes, volumes)

        score = 0
        reasons = []

        # EMA proximity (0-30)
        if ind["ema_diff"] < 0.05:
            score += 30
            reasons.append("EMA crossover çok yakın")
        elif ind["ema_diff"] < 0.1:
            score += 20
            reasons.append("EMA yakınsıyor")

        # RSI zone (0-25)
        if 40 <= ind["rsi"] <= 60:
            score += 25
            reasons.append(f"RSI nötr ({ind['rsi']:.0f})")
        elif 35 <= ind["rsi"] <= 65:
            score += 15
            reasons.append(f"RSI yakın ({ind['rsi']:.0f})")

        # ATR volatility (0-15)
        if ind["atr_pct"] > 0.18:
            score += 15
            reasons.append(f"Volatilite yüksek ({ind['atr_pct']:.3f}%)")
        elif ind["atr_pct"] > 0.12:
            score += 8
            reasons.append(f"Volatilite orta ({ind['atr_pct']:.3f}%)")

        # Volume (0-20)
        if ind["vol_spike"]:
            score += 20
            reasons.append(f"Volume spike ({ind['vol_ratio']:.1f}x)")
        elif ind["vol_ratio"] > 1.3:
            score += 10
            reasons.append(f"Volume yükseliyor ({ind['vol_ratio']:.1f}x)")

        # Candlestick patterns (0-15)
        if patterns["pattern_count"] > 0:
            score += min(patterns["pattern_count"] * 5, 15)
            reasons.append(f"Mum formasyonu: {', '.join(patterns['patterns'][:2])}")

        # Support/Resistance (0-10)
        sr = patterns["support_resistance"]
        if sr["position"] == "NEAR_SUPPORT":
            score += 10
            reasons.append("Destek seviyesinde")
        elif sr["position"] == "NEAR_RESISTANCE":
            score += 5
            reasons.append("Direnç seviyesinde")

        # Volume profile (0-10)
        vp = patterns["volume_profile"]
        if vp["accumulation"]:
            score += 10
            reasons.append("Birikim fazında")
        elif vp["distribution"]:
            score += 5
            reasons.append("Dağıtım fazında")

        return {
            "symbol": symbol,
            "score": score,
            "reasons": reasons,
            "rsi": ind["rsi"],
            "atr_pct": ind["atr_pct"],
            "vol_ratio": ind["vol_ratio"],
            "ema_diff": ind["ema_diff"],
            "patterns": patterns["patterns"],
            "support": sr["support"],
            "resistance": sr["resistance"],
            "volume_trend": vp["trend"],
        }

    def screen_market(self, all_symbols: List[str], kline_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        results = []
        for symbol in all_symbols:
            if symbol in kline_data and not kline_data[symbol].empty:
                analysis = self.analyze_coin(symbol, kline_data[symbol])
                if analysis["score"] > 0:
                    results.append(analysis)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:self.config.top_pairs]
