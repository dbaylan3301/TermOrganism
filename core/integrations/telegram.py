"""Telegram channel integration for TermOrganism."""

from __future__ import annotations
import httpx
from typing import Optional, List, Dict


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
        
        sl_pct = abs(sl_price - entry_price) / entry_price * 100
        tp_pct = abs(tp_price - entry_price) / entry_price * 100
        
        if is_long:
            sl_pct = -sl_pct
        else:
            tp_pct = -tp_pct
        
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
    
    def format_leaderboard(
        self,
        signals: List[Dict],
        title: str = "SIGNAL LEADERBOARD"
    ) -> str:
        """Format multiple signals into a leaderboard table."""
        if not signals:
            return ""
        
        # Emoji haritası
        score_emoji = lambda s: "🔥" if s >= 85 else "⚡" if s >= 70 else ""
        signal_label = lambda s: "STRONG BUY" if s >= 85 else "GOOD" if s >= 70 else "FAIR" if s >= 50 else "WEAK"
        
        # Tablo başı
        lines = [
            f"🏆 <b>{title}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        
        for i, sig in enumerate(signals[:8], 1):
            symbol = sig.get("symbol", "?")
            score = sig.get("score", 0)
            rsi = sig.get("rsi", 50)
            atr_pct = sig.get("atr_pct", 0)
            vol_ratio = sig.get("vol_ratio", 1)
            patterns = sig.get("patterns", [])
            signal_type = sig.get("signal", "NONE")
            
            # Volume bar (ASCII)
            vol_bars = min(int(vol_ratio * 3), 10)
            vol_bar = "█" * vol_bars + "░" * (10 - vol_bars)
            
            # Pattern
            pattern_str = patterns[0] if patterns else "-"
            
            # Signal etiketi
            if signal_type == "LONG":
                sig_label = "LONG 🚀"
            elif signal_type == "SHORT":
                sig_label = "SHORT 🔻"
            else:
                sig_label = signal_label(score)
            
            emoji = score_emoji(score)
            score_str = f"{score}{emoji}" if emoji else str(score)
            
            # Her satır ayrı bir pre bloğu
            row = f"<pre>#{i}  {symbol}  {score_str}  RSI:{rsi:.0f}  ATR:{atr_pct:.3f}%  {vol_bar}  {pattern_str}  {sig_label}</pre>"
            lines.append(row)
        
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔗 <a href=\"https://t.me/holygrailchat3301\">HolyGrail Signals</a>")
        
        return "\n".join(lines)


    def format_top_coin(
        self,
        symbol: str,
        score: int,
        rsi: float,
        atr_pct: float,
        vol_ratio: float,
        patterns: List[str],
        signal_type: str = "NONE",
        orderbook: Optional[Dict] = None,
        current_price: float = 0,
        price_change: float = 0,
        ema_status: str = "",
        rsi_status: str = "",
        volume_status: str = "",
        sl_price: float = 0,
        tp1_price: float = 0,
        tp2_price: float = 0,
        tp3_price: float = 0,
        leverage: int = 5,
    ) -> str:
        """Format clear actionable signal."""
        
        # Sinyal yönü net olmalı
        if signal_type == "LONG":
            direction_emoji = "🟢"
            direction_text = "LONG GİRİŞİ"
            action_text = "AL"
        elif signal_type == "SHORT":
            direction_emoji = "🔴"
            direction_text = "SHORT GİRİŞİ"
            action_text = "SAT"
        else:
            return ""  # Belirsiz sinyal - paylaşma
        
        vol_bars = min(int(vol_ratio * 3), 10)
        vol_bar = "█" * vol_bars + "░" * (10 - vol_bars)
        pattern_str = patterns[0].replace("_", " ") if patterns else ""
        
        # Fiyat formatı
        if current_price >= 1000:
            price_str = f"${current_price:,.2f}"
            sl_str = f"${sl_price:,.2f}"
            tp1_str = f"${tp1_price:,.2f}"
            tp2_str = f"${tp2_price:,.2f}"
            tp3_str = f"${tp3_price:,.2f}"
        elif current_price >= 1:
            price_str = f"${current_price:.4f}"
            sl_str = f"${sl_price:.4f}"
            tp1_str = f"${tp1_price:.4f}"
            tp2_str = f"${tp2_price:.4f}"
            tp3_str = f"${tp3_price:.4f}"
        else:
            price_str = f"${current_price:.6f}"
            sl_str = f"${sl_price:.6f}"
            tp1_str = f"${tp1_price:.6f}"
            tp2_str = f"${tp2_price:.6f}"
            tp3_str = f"${tp3_price:.6f}"
        
        # Değişim
        change_emoji = "🟢" if price_change >= 0 else "🔴"
        change_str = f"{change_emoji} {price_change:+.2f}%"
        
        # SL mesafesi
        sl_distance = abs(current_price - sl_price) / current_price * 100
        
        # R/R hesapla
        if signal_type == "LONG":
            risk = current_price - sl_price
            reward = tp3_price - current_price
        else:
            risk = sl_price - current_price
            reward = current_price - tp3_price
        risk_reward = reward / risk if risk > 0 else 0
        
        # Order book bölümü
        orderbook_section = ""
        if orderbook:
            supports = orderbook.get("supports", [])
            resistances = orderbook.get("resistances", [])
            imbalance = orderbook.get("imbalance", 0)
            bid_ask = orderbook.get("bid_ask_ratio", 1)
            
            # Destekler
            support_lines = []
            for s in supports[:2]:
                support_lines.append(f"• ${s['price']:.4f} ({s['distance_pct']:.1f}% aşağı)")
            
            # Dirençler
            resistance_lines = []
            for r in resistances[:2]:
                resistance_lines.append(f"• ${r['price']:.4f} ({r['distance_pct']:.1f}% yukarı)")
            
            orderbook_section = f"""
📊 ORDER BOOK
Bid/Ask: {bid_ask:.2f} | Denge: {imbalance:+.2f}

🎯 DESTEK: {chr(10).join(support_lines) if support_lines else '• Yok'}
🎯 DİRENÇ: {chr(10).join(resistance_lines) if resistance_lines else '• Yok'}"""
        
        message = f"""{direction_emoji} <b>{direction_text} • #{symbol}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Fiyat:</b> {price_str}
🔄 <b>Değişim:</b> {change_str}
📊 <b>Score:</b> {score}🔥
📈 <b>Pattern:</b> {pattern_str}
📊 <b>Volume:</b> {vol_bar} ({vol_ratio:.1f}x)
📉 <b>RSI:</b> {rsi:.0f}
{orderbook_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>HAREKET PLANI</b>

{action_text} GİRİŞİ: {price_str}
🛑 STOP: {sl_str} ({sl_distance:.1f}% risk)
✅ TP1: {tp1_str}
✅ TP2: {tp2_str}
✅ TP3: {tp3_str}

⚡ Kaldıraç: {leverage}x | R/R: 1:{risk_reward:.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i>Manage risk. DYOR.</i>
🔗 <a href="https://t.me/holygrailchat3301">HolyGrail</a>"""
        
        return message
    
    def format_ninja_alert(
        self,
        symbol: str,
        event: str,
        price: float,
        change_pct: float,
        reason: str,
    ) -> str:
        """Format ninja trade alert."""
        emoji = "🟢" if change_pct > 0 else "🔴"
        
        message = f"""⚡ <b>NINJA ALERT • {symbol}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 <b>Olay:</b> {event}
💰 <b>Fiyat:</b> ${price:,.4f}
📈 <b>Değişim:</b> {emoji} {change_pct:+.2f}%
🔍 <b>Sebep:</b> {reason}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Takipte</b> - Sinyal bekleniyor"""
        
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


def send_leaderboard_notification(
    bot_token: str,
    channel_id: str,
    signals: List[Dict],
    title: str = "SIGNAL LEADERBOARD",
) -> bool:
    """Send leaderboard table to Telegram channel."""
    import asyncio
    
    notifier = TelegramNotifier(bot_token, channel_id)
    message = notifier.format_leaderboard(signals, title)
    
    if not message:
        return False
    
    return asyncio.run(notifier.send_message(message))
