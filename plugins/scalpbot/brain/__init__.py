import os
from .memory import TradingMemory, TradeMemory
from .llm_agent import LLMReasoningAgent, LLMDecision
from .context import ContextRetriever, ContextResult
from .decision import DecisionEngine, FinalDecision

class TradingBrain:
    """Trading Brain Ana Sınıfı"""
    
    def __init__(self, config):
        self.config = config
        self.memory = TradingMemory()
        self.llm_agent = LLMReasoningAgent(
            provider="groq",
            api_key=os.getenv("GROQ_API_KEY", "")
        )
        self.context_retriever = ContextRetriever(self.memory)
        self.decision_engine = DecisionEngine(config)
    
    def analyze(self, symbol, signal_result, regime, indicators):
        context = self.context_retriever.retrieve(symbol, signal_result.signal, regime, indicators)
        
        llm_decision = None
        if self.llm_agent.api_key:
            llm_decision = self.llm_agent.analyze_trade(
                symbol=symbol, direction=signal_result.signal,
                current_price=signal_result.entry_price,
                indicators=indicators, regime=regime,
                similar_trades=context.similar_trades,
                coin_stats=context.symbol_stats
            )
        
        ml_confidence = llm_decision.confidence if llm_decision else signal_result.confidence
        
        return self.decision_engine.make_decision(
            technical_signal=signal_result.signal,
            technical_score=signal_result.score,
            ml_direction=llm_decision.direction if llm_decision else signal_result.signal,
            ml_confidence=ml_confidence,
            context_summary=context.context_summary,
            regime=regime, adx=indicators.get("adx", 0),
            indicators=indicators, current_price=signal_result.entry_price
        )
    
    def daily_reflection(self):
        trades = self.memory.get_recent_trades(hours=24)
        return self.memory.generate_daily_report()
    
    def get_status(self):
        return {"memory_size": len(self.memory.get_recent_trades(hours=24)), "llm_available": bool(self.llm_agent.api_key)}
