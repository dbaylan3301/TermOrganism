"""Self-Adapting Fine-Tuning - Piyasa durumuna göre otomatik ayarlama"""
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from .config import ScalpConfig

@dataclass
class SignalHistory:
    symbol: str
    signal: str
    entry_price: float
    exit_price: float = 0.0
    result: str = "PENDING"  # WIN, LOSS, PENDING
    confidence: float = 0.0
    regime: str = "NEUTRAL"
    timestamp: float = 0.0

class AdaptiveManager:
    """Piyasa durumuna göre otomatik ayarlama yapan yönetici"""
    
    def __init__(self, config: ScalpConfig, history_file: str = "signal_history.json"):
        self.config = config
        self.history_file = history_file
        self.history: List[SignalHistory] = self._load_history()
        self.adjustments: Dict[str, float] = {}
        
    def _load_history(self) -> List[SignalHistory]:
        """Geçmiş sinyalleri yükle"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                return [SignalHistory(**item) for item in data]
            except:
                return []
        return []
    
    def _save_history(self) -> None:
        """Geçmiş sinyalleri kaydet"""
        data = []
        for h in self.history[-100:]:  # Son 100 sinyali tut
            data.append({
                "symbol": h.symbol,
                "signal": h.signal,
                "entry_price": h.entry_price,
                "exit_price": h.exit_price,
                "result": h.result,
                "confidence": h.confidence,
                "regime": h.regime,
                "timestamp": h.timestamp
            })
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_signal(self, signal_data: Dict) -> None:
        """Yeni sinyal kaydet"""
        history_item = SignalHistory(
            symbol=signal_data.get("symbol", ""),
            signal=signal_data.get("signal", ""),
            entry_price=signal_data.get("entry_price", 0.0),
            confidence=signal_data.get("confidence", 0.0),
            regime=signal_data.get("regime", "NEUTRAL"),
            timestamp=datetime.now().timestamp()
        )
        self.history.append(history_item)
        self._save_history()
    
    def record_outcome(self, symbol: str, exit_price: float, result: str) -> None:
        """Sinyal sonucunu kaydet"""
        for h in reversed(self.history):
            if h.symbol == symbol and h.result == "PENDING":
                h.exit_price = exit_price
                h.result = result
                self._save_history()
                break
    
    def get_win_rate(self, regime: str = None, lookback: int = None) -> float:
        """Kazanma oranını hesapla"""
        lookback = lookback or self.config.adaptive_lookback_signals
        
        relevant = [h for h in self.history[-lookback:] if h.result != "PENDING"]
        if regime:
            relevant = [h for h in relevant if h.regime == regime]
        
        if not relevant:
            return 0.5
        
        wins = sum(1 for h in relevant if h.result == "WIN")
        return wins / len(relevant)
    
    def get_regime_stats(self) -> Dict[str, Dict]:
        """Rejim bazlı istatistikler"""
        stats = {}
        for h in self.history:
            if h.result == "PENDING":
                continue
            regime = h.regime
            if regime not in stats:
                stats[regime] = {"wins": 0, "losses": 0, "total": 0}
            stats[regime]["total"] += 1
            if h.result == "WIN":
                stats[regime]["wins"] += 1
            else:
                stats[regime]["losses"] += 1
        
        for regime in stats:
            total = stats[regime]["total"]
            if total > 0:
                stats[regime]["win_rate"] = stats[regime]["wins"] / total
            else:
                stats[regime]["win_rate"] = 0.5
        
        return stats
    
    def suggest_adjustments(self) -> Dict[str, float]:
        """Mevcut performansa göre ayarlama önerileri"""
        suggestions = {}
        
        overall_wr = self.get_win_rate()
        target = self.config.adaptive_win_rate_target
        rate = self.config.adaptive_adjustment_rate
        
        # Genel kazanma oranı hedeften düşükse
        if overall_wr < target - 0.05:
            suggestions["min_confidence"] = self.config.min_confidence * (1 - rate)
            suggestions["volume_spike_mult"] = self.config.volume_spike_mult * (1 + rate)
            suggestions["trigger_bps"] = self.config.trigger_bps * (1 + rate)
        
        elif overall_wr > target + 0.1:
            suggestions["min_confidence"] = self.config.min_confidence * (1 - rate * 0.5)
            suggestions["volume_spike_mult"] = self.config.volume_spike_mult * (1 - rate * 0.3)
        
        # Rejim bazlı öneriler
        regime_stats = self.get_regime_stats()
        
        for regime, stats in regime_stats.items():
            if stats["total"] < 5:
                continue
            
            if stats["win_rate"] < 0.4:
                if regime == "TRENDING_DOWN":
                    suggestions["rsi_short_min"] = max(30, self.config.rsi_short_min - 2)
                elif regime == "BIG_DROP":
                    suggestions["regime_oversold_rsi"] = max(25, self.config.regime_oversold_rsi - 2)
                elif regime == "VOLATILE":
                    suggestions["min_risk_reward"] = self.config.min_risk_reward + 0.1
        
        self.adjustments = suggestions
        return suggestions
    
    def apply_adjustments(self, config: ScalpConfig) -> ScalpConfig:
        """Önerilen ayarlamaları config'e uygula"""
        suggestions = self.suggest_adjustments()
        
        if not suggestions:
            return config
        
        # Config'i kopyala
        new_config = ScalpConfig.from_dict({
            **{f.name: getattr(config, f.name) for f in config.__dataclass_fields__.values()}
        })
        
        # Güvenli sınırlar içinde uygula
        if "min_confidence" in suggestions:
            new_config.min_confidence = max(40, min(75, suggestions["min_confidence"]))
        
        if "volume_spike_mult" in suggestions:
            new_config.volume_spike_mult = max(1.2, min(2.5, suggestions["volume_spike_mult"]))
        
        if "trigger_bps" in suggestions:
            new_config.trigger_bps = max(5, min(20, suggestions["trigger_bps"]))
        
        if "rsi_short_min" in suggestions:
            new_config.rsi_short_min = max(30, min(45, suggestions["rsi_short_min"]))
        
        if "regime_oversold_rsi" in suggestions:
            new_config.regime_oversold_rsi = max(20, min(35, suggestions["regime_oversold_rsi"]))
        
        if "min_risk_reward" in suggestions:
            new_config.min_risk_reward = max(1.5, min(3.0, suggestions["min_risk_reward"]))
        
        return new_config
    
    def get_adaptive_summary(self) -> str:
        """Adaptif özet rapor"""
        overall_wr = self.get_win_rate()
        regime_stats = self.get_regime_stats()
        suggestions = self.suggest_adjustments()
        
        lines = [
            "📊 ADAPTİF FİNE-TUNING RAPORU",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🎯 Genel Kazanma Oranı: %{overall_wr*100:.1f}",
            f"📈 Hedef: %{self.config.adaptive_win_rate_target*100:.1f}",
            f"📝 Toplam Sinyal: {len(self.history)}",
            ""
        ]
        
        if regime_stats:
            lines.append("🌍 REJİM İSTATİSTİKLERİ:")
            for regime, stats in regime_stats.items():
                lines.append(f"  • {regime}: %{stats['win_rate']*100:.1f} ({stats['wins']}W/{stats['losses']}L)")
            lines.append("")
        
        if suggestions:
            lines.append("🔧 ÖNERİLEN AYARLAMALAR:")
            for key, val in suggestions.items():
                lines.append(f"  • {key}: {val:.2f}")
        else:
            lines.append("✅ Mevcut ayarlar yeterli")
        
        return "\n".join(lines)
