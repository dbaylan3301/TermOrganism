"""Context Retrieval - Benzer geçmiş deneyimleri çek."""

from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class ContextResult:
    similar_trades: List[Dict]
    symbol_stats: Dict
    regime_stats: Dict
    failed_patterns: List[Dict]
    context_summary: str
    
class ContextRetriever:
    """Context retrieval sistemi."""
    
    def __init__(self, memory):
        self.memory = memory
    
    def retrieve(self, symbol: str, direction: str, regime: str,
                indicators: Dict) -> ContextResult:
        """Benzer context'i çek."""
        
        # 1. Benzer trade'leri çek
        similar_trades = self.memory.get_similar_trades(symbol, direction, regime)
        similar_dicts = [
            {
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl_pct": t.pnl_pct,
                "duration": t.duration,
                "exit_reason": t.exit_reason,
                "regime": t.regime,
                "adx": t.adx,
                "rsi": t.rsi,
                "volume_ratio": t.volume_ratio,
            }
            for t in similar_trades
        ]
        
        # 2. Coin istatistikleri
        symbol_stats = self.memory.get_symbol_stats(symbol)
        
        # 3. Regime istatistikleri
        regime_stats = self.memory.get_regime_stats(regime)
        
        # 4. Başarısız pattern'ler
        failed_patterns = self.memory.get_failed_patterns(symbol)
        
        # 5. Context özeti
        context_summary = self._build_summary(
            symbol, direction, regime, similar_dicts,
            symbol_stats, regime_stats, failed_patterns
        )
        
        return ContextResult(
            similar_trades=similar_dicts,
            symbol_stats=symbol_stats,
            regime_stats=regime_stats,
            failed_patterns=failed_patterns,
            context_summary=context_summary
        )
    
    def _build_summary(self, symbol: str, direction: str, regime: str,
                      similar_trades: List[Dict], symbol_stats: Dict,
                      regime_stats: Dict, failed_patterns: List[Dict]) -> str:
        """Context özeti oluştur."""
        
        # Benzer trade başarı oranı
        if similar_trades:
            similar_win_rate = sum(1 for t in similar_trades if t.get("pnl_pct", 0) > 0) / len(similar_trades) * 100
            similar_avg_pnl = np.mean([t.get("pnl_pct", 0) for t in similar_trades])
        else:
            similar_win_rate = 0
            similar_avg_pnl = 0
        
        summary = f"""
📊 CONTEXT ÖZETİ - {symbol} {direction}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Benzer Geçmiş İşlemler: {len(similar_trades)} adet
   Başarı Oranı: %{similar_win_rate:.1f}
   Ortalama PnL: %{similar_avg_pnl:.2f}

📈 Coin İstatistikleri:
   Toplam İşlem: {symbol_stats.get('total_trades', 0)}
   Win Rate: %{symbol_stats.get('win_rate', 0):.1f}

🌍 Regime İstatistikleri ({regime}):
   Toplam: {regime_stats.get('total', 0)}
   Win Rate: %{regime_stats.get('win_rate', 0):.1f}

⚠️ Bilinen Başarısız Pattern'ler: {len(failed_patterns)} adet
"""
        
        # Başarısız pattern uyarıları
        if failed_patterns:
            summary += "\n🚨 DİKKAT - Bilinen Sorunlar:\n"
            for fp in failed_patterns[:3]:
                summary += f"   • {fp.get('description', 'N/A')}\n"
        
        return summary
