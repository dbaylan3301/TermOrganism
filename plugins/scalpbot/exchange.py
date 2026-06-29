"""Exchange modülü - CCXT ile MEXC bağlantısı."""

import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

@dataclass
class OrderBookData:
    symbol: str
    bids: List[List[float]]  # [[price, volume], ...]
    asks: List[List[float]]
    timestamp: datetime
    bid_total: float = 0
    ask_total: float = 0
    imbalance: float = 0
    spread: float = 0

@dataclass
class TickerData:
    symbol: str
    last: float
    bid: float
    ask: float
    volume_24h: float
    change_24h_pct: float
    high_24h: float
    low_24h: float
    timestamp: datetime

class ExchangeClient:
    """CCXT ile exchange bağlantısı."""
    
    def __init__(self, exchange_id: str = "mexc", api_key: str = "", secret: str = ""):
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.exchange = None
        self._init_exchange()
    
    def _init_exchange(self):
        """Exchange'i başlat."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
        except Exception as e:
            print(f"Exchange init error: {e}")
            # Fallback to public API
            try:
                exchange_class = getattr(ccxt, self.exchange_id)
                self.exchange = exchange_class({
                    'enableRateLimit': True,
                })
            except Exception:
                self.exchange = None
    
    def fetch_ticker(self, symbol: str) -> Optional[TickerData]:
        """Ticker verisi çek."""
        if not self.exchange:
            return None
        
        try:
            ticker = self.exchange.fetch_ticker(f"{symbol}/USDT")
            
            return TickerData(
                symbol=symbol,
                last=ticker.get('last', 0),
                bid=ticker.get('bid', 0),
                ask=ticker.get('ask', 0),
                volume_24h=ticker.get('quoteVolume', 0),
                change_24h_pct=ticker.get('percentage', 0) or 0,
                high_24h=ticker.get('high', 0),
                low_24h=ticker.get('low', 0),
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"Ticker fetch error for {symbol}: {e}")
            return None
    
    def fetch_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBookData]:
        """Order book çek."""
        if not self.exchange:
            return None
        
        try:
            orderbook = self.exchange.fetch_order_book(f"{symbol}/USDT", limit)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Toplam hacim hesapla
            bid_total = sum(b[1] for b in bids) if bids else 0
            ask_total = sum(a[1] for a in asks) if asks else 0
            
            # Imbalance
            total = bid_total + ask_total
            imbalance = (bid_total - ask_total) / total if total > 0 else 0
            
            # Spread
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else float('inf')
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0
            
            return OrderBookData(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(),
                bid_total=bid_total,
                ask_total=ask_total,
                imbalance=imbalance,
                spread=spread
            )
        except Exception as e:
            print(f"Orderbook fetch error for {symbol}: {e}")
            return None
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> pd.DataFrame:
        """OHLCV verisi çek."""
        if not self.exchange:
            return pd.DataFrame()
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                f"{symbol}/USDT",
                timeframe,
                limit=limit
            )
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            print(f"OHLCV fetch error for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_multi_timeframe(self, symbol: str, timeframes: List[str] = ["15m", "1h"]) -> Dict[str, pd.DataFrame]:
        """Çoklu timeframe verisi çek."""
        result = {}
        for tf in timeframes:
            df = self.fetch_ohlcv(symbol, tf)
            if not df.empty:
                result[tf] = df
            time.sleep(0.1)  # Rate limit
        
        return result
    
    def get_market_info(self, symbol: str) -> Dict:
        """Piyasa bilgisi al."""
        if not self.exchange:
            return {}
        
        try:
            market = self.exchange.market(f"{symbol}/USDT")
            return {
                'symbol': symbol,
                'base': market.get('base'),
                'quote': market.get('quote'),
                'precision': market.get('precision', {}),
                'limits': market.get('limits', {}),
                'active': market.get('active', True)
            }
        except Exception:
            return {}
    
    def get_available_symbols(self) -> List[str]:
        """Kullanılabilir USDT çiftlerini al."""
        if not self.exchange:
            return []
        
        try:
            self.exchange.load_markets()
            symbols = []
            for symbol, market in self.exchange.markets.items():
                if market.get('quote') == 'USDT' and market.get('active', True):
                    symbols.append(market.get('base', symbol.split('/')[0]))
            return sorted(symbols)
        except Exception:
            return []
    
    def check_liquidity(self, symbol: str, min_volume_24h: float = 100000) -> bool:
        """Likidite kontrolü."""
        ticker = self.fetch_ticker(symbol)
        if ticker:
            return ticker.volume_24h >= min_volume_24h
        return False


class AsyncExchangeClient:
    """Async exchange istemcisi."""
    
    def __init__(self, exchange_id: str = "mexc"):
        self.exchange_id = exchange_id
        self.exchange = None
    
    async def init(self):
        """Async exchange başlat."""
        try:
            import ccxt.async_support as ccxt_async
            exchange_class = getattr(ccxt_async, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
            })
        except Exception as e:
            print(f"Async exchange init error: {e}")
    
    async def close(self):
        """Exchange bağlantısını kapat."""
        if self.exchange:
            await self.exchange.close()
    
    async def fetch_ticker(self, symbol: str) -> Optional[TickerData]:
        """Async ticker çek."""
        if not self.exchange:
            return None
        
        try:
            ticker = await self.exchange.fetch_ticker(f"{symbol}/USDT")
            
            return TickerData(
                symbol=symbol,
                last=ticker.get('last', 0),
                bid=ticker.get('bid', 0),
                ask=ticker.get('ask', 0),
                volume_24h=ticker.get('quoteVolume', 0),
                change_24h_pct=ticker.get('percentage', 0) or 0,
                high_24h=ticker.get('high', 0),
                low_24h=ticker.get('low', 0),
                timestamp=datetime.now()
            )
        except Exception:
            return None
    
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBookData]:
        """Async order book çek."""
        if not self.exchange:
            return None
        
        try:
            orderbook = await self.exchange.fetch_order_book(f"{symbol}/USDT", limit)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            bid_total = sum(b[1] for b in bids) if bids else 0
            ask_total = sum(a[1] for a in asks) if asks else 0
            
            total = bid_total + ask_total
            imbalance = (bid_total - ask_total) / total if total > 0 else 0
            
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else float('inf')
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0
            
            return OrderBookData(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(),
                bid_total=bid_total,
                ask_total=ask_total,
                imbalance=imbalance,
                spread=spread
            )
        except Exception:
            return None
