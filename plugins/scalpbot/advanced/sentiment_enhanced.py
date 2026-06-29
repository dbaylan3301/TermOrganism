"""News Sentiment Integration - Enhanced with LLM."""

import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

@dataclass
class SentimentConfig:
    cache_ttl: int = 900  # 15 minutes
    max_posts: int = 20
    use_llm: bool = True
    llm_provider: str = "groq"  # or "xai", "openai"

class EnhancedSentimentAnalyzer:
    """Gelişmiş sentiment analizi - LLM + RSS + Social."""
    
    def __init__(self, config: SentimentConfig = None):
        self.config = config or SentimentConfig()
        self.cache = {}
        self.session = None
        
        # Keyword lists
        self.POSITIVE_WORDS = {
            "bullish", "surge", "rally", "gain", "profit", "growth", "adoption",
            "partnership", "launch", "upgrade", "breakthrough", "record", "high",
            "moon", "pump", "buy", "long", "accumulate", "institutional", "etf",
            "approval", "mainstream", "milestone", "support", "bounce", "recovery"
        }
        
        self.NEGATIVE_WORDS = {
            "bearish", "crash", "dump", "loss", "decline", "ban", "hack",
            "scam", "fraud", "regulation", "warning", "risk", "sell", "short",
            "panic", "fear", "uncertainty", "volatile", "collapse", "lawsuit",
            "SEC", "investigation", "shutdown", "vulnerability", "exploit"
        }
    
    async def get_sentiment(self, symbol: str, use_cache: bool = True) -> Dict:
        """Kapsamlı sentiment analizi."""
        cache_key = f"{symbol}_{datetime.now().timestamp() // self.config.cache_ttl}"
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        results = {
            "symbol": symbol,
            "overall_score": 0,
            "overall_label": "neutral",
            "confidence": 0,
            "sources": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Parallel source fetching
        tasks = [
            self._get_crypto_news(symbol),
            self._get_social_sentiment(symbol),
            self._get_fear_greed_index()
        ]
        
        news_result, social_result, fear_greed_result = await asyncio.gather(*tasks)
        
        # Merge results
        if news_result:
            results["sources"]["news"] = news_result
        if social_result:
            results["sources"]["social"] = social_result
        if fear_greed_result:
            results["sources"]["fear_greed"] = fear_greed_result
        
        # Calculate overall score
        scores = []
        weights = []
        
        if news_result and "score" in news_result:
            scores.append(news_result["score"])
            weights.append(0.4)
        
        if social_result and "score" in social_result:
            scores.append(social_result["score"])
            weights.append(0.3)
        
        if fear_greed_result and "score" in fear_greed_result:
            scores.append(fear_greed_result["score"])
            weights.append(0.3)
        
        if scores:
            overall_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
            results["overall_score"] = round(overall_score, 3)
            results["confidence"] = min(0.9, 0.5 + len(scores) * 0.15)
            
            if overall_score > 0.2:
                results["overall_label"] = "positive"
            elif overall_score < -0.2:
                results["overall_label"] = "negative"
            else:
                results["overall_label"] = "neutral"
        
        # Cache
        self.cache[cache_key] = results
        
        return results
    
    async def _get_crypto_news(self, symbol: str) -> Optional[Dict]:
        """Crypto haberlerini çek."""
        try:
            # CoinGecko news API (free tier)
            url = f"https://api.coingecko.com/api/v3/news"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Filter for symbol
                        symbol_lower = symbol.lower()
                        relevant_news = [
                            n for n in data
                            if symbol_lower in n.get('title', '').lower() or
                               symbol_lower in n.get('description', '').lower()
                        ][:self.config.max_posts]
                        
                        if relevant_news:
                            return self._analyze_texts([n['title'] for n in relevant_news])
        except Exception:
            pass
        
        return None
    
    async def _get_social_sentiment(self, symbol: str) -> Optional[Dict]:
        """Social media sentiment."""
        try:
            # Reddit/crypto sentiment API
            url = f"https://api.pushshift.io/reddit/search/submission/?q={symbol}&subreddit=cryptocurrency&size=20"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        posts = data.get('data', [])
                        titles = [p.get('title', '') for p in posts[:self.config.max_posts]]
                        
                        if titles:
                            return self._analyze_texts(titles)
        except Exception:
            pass
        
        return None
    
    async def _get_fear_greed_index(self) -> Optional[Dict]:
        """Fear & Greed Index."""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and len(data['data']) > 0:
                            fng = data['data'][0]
                            value = int(fng.get('value', 50))
                            classification = fng.get('value_classification', 'Neutral')
                            
                            # Convert to -1 to 1 scale
                            score = (value - 50) / 50
                            
                            return {
                                "value": value,
                                "classification": classification,
                                "score": score
                            }
        except Exception:
            pass
        
        return None
    
    def _analyze_texts(self, texts: List[str]) -> Dict:
        """Metin listesini analiz et."""
        if not texts:
            return {"score": 0, "label": "neutral", "confidence": 0}
        
        positive_count = 0
        negative_count = 0
        keywords = []
        
        for text in texts:
            text_lower = text.lower()
            words = re.findall(r'\b\w+\b', text_lower)
            
            for w in words:
                if w in self.POSITIVE_WORDS:
                    positive_count += 1
                    keywords.append(w)
                elif w in self.NEGATIVE_WORDS:
                    negative_count += 1
                    keywords.append(w)
        
        total = positive_count + negative_count
        
        if total == 0:
            return {"score": 0, "label": "neutral", "confidence": 0.3}
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "score": round(score, 3),
            "label": label,
            "confidence": min(0.9, 0.5 + total * 0.05),
            "keywords": list(set(keywords))[:10],
            "positive_count": positive_count,
            "negative_count": negative_count
        }
    
    async def get_sentiment_with_llm(self, symbol: str, posts: List[str]) -> Dict:
        """LLM ile gelişmiş sentiment analizi."""
        if not self.config.use_llm:
            return await self.get_sentiment(symbol)
        
        # Combine posts
        combined_text = "\n".join(posts[:10])
        
        prompt = f"""Analyze the sentiment of these {symbol} cryptocurrency posts.
Rate the overall sentiment from -1 (very negative) to 1 (very positive).
Also provide a brief explanation.

Posts:
{combined_text}

Return JSON format:
{{"score": <float -1 to 1>, "label": "positive/negative/neutral", "explanation": "<brief>"}}"""
        
        try:
            if self.config.llm_provider == "groq":
                return await self._call_groq(prompt)
            elif self.config.llm_provider == "xai":
                return await self._call_xai(prompt)
            else:
                return await self._call_openai(prompt)
        except Exception as e:
            # Fallback to basic analysis
            return self._analyze_texts(posts)
    
    async def _call_groq(self, prompt: str) -> Dict:
        """Groq API çağrısı."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": "Bearer ",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        
                        # Parse JSON from response
                        import json
                        json_match = re.search(r'\{[^}]+\}', content)
                        if json_match:
                            return json.loads(json_match.group())
        except Exception:
            pass
        
        return {"score": 0, "label": "neutral"}
    
    async def _call_xai(self, prompt: str) -> Dict:
        """xAI/Grok API çağrısı."""
        # Placeholder - implement with actual API
        return {"score": 0, "label": "neutral"}
    
    async def _call_openai(self, prompt: str) -> Dict:
        """OpenAI API çağrısı."""
        # Placeholder - implement with actual API
        return {"score": 0, "label": "neutral"}
    
    def get_trading_signal(self, sentiment: Dict) -> Dict:
        """Sentiment'ten trading sinyali üret."""
        score = sentiment.get("overall_score", 0)
        confidence = sentiment.get("confidence", 0)
        
        # Strong positive
        if score > 0.4 and confidence > 0.7:
            return {
                "direction": "LONG",
                "confidence": min(90, confidence * 100),
                "reason": f"Strong positive sentiment ({score:.2f})"
            }
        
        # Strong negative
        if score < -0.4 and confidence > 0.7:
            return {
                "direction": "SHORT",
                "confidence": min(90, confidence * 100),
                "reason": f"Strong negative sentiment ({score:.2f})"
            }
        
        # Moderate
        if score > 0.2:
            return {
                "direction": "LONG",
                "confidence": 60,
                "reason": f"Moderate positive sentiment ({score:.2f})"
            }
        
        if score < -0.2:
            return {
                "direction": "SHORT",
                "confidence": 60,
                "reason": f"Moderate negative sentiment ({score:.2f})"
            }
        
        return {
            "direction": "NEUTRAL",
            "confidence": 50,
            "reason": f"Neutral sentiment ({score:.2f})"
        }

class SentimentCache:
    """Sentiment cache yönetimi."""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Dict]:
        """Cache'den al."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < timedelta(seconds=entry.get('ttl', 900)):
                return entry['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict, ttl: int = 900):
        """Cache'e kaydet."""
        if len(self.cache) >= self.max_size:
            # Remove oldest
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'ttl': ttl
        }
    
    def clear(self):
        """Cache'i temizle."""
        self.cache.clear()
