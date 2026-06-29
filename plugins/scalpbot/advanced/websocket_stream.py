"""WebSocket Real-time Data Stream - CCXT Pro."""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class StreamConfig:
    symbols: List[str]
    timeframe: str = "1m"
    buffer_size: int = 1000
    update_interval: int = 5  # seconds

class WebSocketStream:
    """WebSocket ile gerçek zamanlı veri akışı."""
    
    def __init__(self, exchange_id: str = "mexc"):
        self.exchange_id = exchange_id
        self.exchange = None
        self.data_buffers = {}
        self.callbacks = []
        self.running = False
        self._task = None
        
        try:
            import ccxt.pro as ccxtpro
            self.ccxtpro = ccxtpro
            self.available = True
        except ImportError:
            self.available = False
    
    async def start(self, config: StreamConfig) -> bool:
        """WebSocket akışını başlat."""
        if not self.available:
            return False
        
        try:
            self.exchange = self.ccxtpro.mexc({
                'apiKey': '',
                'secret': '',
                'enableRateLimit': True,
            })
            
            self.running = True
            self._task = asyncio.create_task(self._stream_loop(config))
            return True
        except Exception as e:
            print(f"WebSocket start error: {e}")
            return False
    
    async def stop(self):
        """WebSocket akışını durdur."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.exchange:
            await self.exchange.close()
    
    async def _stream_loop(self, config: StreamConfig):
        """Ana stream döngüsü."""
        tasks = []
        for symbol in config.symbols:
            task = asyncio.create_task(
                self._watch_symbol(symbol, config.timeframe, config.buffer_size)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _watch_symbol(self, symbol: str, timeframe: str, buffer_size: int):
        """Tek sembol için ticker watched."""
        if symbol not in self.data_buffers:
            self.data_buffers[symbol] = []
        
        while self.running:
            try:
                ticker = await self.exchange.watch_ticker(f"{symbol}/USDT")
                
                data_point = {
                    'symbol': symbol,
                    'last': ticker.get('last', 0),
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'volume': ticker.get('quoteVolume', 0),
                    'change': ticker.get('percentage', 0) or 0,
                    'timestamp': datetime.now()
                }
                
                self.data_buffers[symbol].append(data_point)
                
                # Buffer limiti
                if len(self.data_buffers[symbol]) > buffer_size:
                    self.data_buffers[symbol] = self.data_buffers[symbol][-buffer_size:]
                
                # Callback'leri çağır
                for callback in self.callbacks:
                    try:
                        await callback(data_point)
                    except Exception:
                        pass
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Watch error for {symbol}: {e}")
                await asyncio.sleep(1)
    
    async def watch_ohlcv(self, symbol: str, timeframe: str = "1m", 
                          limit: int = 100) -> pd.DataFrame:
        """OHLCV verisi çek."""
        if not self.exchange:
            return pd.DataFrame()
        
        try:
            ohlcv = await self.exchange.watch_ohlcv(
                f"{symbol}/USDT", timeframe, limit=limit
            )
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"OHLCV error: {e}")
            return pd.DataFrame()
    
    async def watch_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """Order book watched."""
        if not self.exchange:
            return {}
        
        try:
            orderbook = await self.exchange.watch_order_book(f"{symbol}/USDT", limit)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            bid_total = sum(b[1] for b in bids)
            ask_total = sum(a[1] for a in asks)
            
            imbalance = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0
            
            return {
                'bids': bids,
                'asks': asks,
                'bid_total': bid_total,
                'ask_total': ask_total,
                'imbalance': imbalance,
                'spread': asks[0][0] - bids[0][0] if bids and asks else 0
            }
        except Exception as e:
            print(f"Orderbook error: {e}")
            return {}
    
    def add_callback(self, callback: Callable):
        """Callback ekle."""
        self.callbacks.append(callback)
    
    def get_buffer(self, symbol: str) -> List[Dict]:
        """Sembol buffer'ını al."""
        return self.data_buffers.get(symbol, [])
    
    def get_latest(self, symbol: str) -> Optional[Dict]:
        """Son veri noktasını al."""
        buffer = self.data_buffers.get(symbol, [])
        return buffer[-1] if buffer else None
    
    def to_dataframe(self, symbol: str) -> pd.DataFrame:
        """Buffer'ı DataFrame'e çevir."""
        buffer = self.data_buffers.get(symbol, [])
        if not buffer:
            return pd.DataFrame()
        
        return pd.DataFrame(buffer)

class DataProcessor:
    """WebSocket verisini işleyen modül."""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.price_history = {}
        self.volume_history = {}
    
    def update(self, data_point: Dict) -> Dict:
        """Yeni veri noktasını işle."""
        symbol = data_point['symbol']
        
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
        
        self.price_history[symbol].append(data_point['last'])
        self.volume_history[symbol].append(data_point['volume'])
        
        # Window limiti
        if len(self.price_history[symbol]) > self.window_size:
            self.price_history[symbol] = self.price_history[symbol][-self.window_size:]
            self.volume_history[symbol] = self.volume_history[symbol][-self.window_size:]
        
        # İndikatörler
        prices = np.array(self.price_history[symbol])
        volumes = np.array(self.volume_history[symbol])
        
        indicators = {}
        
        if len(prices) >= 2:
            indicators['returns'] = (prices[-1] / prices[-2] - 1) * 100
            indicators['volatility'] = np.std(np.diff(prices) / prices[:-1]) * 100 if len(prices) > 1 else 0
        
        if len(prices) >= 9:
            indicators['ema_9'] = self._ema(prices, 9)
        
        if len(prices) >= 21:
            indicators['ema_21'] = self._ema(prices, 21)
        
        if len(prices) >= 14:
            indicators['rsi'] = self._rsi(prices, 14)
        
        if len(volumes) >= 20:
            indicators['volume_ma'] = np.mean(volumes[-20:])
            indicators['volume_ratio'] = volumes[-1] / indicators['volume_ma'] if indicators['volume_ma'] > 0 else 1
        
        return {
            'symbol': symbol,
            'price': data_point['last'],
            'indicators': indicators,
            'timestamp': data_point['timestamp']
        }
    
    def _ema(self, data: np.ndarray, period: int) -> float:
        """EMA hesapla."""
        alpha = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def _rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """RSI hesapla."""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
