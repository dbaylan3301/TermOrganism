import time
import numpy as np
import requests
import pandas as pd
from typing import List
from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult

MOCK_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
              "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]

API_ENDPOINTS = [
    {"name": "Binance Spot", "ticker": "https://api.binance.com/api/v3/ticker/24hr", "kline": "https://api.binance.com/api/v3/klines"},
    {"name": "Binance Futures", "ticker": "https://fapi.binance.com/fapi/v1/ticker/24hr", "kline": "https://fapi.binance.com/fapi/v1/klines"},
    {"name": "Binance Spot (1)", "ticker": "https://api1.binance.com/api/v3/ticker/24hr", "kline": "https://api1.binance.com/api/v3/klines"},
    {"name": "Binance Spot (2)", "ticker": "https://api2.binance.com/api/v3/ticker/24hr", "kline": "https://api2.binance.com/api/v3/klines"},
    {"name": "Binance Spot (3)", "ticker": "https://api3.binance.com/api/v3/ticker/24hr", "kline": "https://api3.binance.com/api/v3/klines"},
]

class CoinScanner:
    def __init__(self, config: ScalpConfig, mock: bool = False):
        self.config = config
        self.running = False
        self.mock = mock
        self.working_api = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def _test_api(self, api: dict) -> bool:
        try:
            resp = self.session.get(api["ticker"], timeout=5, verify=True)
            return resp.status_code == 200
        except:
            return False

    def _find_working_api(self) -> dict:
        if self.working_api:
            return self.working_api
        for api in API_ENDPOINTS:
            if self._test_api(api):
                self.working_api = api
                print(f"✅ {api['name']} bağlantısı başarılı")
                return api
        return None

    def fetch_usdt_pairs(self) -> List[str]:
        if self.mock:
            return MOCK_PAIRS[:self.config.top_pairs]
        api = self._find_working_api()
        if not api:
            print("⚠️ Hiçbir Binance API'sine bağlanılamadı")
            return []
        try:
            resp = self.session.get(api["ticker"], timeout=10)
            resp.raise_for_status()
            tickers = resp.json()
            usdt_pairs = [
                t["symbol"] for t in tickers
                if t["symbol"].endswith("USDT")
                and float(t.get("quoteVolume", 0)) > 0
            ]
            usdt_pairs.sort(
                key=lambda s: float(
                    next(t["quoteVolume"] for t in tickers if t["symbol"] == s)
                ),
                reverse=True
            )
            return usdt_pairs[:self.config.top_pairs]
        except Exception as e:
            print(f"⚠️ Pair listesi alınamadı: {e}")
            self.working_api = None
            return []

    def fetch_klines(self, symbol: str) -> pd.DataFrame:
        if self.mock:
            return self._generate_mock_klines(symbol)
        api = self._find_working_api()
        if not api:
            return pd.DataFrame()
        try:
            params = {"symbol": symbol, "interval": self.config.kline_interval, "limit": self.config.kline_limit}
            resp = self.session.get(api["kline"], params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            print(f"⚠️ Kline alınamadı ({symbol}): {e}")
            return pd.DataFrame()

    def _generate_mock_klines(self, symbol: str) -> pd.DataFrame:
        np.random.seed(hash(symbol) % 2**31)
        n = self.config.kline_limit
        base_prices = {
            "BTCUSDT": 67000, "ETHUSDT": 3500, "SOLUSDT": 145,
            "BNBUSDT": 580, "XRPUSDT": 0.52, "DOGEUSDT": 0.12,
            "ADAUSDT": 0.45, "AVAXUSDT": 35, "DOTUSDT": 7.2, "LINKUSDT": 14.5
        }
        base = base_prices.get(symbol, 100)
        trend = np.random.choice([-0.001, 0, 0.001])
        closes = base + np.cumsum(np.random.randn(n) * base * 0.002 + base * trend)
        highs = closes * (1 + np.abs(np.random.randn(n) * 0.003))
        lows = closes * (1 - np.abs(np.random.randn(n) * 0.003))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = np.random.uniform(500000, 5000000, n)
        return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes})

    def scan_once(self) -> List[SignalResult]:
        pairs = self.fetch_usdt_pairs()
        if not pairs:
            return []
        signals = []
        for symbol in pairs:
            df = self.fetch_klines(symbol)
            if df.empty:
                continue
            result = evaluate_signal(df, self.config, symbol=symbol)
            if result.signal != "NONE":
                signals.append(result)
        return signals

    def run(self):
        self.running = True
        print("🔍 5x Scalp Bot başlatılıyor...")
        if not self.mock:
            print("   API bağlantısı test ediliyor...")
            api = self._find_working_api()
            if not api:
                print("❌ API bağlantısı kurulamadı. Mock mod ile devam ediliyor...")
                self.mock = True
        print(f"   Taranan çift sayısı: {self.config.top_pairs}")
        print(f"   Tarama aralığı: {self.config.scan_interval_sec}s")
        print("   Çıkmak için: Ctrl+C\n")

        try:
            while self.running:
                signals = self.scan_once()
                if signals:
                    for sig in signals:
                        from .display import display_signal
                        display_signal(sig)
                        print()
                else:
                    print(f"⏳ [{time.strftime('%H:%M:%S')}] Sinyal yok, bekleniyor...")
                time.sleep(self.config.scan_interval_sec)
        except KeyboardInterrupt:
            print("\n\nTarama durduruldu.")
            self.running = False
