"""Order Book analiz modülü - Destek/Direnç tespiti."""

import httpx
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class OrderBookLevel:
    price: float
    quantity: float
    total_value: float  # price * quantity

@dataclass
class OrderBookAnalysis:
    symbol: str
    # En yoğun alış noktaları
    strong_supports: List[Dict]  # price, volume, strength
    # En yoğun satış noktaları
    strong_resistances: List[Dict]  # price, volume, strength
    # Order book dengesi
    bid_ask_ratio: float  # bid / ask
    imbalance: float  # -1 (sell) ile +1 (buy) arası
    # Fiyat seviyesi
    current_price: float
    # İşlem uygunluğu
    is_tradeable: bool
    trade_direction: str  # "LONG", "SHORT", "NONE"
    confidence: float  # 0-100

class OrderBookAnalyzer:
    """Binance API ile order book analizi."""
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self):
        self.client = httpx.Client(timeout=10)
    
    def fetch_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Binance'den order book çek."""
        url = f"{self.BASE_URL}/api/v3/depth"
        params = {"symbol": f"{symbol}USDT", "limit": limit}
        
        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        
        return {"bids": [], "asks": []}
    
    def analyze_order_book(self, symbol: str, current_price: float) -> OrderBookAnalysis:
        """Order book'u analiz et."""
        data = self.fetch_order_book(symbol)
        
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        if not bids or not asks:
            return OrderBookAnalysis(
                symbol=symbol,
                strong_supports=[],
                strong_resistances=[],
                bid_ask_ratio=1.0,
                imbalance=0.0,
                current_price=current_price,
                is_tradeable=False,
                trade_direction="NONE",
                confidence=0
            )
        
        # Bid ve ask'ları parse et
        bid_levels = [OrderBookLevel(float(p), float(q), float(p) * float(q)) 
                      for p, q in bids if float(p) > 0]
        ask_levels = [OrderBookLevel(float(p), float(q), float(p) * float(q)) 
                      for p, q in asks if float(p) > 0]
        
        # Toplam hacim
        total_bid_volume = sum(b.quantity for b in bid_levels)
        total_ask_volume = sum(a.quantity for a in ask_levels)
        
        # Bid/Ask oranı
        bid_ask_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 1.0
        
        # İmbalances (-1 ile +1 arası)
        total_volume = total_bid_volume + total_ask_volume
        imbalance = (total_bid_volume - total_ask_volume) / total_volume if total_volume > 0 else 0
        
        # Destek noktaları (alış yoğunluğu olan seviyeler)
        supports = self._find_support_levels(bid_levels, current_price)
        
        # Direnç noktaları (satış yoğunluğu olan seviyeler)
        resistances = self._find_resistance_levels(ask_levels, current_price)
        
        # İşlem uygunluğu kontrolü
        is_tradeable, direction, confidence = self._evaluate_trade(
            supports, resistances, bid_ask_ratio, imbalance, current_price
        )
        
        return OrderBookAnalysis(
            symbol=symbol,
            strong_supports=supports[:3],
            strong_resistances=resistances[:3],
            bid_ask_ratio=round(bid_ask_ratio, 3),
            imbalance=round(imbalance, 3),
            current_price=current_price,
            is_tradeable=is_tradeable,
            trade_direction=direction,
            confidence=confidence
        )
    
    def _find_support_levels(self, bid_levels: List[OrderBookLevel], 
                            current_price: float) -> List[Dict]:
        """Destek seviyelerini bul (fiyat altında en yoğun alış)."""
        if not bid_levels:
            return []
        
        # Fiyatın altındaki bid'leri filtrele
        below_price = [b for b in bid_levels if b.price < current_price]
        
        if not below_price:
            return []
        
        # Fiyata göre grupla (%0.1 aralıkla)
        groups = {}
        for bid in below_price:
            # Yakın fiyat grupları
            group_key = round(bid.price / current_price * 1000) / 1000
            if group_key not in groups:
                groups[group_key] = {"price": bid.price, "total_volume": 0, "levels": 0}
            groups[group_key]["total_volume"] += bid.quantity
            groups[group_key]["levels"] += 1
            groups[group_key]["price"] = min(groups[group_key]["price"], bid.price)
        
        # Güçlü destekleri bul (yüksek hacimli)
        supports = []
        for key, group in sorted(groups.items(), key=lambda x: x[1]["total_volume"], reverse=True):
            if group["levels"] >= 3:  # En az 3 seviye
                strength = min(group["total_volume"] * 100, 100)
                supports.append({
                    "price": group["price"],
                    "volume": group["total_volume"],
                    "strength": strength,
                    "distance_pct": (current_price - group["price"]) / current_price * 100
                })
        
        return sorted(supports, key=lambda x: x["strength"], reverse=True)[:5]
    
    def _find_resistance_levels(self, ask_levels: List[OrderBookLevel],
                               current_price: float) -> List[Dict]:
        """Direnç seviyelerini bul (fiyat üstünde en yoğun satış)."""
        if not ask_levels:
            return []
        
        # Fiyatın üstündeki ask'leri filtrele
        above_price = [a for a in ask_levels if a.price > current_price]
        
        if not above_price:
            return []
        
        # Fiyata göre grupla
        groups = {}
        for ask in above_price:
            group_key = round(ask.price / current_price * 1000) / 1000
            if group_key not in groups:
                groups[group_key] = {"price": ask.price, "total_volume": 0, "levels": 0}
            groups[group_key]["total_volume"] += ask.quantity
            groups[group_key]["levels"] += 1
            groups[group_key]["price"] = max(groups[group_key]["price"], ask.price)
        
        # Güçlü dirençleri bul
        resistances = []
        for key, group in sorted(groups.items(), key=lambda x: x[1]["total_volume"], reverse=True):
            if group["levels"] >= 3:
                strength = min(group["total_volume"] * 100, 100)
                resistances.append({
                    "price": group["price"],
                    "volume": group["total_volume"],
                    "strength": strength,
                    "distance_pct": (group["price"] - current_price) / current_price * 100
                })
        
        return sorted(resistances, key=lambda x: x["strength"], reverse=True)[:5]
    
    def _evaluate_trade(self, supports: List[Dict], resistances: List[Dict],
                       bid_ask_ratio: float, imbalance: float,
                       current_price: float) -> Tuple[bool, str, float]:
        """İşlem uygunluğunu değerlendir."""
        confidence = 0
        direction = "NONE"
        
        # Destek güçlülüğü
        support_strength = sum(s["strength"] for s in supports[:2]) if supports else 0
        resistance_strength = sum(r["strength"] for r in resistances[:2]) if resistances else 0
        
        # Bid/Ask oranı analizi
        if bid_ask_ratio > 1.5:
            confidence += 25  # Alıcı baskın
        elif bid_ask_ratio > 1.2:
            confidence += 15
        elif bid_ask_ratio < 0.67:
            confidence += 25  # Satıcı baskın (short fırsatı)
        elif bid_ask_ratio < 0.83:
            confidence += 15
        
        # Imbalance analizi
        if imbalance > 0.3:
            confidence += 25  # Güçlü alıcı dengesi
            direction = "LONG"
        elif imbalance > 0.15:
            confidence += 15
            direction = "LONG"
        elif imbalance < -0.3:
            confidence += 25  # Güçlü satıcı dengesi
            direction = "SHORT"
        elif imbalance < -0.15:
            confidence += 15
            direction = "SHORT"
        
        # Destek/Direnç dengesi
        if support_strength > resistance_strength * 1.5:
            confidence += 20
            if direction != "SHORT":
                direction = "LONG"
        elif resistance_strength > support_strength * 1.5:
            confidence += 20
            if direction != "LONG":
                direction = "SHORT"
        
        # Yakın destek/direnç mesafesi
        if supports:
            closest_support = min(s["distance_pct"] for s in supports)
            if closest_support < 1.0:  # %1'den yakın destek
                confidence += 15
        
        if resistances:
            closest_resistance = min(r["distance_pct"] for r in resistances)
            if closest_resistance < 1.0:  # %1'den yakın direnç
                confidence -= 10  # Dirence yakın = riskli
        
        # Minimum eşik
        is_tradeable = confidence >= 60 and direction != "NONE"
        
        return is_tradeable, direction, min(confidence, 100)


def get_order_book_analysis(symbol: str, current_price: float) -> OrderBookAnalysis:
    """Order book analizi yap."""
    analyzer = OrderBookAnalyzer()
    return analyzer.analyze_order_book(symbol, current_price)
