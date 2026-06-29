"""Detaylı logging sistemi."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

class TradeLogger:
    """İşlem loglama sistemi."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.trades_file = os.path.join(log_dir, "trades.json")
        self.signals_file = os.path.join(log_dir, "signals.json")
        self.regime_file = os.path.join(log_dir, "regime.json")
        self.performance_file = os.path.join(log_dir, "performance.json")
    
    def log_signal(self, signal_data: Dict) -> None:
        """Sinyal logla."""
        signal_data["timestamp"] = datetime.now().isoformat()
        
        try:
            signals = self._load_json(self.signals_file)
            signals.append(signal_data)
            
            # Son 1000 sinyali tut
            if len(signals) > 1000:
                signals = signals[-1000:]
            
            self._save_json(self.signals_file, signals)
        except Exception:
            pass
    
    def log_trade(self, trade_data: Dict) -> None:
        """İşlem logla."""
        trade_data["timestamp"] = datetime.now().isoformat()
        
        try:
            trades = self._load_json(self.trades_file)
            trades.append(trade_data)
            self._save_json(self.trades_file, trades)
        except Exception:
            pass
    
    def log_regime(self, regime_data: Dict) -> None:
        """Rejim durumunu logla."""
        regime_data["timestamp"] = datetime.now().isoformat()
        
        try:
            regimes = self._load_json(self.regime_file)
            regimes.append(regime_data)
            
            # Son 500 kaydı tut
            if len(regimes) > 500:
                regimes = regimes[-500:]
            
            self._save_json(self.regime_file, regimes)
        except Exception:
            pass
    
    def log_performance(self, perf_data: Dict) -> None:
        """Performans verisini logla."""
        perf_data["timestamp"] = datetime.now().isoformat()
        
        try:
            perfs = self._load_json(self.performance_file)
            perfs.append(perf_data)
            self._save_json(self.performance_file, perfs)
        except Exception:
            pass
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """İşlem geçmişini al."""
        try:
            trades = self._load_json(self.trades_file)
            return trades[-limit:]
        except Exception:
            return []
    
    def get_signal_history(self, limit: int = 100) -> List[Dict]:
        """Sinyal geçmişini al."""
        try:
            signals = self._load_json(self.signals_file)
            return signals[-limit:]
        except Exception:
            return []
    
    def get_win_rate(self, last_n: int = 50) -> float:
        """Son N işlemdeki win rate."""
        trades = self.get_trade_history(last_n)
        if not trades:
            return 0.0
        
        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        return wins / len(trades) * 100
    
    def get_profit_factor(self, last_n: int = 50) -> float:
        """Son N işlemdeki profit factor."""
        trades = self.get_trade_history(last_n)
        if not trades:
            return 0.0
        
        gross_profit = sum(t.get("pnl_pct", 0) for t in trades if t.get("pnl_pct", 0) > 0)
        gross_loss = abs(sum(t.get("pnl_pct", 0) for t in trades if t.get("pnl_pct", 0) <= 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _load_json(self, filepath: str) -> List[Dict]:
        """JSON dosyasından yükle."""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return []
    
    def _save_json(self, filepath: str, data: List[Dict]) -> None:
        """JSON dosyasına kaydet."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class SignalQualityLogger:
    """Sinyal kalite analizi için logger."""
    
    def __init__(self, logger: TradeLogger):
        self.logger = logger
    
    def analyze_signal_quality(self) -> Dict:
        """Sinyal kalitesini analiz et."""
        signals = self.logger.get_signal_history(200)
        trades = self.logger.get_trade_history(200)
        
        if not signals or not trades:
            return {"quality": "UNKNOWN", "reason": "Yetersiz veri"}
        
        # Sinyal-trades eşleşmesi
        matched = 0
        for sig in signals:
            for trade in trades:
                if (sig.get("symbol") == trade.get("symbol") and
                    sig.get("signal") == trade.get("signal")):
                    matched += 1
                    break
        
        match_rate = matched / len(signals) * 100 if signals else 0
        
        # Win rate
        win_rate = self.logger.get_win_rate(100)
        
        # Profit factor
        pf = self.logger.get_profit_factor(100)
        
        # Kalite skoru
        quality_score = 0
        if match_rate > 70:
            quality_score += 30
        if win_rate > 55:
            quality_score += 35
        if pf > 1.5:
            quality_score += 35
        
        if quality_score >= 80:
            quality = "EXCELLENT"
        elif quality_score >= 60:
            quality = "GOOD"
        elif quality_score >= 40:
            quality = "FAIR"
        else:
            quality = "POOR"
        
        return {
            "quality": quality,
            "quality_score": quality_score,
            "match_rate": round(match_rate, 1),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(pf, 2),
            "total_signals": len(signals),
            "total_trades": len(trades),
        }
