"""Merkezi Hafıza Sistemi - Trading Brain."""

import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

@dataclass
class TradeMemory:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    leverage: int
    pnl_pct: float
    pnl_usd: float
    duration: float
    regime: str
    adx: float
    rsi: float
    volume_ratio: float
    score: int
    confidence: float
    indicators: Dict
    entry_time: str
    exit_time: str
    exit_reason: str
    lesson_learned: str = ""
    
    def to_embedding_text(self) -> str:
        """Embedding için metin oluştur."""
        return f"""
        {self.symbol} {self.direction} trade
        Entry: {self.entry_price}, Exit: {self.exit_price}
        PnL: {self.pnl_pct:.2f}%
        Regime: {self.regime}
        ADX: {self.adx:.1f}, RSI: {self.rsi:.1f}
        Volume: {self.volume_ratio:.1f}x
        Score: {self.score}, Confidence: {self.confidence:.1f}%
        Duration: {self.duration/60:.0f} minutes
        Exit: {self.exit_reason}
        Lesson: {self.lesson_learned}
        """

class TradingMemory:
    """Trading hafıza sistemi."""
    
    def __init__(self, db_path: str = "trading_memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Veritabanını başlat."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                sl_price REAL,
                tp_price REAL,
                leverage INTEGER,
                pnl_pct REAL,
                pnl_usd REAL,
                duration REAL,
                regime TEXT,
                adx REAL,
                rsi REAL,
                volume_ratio REAL,
                score INTEGER,
                confidence REAL,
                indicators TEXT,
                entry_time TEXT,
                exit_time TEXT,
                exit_reason TEXT,
                lesson_learned TEXT,
                embedding_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Strategy Performance tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                regime TEXT,
                direction TEXT,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0.0,
                avg_pnl REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                avg_duration REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Coin Behavior tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                avg_volatility REAL,
                avg_volume REAL,
                preferred_regime TEXT,
                best_direction TEXT,
                avg_hold_time REAL,
                win_rate REAL,
                sample_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Failed Patterns tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                pattern_type TEXT,
                regime TEXT,
                indicators TEXT,
                description TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_trade(self, trade: TradeMemory):
        """Trade'i kaydet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trades 
            (trade_id, symbol, direction, entry_price, exit_price, sl_price, tp_price,
             leverage, pnl_pct, pnl_usd, duration, regime, adx, rsi, volume_ratio,
             score, confidence, indicators, entry_time, exit_time, exit_reason,
             lesson_learned, embedding_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.trade_id, trade.symbol, trade.direction,
            trade.entry_price, trade.exit_price, trade.sl_price, trade.tp_price,
            trade.leverage, trade.pnl_pct, trade.pnl_usd, trade.duration,
            trade.regime, trade.adx, trade.rsi, trade.volume_ratio,
            trade.score, trade.confidence, json.dumps(trade.indicators),
            trade.entry_time, trade.exit_time, trade.exit_reason,
            trade.lesson_learned, trade.to_embedding_text()
        ))
        
        conn.commit()
        conn.close()
    
    def get_similar_trades(self, symbol: str, direction: str, regime: str,
                          limit: int = 20) -> List[TradeMemory]:
        """Benzer geçmiş trade'leri çek."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades 
            WHERE symbol = ? AND direction = ? AND regime = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (symbol, direction, regime, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def get_symbol_stats(self, symbol: str) -> Dict:
        """Symbol için istatistikleri çek."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as winning_trades,
                AVG(pnl_pct) as avg_pnl,
                AVG(duration) as avg_duration,
                SUM(pnl_usd) as total_pnl
            FROM trades 
            WHERE symbol = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:
            return {
                "total_trades": row[0],
                "winning_trades": row[1],
                "win_rate": (row[1] / row[0] * 100) if row[0] > 0 else 0,
                "avg_pnl": row[2] or 0,
                "avg_duration": row[3] or 0,
                "total_pnl": row[4] or 0
            }
        
        return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0}
    
    def get_regime_stats(self, regime: str) -> Dict:
        """Regime için istatistikleri çek."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as winners,
                AVG(pnl_pct) as avg_pnl
            FROM trades 
            WHERE regime = ?
        """, (regime,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:
            return {
                "total": row[0],
                "winners": row[1],
                "win_rate": (row[1] / row[0] * 100) if row[0] > 0 else 0,
                "avg_pnl": row[2] or 0
            }
        
        return {"total": 0, "win_rate": 0, "avg_pnl": 0}
    
    def get_recent_trades(self, hours: int = 48) -> List[TradeMemory]:
        """Son N saatlik trade'leri çek."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT * FROM trades 
            WHERE created_at > ?
            ORDER BY created_at DESC
        """, (cutoff,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def save_failed_pattern(self, symbol: str, pattern_type: str, regime: str,
                           indicators: Dict, description: str):
        """Başarısız paterni kaydet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO failed_patterns 
            (symbol, pattern_type, regime, indicators, description)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, pattern_type, regime, json.dumps(indicators), description))
        
        conn.commit()
        conn.close()
    
    def get_failed_patterns(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """Başarısız pattern'leri çek."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT * FROM failed_patterns 
                WHERE symbol = ?
                ORDER BY frequency DESC, last_seen DESC
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT * FROM failed_patterns 
                ORDER BY frequency DESC, last_seen DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0], "symbol": row[1], "pattern_type": row[2],
            "regime": row[3], "indicators": json.loads(row[4]),
            "description": row[5], "frequency": row[6]
        } for row in rows]
    
    def _row_to_trade(self, row) -> TradeMemory:
        """Satırı TradeMemory'ye çevir."""
        return TradeMemory(
            trade_id=row[0], symbol=row[1], direction=row[2],
            entry_price=row[3], exit_price=row[4], sl_price=row[5],
            tp_price=row[6], leverage=row[7], pnl_pct=row[8],
            pnl_usd=row[9], duration=row[10], regime=row[11],
            adx=row[12], rsi=row[13], volume_ratio=row[14],
            score=row[15], confidence=row[16],
            indicators=json.loads(row[17]) if row[17] else {},
            entry_time=row[18], exit_time=row[19],
            exit_reason=row[20], lesson_learned=row[21] or ""
        )
    
    def generate_daily_report(self) -> str:
        """Günlük rapor oluştur."""
        trades = self.get_recent_trades(hours=24)
        
        if not trades:
            return "Son 24 saatte işlem yok."
        
        total = len(trades)
        winners = sum(1 for t in trades if t.pnl_pct > 0)
        total_pnl = sum(t.pnl_pct for t in trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        report = f"""📊 GÜNLÜK RAPOR ({datetime.now().strftime('%Y-%m-%d')})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Toplam İşlem: {total}
✅ Kazanılan: {winners}
❌ Kaybedilen: {total - winners}
📊 Win Rate: %{winners/total*100:.1f}
💰 Toplam PnL: %{total_pnl:.2f}
📈 Ortalama PnL: %{avg_pnl:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Son İşlemler:
"""
        
        for trade in trades[:5]:
            emoji = "✅" if trade.pnl_pct > 0 else "❌"
            report += f"{emoji} {trade.symbol} {trade.direction} %{trade.pnl_pct:.2f}\n"
        
        return report
