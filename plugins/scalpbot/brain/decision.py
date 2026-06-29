"""Decision Engine - Nihai karar mekanizması."""

from dataclasses import dataclass
from typing import Dict, Optional
import time

@dataclass
class FinalDecision:
    signal: str  # LONG, SHORT, NONE
    confidence: float
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    leverage: int
    reasoning: str
    risk_score: float
    context_score: float
    ml_score: float
    final_score: float
    
class DecisionEngine:
    """Nihai karar motoru."""
    
    def __init__(self, config):
        self.config = config
        
        # Ağırlıklar
        self.weights = {
            "technical": 0.30,  # Teknik analiz
            "ml": 0.25,        # ML skoru
            "context": 0.25,    # Geçmiş deneyim
            "risk": 0.20        # Risk skoru
        }
        
        # Minimum eşik
        self.min_final_score = 75  # Minimum 75 skor
        self.min_confidence = 70   # Minimum güven
    
    def make_decision(self,
                     technical_signal: str,
                     technical_score: int,
                     ml_direction: str,
                     ml_confidence: float,
                     context_summary: str,
                     regime: str,
                     adx: float,
                     indicators: Dict,
                     current_price: float) -> FinalDecision:
        """Nihai karar ver."""
        
        # 1. Teknik skor (0-100)
        tech_score = min(technical_score / 1.2, 100)  # Normalize
        
        # 2. ML skoru (0-100)
        ml_score = ml_confidence if ml_direction == technical_signal else ml_confidence * 0.5
        
        # 3. Context skoru (0-100)
        context_score = self._calculate_context_score(context_summary, technical_signal)
        
        # 4. Risk skoru (0-100)
        risk_score = self._calculate_risk_score(adx, indicators, regime)
        
        # Ağırlıklı ortalama
        final_score = (
            tech_score * self.weights["technical"] +
            ml_score * self.weights["ml"] +
            context_score * self.weights["context"] +
            risk_score * self.weights["risk"]
        )
        
        # Karar ver
        signal = "NONE"
        if final_score >= self.min_final_score and technical_signal in ["LONG", "SHORT"]:
            signal = technical_signal
        
        # SL/TP hesapla
        sl_price, tp1, tp2, tp3 = self._calculate_sl_tp(
            current_price, signal, indicators
        )
        
        # Kaldıraç
        leverage = self._determine_leverage(final_score, adx)
        
        # Reasoning
        reasoning = self._build_reasoning(
            signal, final_score, tech_score, ml_score,
            context_score, risk_score, adx, regime
        )
        
        return FinalDecision(
            signal=signal,
            confidence=final_score,
            entry_price=current_price,
            sl_price=sl_price,
            tp1_price=tp1,
            tp2_price=tp2,
            tp3_price=tp3,
            leverage=leverage,
            reasoning=reasoning,
            risk_score=risk_score,
            context_score=context_score,
            ml_score=ml_score,
            final_score=final_score
        )
    
    def _calculate_context_score(self, context_summary: str, direction: str) -> float:
        """Context skorunu hesapla."""
        score = 50  # Varsayılan
        
        # Başarı oranına göre
        if "Başarı Oranı: %" in context_summary:
            try:
                win_rate = float(context_summary.split("Başarı Oranı: %")[1].split("\n")[0])
                score = min(win_rate + 20, 100)
            except (ValueError, IndexError):
                pass
        
        # Başarısız pattern uyarısı varsa düşür
        if "DİKKAT" in context_summary or "Başarısız" in context_summary:
            score *= 0.7
        
        return score
    
    def _calculate_risk_score(self, adx: float, indicators: Dict, regime: str) -> float:
        """Risk skorunu hesapla."""
        score = 50
        
        # ADX yüksekse risk düşük
        if adx > 30:
            score += 20
        elif adx > 25:
            score += 10
        
        # Volatilite çok yüksekse riskli
        atr_ratio = indicators.get("atr_ratio", 1.0)
        if atr_ratio > 2.0:
            score -= 15
        elif atr_ratio > 1.5:
            score -= 5
        
        # Regime
        if regime == "TRENDING":
            score += 10
        elif regime == "RANGING":
            score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_sl_tp(self, entry_price: float, signal: str,
                        indicators: Dict) -> tuple:
        """SL/TP hesapla."""
        atr = indicators.get("atr", entry_price * 0.01)
        
        if signal == "LONG":
            sl = entry_price - atr * 1.8
            tp1 = entry_price + atr * 1.5
            tp2 = entry_price + atr * 2.5
            tp3 = entry_price + atr * 4.0
        elif signal == "SHORT":
            sl = entry_price + atr * 1.8
            tp1 = entry_price - atr * 1.5
            tp2 = entry_price - atr * 2.5
            tp3 = entry_price - atr * 4.0
        else:
            sl = entry_price
            tp1 = entry_price
            tp2 = entry_price
            tp3 = entry_price
        
        return sl, tp1, tp2, tp3
    
    def _determine_leverage(self, score: float, adx: float) -> int:
        """Kaldıraç belirle."""
        if score >= 85 and adx > 30:
            return 7
        elif score >= 80:
            return 6
        elif score >= 75:
            return 5
        else:
            return 4
    
    def _build_reasoning(self, signal: str, final_score: float,
                        tech_score: float, ml_score: float,
                        context_score: float, risk_score: float,
                        adx: float, regime: str) -> str:
        """Reasoning metni oluştur."""
        if signal == "NONE":
            return f"Yeterli güvenilirlik yok (Skor: {final_score:.1f})"
        
        reasoning = f"""
🎯 KARAR: {signal}
📊 Final Skor: {final_score:.1f}/100

Bileşenler:
• Teknik Analiz: {tech_score:.1f}/100
• ML Tahmini: {ml_score:.1f}/100
• Geçmiş Context: {context_score:.1f}/100
• Risk Değerlendirmesi: {risk_score:.1f}/100

Piyasa Durumu:
• ADX: {adx:.1f} ({'Güçlü trend' if adx > 25 else 'Zayıf trend'})
• Regime: {regime}
"""
        
        return reasoning
