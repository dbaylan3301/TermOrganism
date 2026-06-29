"""LLM Reasoning Agent - Trading Brain."""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
import httpx

@dataclass
class LLMDecision:
    direction: str  # LONG, SHORT, NEUTRAL
    confidence: float
    reasoning: str
    suggested_sl: float
    suggested_tp: float
    risk_assessment: str
    alternative_scenarios: List[str]
    
class LLMReasoningAgent:
    """LLM tabanlı akıl yürütme ajanı."""
    
    def __init__(self, provider: str = "groq", api_key: str = ""):
        self.provider = provider
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = "llama-3.3-70b-versatile"
        
        # Free model alternatifleri
        self.free_models = {
            "groq": "llama-3.3-70b-versatile",
            "together": "meta-llama/Llama-3-70b-chat-hf",
            "openrouter": "meta-llama/llama-3-70b-instruct"
        }
    
    def analyze_trade(self, 
                     symbol: str,
                     direction: str,
                     current_price: float,
                     indicators: Dict,
                     regime: str,
                     similar_trades: List[Dict],
                     coin_stats: Dict) -> LLMDecision:
        """Trade analizi yap."""
        
        prompt = self._build_prompt(
            symbol, direction, current_price, indicators,
            regime, similar_trades, coin_stats
        )
        
        # LLM çağrısı
        response = self._call_llm(prompt)
        
        # Yanıtı parse et
        decision = self._parse_response(response)
        
        return decision
    
    def _build_prompt(self, symbol: str, direction: str, current_price: float,
                     indicators: Dict, regime: str, similar_trades: List[Dict],
                     coin_stats: Dict) -> str:
        """Analiz prompt'u oluştur."""
        
        # Benzer trade'leri formatla
        similar_text = ""
        if similar_trades:
            similar_text = "\n".join([
                f"- {t.get('direction', '?')} @ {t.get('entry_price', 0)} → PnL: %{t.get('pnl_pct', 0):.2f} ({t.get('exit_reason', '?')})"
                for t in similar_trades[:5]
            ])
        else:
            similar_text = "Benzer geçmiş trade bulunamadı."
        
        # Coin istatistikleri
        stats_text = f"""
        Toplam İşlem: {coin_stats.get('total_trades', 0)}
        Win Rate: %{coin_stats.get('win_rate', 0):.1f}
        Ortalama PnL: %{coin_stats.get('avg_pnl', 0):.2f}
        """
        
        prompt = f"""Sen deneyimli bir hedge fund traderısın. Aşağıdaki bilgilere göre trade için karar ver.

COIN: {symbol}
MEVCUT FİYAT: ${current_price:.4f}
ÖNERİLEN YÖN: {direction}

TEKNİK GÖSTERGELER:
- ADX: {indicators.get('adx', 0):.1f}
- RSI: {indicators.get('rsi', 0):.1f}
- EMA Fast: {indicators.get('ema_fast', 0):.4f}
- EMA Slow: {indicators.get('ema_slow', 0):.4f}
- Volume Ratio: {indicators.get('volume_ratio', 1):.1f}x
- ATR: {indicators.get('atr', 0):.4f}
- Momentum: %{indicators.get('momentum', 0):.2f}

PİYASA REJİMİ: {regime}

BENZER GEÇMİŞ İŞLEMLER:
{similar_text}

COİN İSTATİSTİKLERİ:
{stats_text}

Lütfen şu formatta karar ver:
1. KARAR: LONG/SHORT/NEUTRAL
2. GÜVEN: 0-100 arası
3. ÖNERİLEN SL: ${current_price * (1 + (-0.015 if direction == 'SHORT' else 0.015)):.4f}
4. ÖNERİLEN TP: ${current_price * (1 + (0.03 if direction == 'SHORT' else -0.03)):.4f}
5. RİSK DEĞERLENDİRMESİ: Kısa risk açıklaması
6. ALTERNATİF SENARYOLAR: 2-3 alternatif durum
7. NEDEN: Kısa neden açıklaması (chain of thought)

Cevabı JSON formatında ver."""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """LLM API'sini çağır."""
        if not self.api_key:
            return self._fallback_response()
        
        try:
            if self.provider == "groq":
                return self._call_groq(prompt)
            elif self.provider == "openrouter":
                return self._call_openrouter(prompt)
            else:
                return self._fallback_response()
        except Exception as e:
            print(f"LLM hatası: {e}")
            return self._fallback_response()
    
    def _call_groq(self, prompt: str) -> str:
        """Groq API çağrısı."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Sen profesyonel bir trading asistanısın. Kısa ve net cevaplar ver."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        
        return self._fallback_response()
    
    def _call_openrouter(self, prompt: str) -> str:
        """OpenRouter API çağrısı."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.free_models.get("openrouter"),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        
        return self._fallback_response()
    
    def _fallback_response(self) -> str:
        """API yoksa fallback yanıt."""
        return json.dumps({
            "direction": "NEUTRAL",
            "confidence": 50,
            "reasoning": "LLM API mevcut değil - varsayılan karar",
            "suggested_sl": 0,
            "suggested_tp": 0,
            "risk_assessment": "Düşük güvenilirlik",
            "alternative_scenarios": ["Bekleme modu"]
        })
    
    def _parse_response(self, response: str) -> LLMDecision:
        """LLM yanıtını parse et."""
        try:
            # JSON parse etmeye çalış
            data = json.loads(response)
            return LLMDecision(
                direction=data.get("direction", "NEUTRAL"),
                confidence=float(data.get("confidence", 50)),
                reasoning=data.get("reasoning", ""),
                suggested_sl=float(data.get("suggested_sl", 0)),
                suggested_tp=float(data.get("suggested_tp", 0)),
                risk_assessment=data.get("risk_assessment", ""),
                alternative_scenarios=data.get("alternative_scenarios", [])
            )
        except (json.JSONDecodeError, ValueError):
            # JSON değilse metinden çıkar
            return self._extract_from_text(response)
    
    def _extract_from_text(self, text: str) -> LLMDecision:
        """Metin içinden karar çıkar."""
        direction = "NEUTRAL"
        confidence = 50
        
        text_lower = text.lower()
        if "long" in text_lower:
            direction = "LONG"
            confidence = 65
        elif "short" in text_lower:
            direction = "SHORT"
            confidence = 65
        
        # Güven skorunu ara
        for line in text.split("\n"):
            if "güven" in line.lower() or "confidence" in line.lower():
                for word in line.split():
                    try:
                        num = float(word.replace("%", "").replace(":", ""))
                        if 0 <= num <= 100:
                            confidence = num
                            break
                    except ValueError:
                        continue
        
        return LLMDecision(
            direction=direction,
            confidence=confidence,
            reasoning=text[:500],
            suggested_sl=0,
            suggested_tp=0,
            risk_assessment="Analiz edildi",
            alternative_scenarios=[]
        )
    
    def daily_reflection(self, trades: List[Dict], market_summary: str) -> str:
        """Günlük refleksiyon - ne öğrendik?"""
        prompt = f"""Sen bir trading ekibisin. Bugün yapılan işlemleri analiz et ve dersler çıkar.

BUGÜNKİ İŞLEMLER:
{json.dumps(trades[:10], indent=2)}

PİYASA ÖZETİ:
{market_summary}

Lütfen şunları açıkla:
1. BUGÜN BAŞARILI OLANLAR: Neden çalıştı?
2. BAŞARISIZ OLANLAR: Neden çalışmadı?
3. ÖĞRENİLEN DERSLER: Gelecekte ne yapmalıyız?
4. STRATEJİ GÜNCELLEMELERİ: Hangi ayarlar değiştirilmeli?

Kısa ve öz ol."""
        
        return self._call_llm(prompt)
