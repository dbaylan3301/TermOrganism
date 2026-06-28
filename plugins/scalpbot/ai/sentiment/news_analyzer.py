"""News sentiment analyzer."""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    score: float  # -1 to 1
    label: str  # "positive", "negative", "neutral"
    confidence: float
    keywords: List[str]


class NewsAnalyzer:
    """Analyze news sentiment for crypto."""
    
    POSITIVE_WORDS = {
        "bullish", "surge", "rally", "gain", "profit", "growth", "adoption",
        "partnership", "launch", "upgrade", "breakthrough", "record", "high",
        "moon", "pump", "buy", "long", "accumulate", "institutional"
    }
    
    NEGATIVE_WORDS = {
        "bearish", "crash", "dump", "loss", "decline", "ban", "hack",
        "scam", "fraud", "regulation", "warning", "risk", "sell", "short",
        "panic", "fear", "uncertainty", "volatile", "collapse"
    }
    
    def __init__(self):
        self.cache = {}
    
    def analyze_text(self, text: str) -> SentimentResult:
        """Analyze sentiment of text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(0.0, "neutral", 0.3, [])
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        confidence = min(0.9, 0.5 + total * 0.1)
        
        keywords = [w for w in words 
                   if w in self.POSITIVE_WORDS or w in self.NEGATIVE_WORDS]
        
        return SentimentResult(score, label, confidence, keywords[:5])
    
    def analyze_headlines(self, headlines: List[str]) -> SentimentResult:
        """Analyze multiple headlines."""
        results = [self.analyze_text(h) for h in headlines]
        
        if not results:
            return SentimentResult(0.0, "neutral", 0.0, [])
        
        avg_score = sum(r.score for r in results) / len(results)
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        all_keywords = []
        for r in results:
            all_keywords.extend(r.keywords)
        
        if avg_score > 0.2:
            label = "positive"
        elif avg_score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        return SentimentResult(
            score=avg_score,
            label=label,
            confidence=avg_confidence,
            keywords=list(set(all_keywords))[:10]
        )