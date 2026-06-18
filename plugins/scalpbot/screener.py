import requests
import pandas as pd
from typing import List, Dict, Optional
from .config import ScalpConfig

class MarketScreener:
    def __init__(self, config: ScalpConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def get_market_overview(self) -> List[Dict]:
        """Get top coins with volume and price change data."""
        try:
            tickers = yf_download_tickers()
            return tickers
        except:
            return []

    def analyze_coin(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Analyze a single coin for trading potential."""
        if data.empty or len(data) < 50:
            return {"symbol": symbol, "score": 0, "reasons": ["yetersiz veri"]}

        closes = data["close"].values
        highs = data["high"].values
        lows = data["low"].values
        volumes = data["volume"].values

        from .indicators import calc_ema, calc_rsi, calc_atr, calc_volume_spike, check_crossover

        ema_fast = calc_ema(closes, 8)
        ema_slow = calc_ema(closes, 13)
        rsi = calc_rsi(closes, 14)
        atr = calc_atr(highs, lows, closes, 7)
        vol_spike, vol_ratio = calc_volume_spike(volumes)

        score = 0
        reasons = []

        # EMA Crossover proximity (0-30 points)
        if not any(map(lambda x: pd.isna(x), [ema_fast[-1], ema_slow[-1]])):
            diff = ema_fast[-1] - ema_slow[-1]
            diff_pct = abs(diff) / ema_slow[-1] * 100
            if diff_pct < 0.05:
                score += 30
                reasons.append("EMA crossover çok yakın")
            elif diff_pct < 0.1:
                score += 20
                reasons.append("EMA yakınsıyor")

        # RSI zone (0-25 points)
        if not pd.isna(rsi[-1]):
            if 40 <= rsi[-1] <= 60:
                score += 25
                reasons.append(f"RSI nötr bölge ({rsi[-1]:.0f})")
            elif 35 <= rsi[-1] <= 40 or 60 <= rsi[-1] <= 65:
                score += 15
                reasons.append(f"RSI ters dönüş bölgesi ({rsi[-1]:.0f})")

        # ATR volatility (0-20 points)
        if not pd.isna(atr[-1]):
            atr_pct = (atr[-1] / closes[-1]) * 100
            if atr_pct > 0.18:
                score += 20
                reasons.append(f"Yüksek volatilite ({atr_pct:.2f}%)")
            elif atr_pct > 0.12:
                score += 10
                reasons.append(f"Orta volatilite ({atr_pct:.2f}%)")

        # Volume spike (0-25 points)
        if vol_spike:
            score += 25
            reasons.append(f"Volume spike ({vol_ratio:.1f}x)")
        elif vol_ratio > 1.3:
            score += 10
            reasons.append(f"Yükselen volume ({vol_ratio:.1f}x)")

        return {
            "symbol": symbol,
            "score": score,
            "reasons": reasons,
            "rsi": float(rsi[-1]) if not pd.isna(rsi[-1]) else 50,
            "atr_pct": float((atr[-1] / closes[-1]) * 100) if not pd.isna(atr[-1]) else 0,
            "vol_ratio": float(vol_ratio),
            "ema_diff": float(abs(ema_fast[-1] - ema_slow[-1]) / ema_slow[-1] * 100) if not any(map(lambda x: pd.isna(x), [ema_fast[-1], ema_slow[-1]])) else 999,
        }

    def screen_market(self, all_symbols: List[str], kline_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Screen all coins and return ranked list."""
        results = []
        for symbol in all_symbols:
            if symbol in kline_data and not kline_data[symbol].empty:
                analysis = self.analyze_coin(symbol, kline_data[symbol])
                if analysis["score"] > 0:
                    results.append(analysis)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:self.config.top_pairs]
