"""Social media sentiment aggregator."""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from .news_analyzer import NewsAnalyzer, SentimentResult


@dataclass
class SocialSentiment:
    """Aggregated social sentiment."""
    overall_score: float
    overall_label: str
    news_sentiment: SentimentResult
    twitter_sentiment: Optional[SentimentResult]
    reddit_sentiment: Optional[SentimentResult]
    fear_greed_value: int
    confidence: float


class SocialAggregator:
    """Aggregate sentiment from multiple sources."""
    
    def __init__(self):
        self.analyzer = NewsAnalyzer()
        self.cache = {}
    
    def aggregate(self, news: List[str] = None, 
                  twitter: List[str] = None,
                  reddit: List[str] = None,
                  fear_greed_value: int = 50) -> SocialSentiment:
        """Aggregate sentiment from all sources."""
        
        # Analyze news
        news_sentiment = self.analyzer.analyze_headlines(news or [])
        
        # Analyze twitter
        twitter_sentiment = self.analyzer.analyze_headlines(twitter or []) if twitter else None
        
        # Analyze reddit
        reddit_sentiment = self.analyzer.analyze_headlines(reddit or []) if reddit else None
        
        # Calculate overall score
        scores = [news_sentiment.score]
        weights = [0.5]
        
        if twitter_sentiment:
            scores.append(twitter_sentiment.score)
            weights.append(0.3)
        
        if reddit_sentiment:
            scores.append(reddit_sentiment.score)
            weights.append(0.2)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        overall_score = sum(s * w for s, w in zip(scores, weights))
        
        # Adjust with Fear & Greed
        fear_greed_adjustment = (fear_greed_value - 50) / 100
        overall_score = overall_score * 0.7 + fear_greed_adjustment * 0.3
        
        # Get label
        if overall_score > 0.2:
            overall_label = "bullish"
        elif overall_score < -0.2:
            overall_label = "bearish"
        else:
            overall_label = "neutral"
        
        # Calculate confidence
        confidence = np.mean([r.confidence for r in [news_sentiment, twitter_sentiment, reddit_sentiment] if r])
        
        return SocialSentiment(
            overall_score=overall_score,
            overall_label=overall_label,
            news_sentiment=news_sentiment,
            twitter_sentiment=twitter_sentiment,
            reddit_sentiment=reddit_sentiment,
            fear_greed_value=fear_greed_value,
            confidence=confidence
        )