"""Telegram channel integration for TermOrganism."""

from __future__ import annotations
import httpx
from typing import Optional


class TelegramNotifier:
    """Send notifications to Telegram channel."""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram channel."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception:
            return False
    
    def format_signal_message(
        self,
        symbol: str,
        signal: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        leverage: int,
        risk_reward: float,
        confidence: float,
        confidence_level: str,
    ) -> str:
        """Format signal into emoji-rich Telegram message."""
        is_long = signal == "LONG"
        emoji = "🚀" if is_long else "🔻"
        arrow = "▲" if is_long else "▼"
        
        entry_pct = 0.0
        sl_pct = abs(sl_price - entry_price) / entry_price * 100
        tp_pct = abs(tp_price - entry_price) / entry_price * 100
        
        if is_long:
            tp_pct = tp_pct
            sl_pct = -sl_pct
        else:
            tp_pct = -tp_pct
            sl_pct = sl_pct
        
        message = f"""{emoji} <b>{signal} SİNYAL • {symbol}</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Giriş:</b> ${entry_price:,.2f}
🎯 <b>Hedef:</b> ${tp_price:,.2f} ({tp_pct:+.2f}%)
🛑 <b>Stop:</b> ${sl_price:,.2f} ({sl_pct:+.2f}%)
📊 <b>Kaldıraç:</b> {leverage}x
⚡ <b>Risk/Kazanç:</b> 1:{risk_reward:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Güvenilirlik:</b> {confidence:.0f}% {confidence_level}
━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <a href="https://t.me/holygrailchat3301">HolyGrail Signals</a>"""
        
        return message


def send_signal_notification(
    bot_token: str,
    channel_id: str,
    symbol: str,
    signal: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    leverage: int,
    risk_reward: float,
    confidence: float,
    confidence_level: str,
) -> bool:
    """Synchronous wrapper for sending signal notification."""
    import asyncio
    
    notifier = TelegramNotifier(bot_token, channel_id)
    message = notifier.format_signal_message(
        symbol=symbol,
        signal=signal,
        entry_price=entry_price,
        sl_price=sl_price,
        tp_price=tp_price,
        leverage=leverage,
        risk_reward=risk_reward,
        confidence=confidence,
        confidence_level=confidence_level,
    )
    
    return asyncio.run(notifier.send_message(message))
