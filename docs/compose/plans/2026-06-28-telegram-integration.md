# Telegram Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Telegram channel notification when scalpbot detects high-confidence trading signals.

**Architecture:** Create a Telegram notification module that formats signals into emoji-rich messages and sends them to a specified channel via Telegram Bot API.

**Tech Stack:** Python 3.11+, httpx (async HTTP), Telegram Bot API

---

## Task 1: Create Telegram Integration Module

**Covers:** Telegram API connection and message sending

**Files:**
- Create: `core/integrations/telegram.py`

- [ ] **Step 1: Create telegram.py module**

```python
# core/integrations/telegram.py
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
```

- [ ] **Step 2: Test telegram module import**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "from core.integrations.telegram import TelegramNotifier, send_signal_notification; print('Import OK')"
```

- [ ] **Step 3: Commit changes**

```bash
git add core/integrations/telegram.py
git commit -m "feat: add Telegram integration module"
```

---

## Task 2: Add Telegram Config to ScalpConfig

**Covers:** Configuration for Telegram notifications

**Files:**
- Modify: `plugins/scalpbot/config.py:1-56`

- [ ] **Step 1: Add Telegram fields to ScalpConfig**

```python
# Add after line 49 (signal_cooldown_sec)
# Telegram
telegram_enabled: bool = True
telegram_bot_token: str = "8346013289:AAHLbunkU_lSUTDDCcoVsOKbJxZ39TeMGXc"
telegram_channel_id: str = "-100825111862"
telegram_min_confidence: float = 85.0
```

- [ ] **Step 2: Test config loads correctly**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.config import ScalpConfig
config = ScalpConfig()
print(f'Telegram enabled: {config.telegram_enabled}')
print(f'Min confidence: {config.telegram_min_confidence}')
"
```

- [ ] **Step 3: Commit changes**

```bash
git add plugins/scalpbot/config.py
git commit -m "feat: add Telegram config to ScalpConfig"
```

---

## Task 3: Integrate Telegram into Scanner

**Covers:** Send notification when signal detected

**Files:**
- Modify: `plugins/scalpbot/scanner.py:1-220`

- [ ] **Step 1: Add import for telegram module**

```python
# Add after line 17 (from .patterns import ...)
try:
    from core.integrations.telegram import send_signal_notification
except ImportError:
    send_signal_notification = None
```

- [ ] **Step 2: Add telegram notification method to CoinScanner**

```python
# Add after line 135 (check_signal_confirmation method)
def _send_telegram_notification(self, signal: SignalResult) -> None:
    """Send signal to Telegram channel if enabled."""
    if not self.config.telegram_enabled:
        return
    
    if signal.confidence < self.config.telegram_min_confidence:
        return
    
    if send_signal_notification is None:
        console.print("[#F97316]⚠ Telegram modülü bulunamadı[/#F97316]")
        return
    
    try:
        success = send_signal_notification(
            bot_token=self.config.telegram_bot_token,
            channel_id=self.config.telegram_channel_id,
            symbol=signal.symbol,
            signal=signal.signal,
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            tp_price=signal.tp_price,
            leverage=signal.leverage,
            risk_reward=signal.risk_reward,
            confidence=signal.confidence,
            confidence_level=signal.confidence_level,
        )
        
        if success:
            console.print("[#10B981]✓ Telegram'a bildirim gönderildi[/#10B981]")
        else:
            console.print("[#EF4444]✗ Telegram bildirimi başarısız[/#EF4444]")
    except Exception as e:
        console.print(f"[#EF4444]✗ Telegram hatası: {e}[/#EF4444]")
```

- [ ] **Step 3: Call telegram notification after signal confirmation**

```python
# Find line 176-186 (after self.last_signal = best)
# Add after line 178 (self.signal_count += 1):
self._send_telegram_notification(best)
```

- [ ] **Step 4: Test scanner with telegram config**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.scanner import CoinScanner
from plugins.scalpbot.config import ScalpConfig
config = ScalpConfig()
scanner = CoinScanner(config, mock=True)
print('Scanner with Telegram config loaded')
print(f'Telegram enabled: {config.telegram_enabled}')
"
```

- [ ] **Step 5: Commit changes**

```bash
git add plugins/scalpbot/scanner.py
git commit -m "feat: integrate Telegram notifications into scanner"
```

---

## Task 4: Add Telegram Test

**Covers:** Verify telegram integration works

**Files:**
- Create: `tests/test_telegram_integration.py`

- [ ] **Step 1: Create test file**

```python
# tests/test_telegram_integration.py
"""Tests for Telegram integration."""

import pytest
from unittest.mock import patch, MagicMock
from core.integrations.telegram import TelegramNotifier, send_signal_notification


def test_telegram_notifier_init():
    """Test TelegramNotifier initialization."""
    notifier = TelegramNotifier("token123", "channel456")
    assert notifier.bot_token == "token123"
    assert notifier.channel_id == "channel456"
    assert "token123" in notifier.base_url


def test_format_signal_message_long():
    """Test LONG signal message formatting."""
    notifier = TelegramNotifier("token", "channel")
    message = notifier.format_signal_message(
        symbol="BTC-USDT",
        signal="LONG",
        entry_price=65000.0,
        sl_price=63500.0,
        tp_price=68750.0,
        leverage=5,
        risk_reward=1.75,
        confidence=87.0,
        confidence_level="ÇOK YÜKSEK",
    )
    assert "🚀" in message
    assert "LONG SİNYAL" in message
    assert "BTC-USDT" in message
    assert "$65,000.00" in message
    assert "87%" in message


def test_format_signal_message_short():
    """Test SHORT signal message formatting."""
    notifier = TelegramNotifier("token", "channel")
    message = notifier.format_signal_message(
        symbol="ETH-USDT",
        signal="SHORT",
        entry_price=3500.0,
        sl_price=3600.0,
        tp_price=3300.0,
        leverage=5,
        risk_reward=2.0,
        confidence=90.0,
        confidence_level="ÇOK YÜKSEK",
    )
    assert "🔻" in message
    assert "SHORT SİNYAL" in message
    assert "ETH-USDT" in message


@patch("core.integrations.telegram.httpx.AsyncClient")
def test_send_message_success(mock_client):
    """Test successful message sending."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.return_value.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.return_value.__aexit__ = MagicMock(return_value=False)
    mock_client.return_value.post = MagicMock(return_value=mock_response)
    
    notifier = TelegramNotifier("token", "channel")
    result = notifier.send_message("test message")
    
    assert result is True


@patch("core.integrations.telegram.httpx.AsyncClient")
def test_send_message_failure(mock_client):
    """Test failed message sending."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_client.return_value.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.return_value.__aexit__ = MagicMock(return_value=False)
    mock_client.return_value.post = MagicMock(return_value=mock_response)
    
    notifier = TelegramNotifier("token", "channel")
    result = notifier.send_message("test message")
    
    assert result is False


def test_config_has_telegram_fields():
    """Test ScalpConfig has Telegram fields."""
    from plugins.scalpbot.config import ScalpConfig
    config = ScalpConfig()
    
    assert hasattr(config, "telegram_enabled")
    assert hasattr(config, "telegram_bot_token")
    assert hasattr(config, "telegram_channel_id")
    assert hasattr(config, "telegram_min_confidence")
    assert config.telegram_enabled is True
    assert config.telegram_min_confidence == 85.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -m pytest tests/test_telegram_integration.py -v
```

- [ ] **Step 3: Commit test file**

```bash
git add tests/test_telegram_integration.py
git commit -m "test: add Telegram integration tests"
```

---

## Task 5: End-to-End Test with Real Telegram

**Covers:** Verify message actually sends to Telegram channel

**Files:**
- Create: `scripts/test_telegram_send.py`

- [ ] **Step 1: Create manual test script**

```python
# scripts/test_telegram_send.py
"""Manual test script for Telegram integration."""

import asyncio
from core.integrations.telegram import TelegramNotifier


async def test_send():
    """Send test message to Telegram channel."""
    BOT_TOKEN = "8346013289:AAHLbunkU_lSUTDDCcoVsOKbJxZ39TeMGXc"
    CHANNEL_ID = "-100825111862"
    
    notifier = TelegramNotifier(BOT_TOKEN, CHANNEL_ID)
    
    test_message = """🚀 <b>TEST SİNYAL • BTC-USDT</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Giriş:</b> $65,432.00
🎯 <b>Hedef:</b> $68,750.00 (+5.07%)
🛑 <b>Stop:</b> $63,500.00 (-2.95%)
📊 <b>Kaldıraç:</b> 5x
⚡ <b>Risk/Kazanç:</b> 1:1.75
━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Güvenilirlik:</b> 87% ÇOK YÜKSEK
━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <a href="https://t.me/holygrailchat3301">HolyGrail Signals</a>"""
    
    success = await notifier.send_message(test_message)
    
    if success:
        print("✅ Mesaj başarıyla gönderildi!")
    else:
        print("❌ Mesaj gönderilemedi!")


if __name__ == "__main__":
    asyncio.run(test_send())
```

- [ ] **Step 2: Run manual test**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python scripts/test_telegram_send.py
```

- [ ] **Step 3: Commit test script**

```bash
git add scripts/test_telegram_send.py
git commit -m "test: add manual Telegram test script"
```

---

## Execution Handoff

After completing all tasks:

1. Run manual test to verify Telegram receives message
2. Start scalpbot scanner and wait for signal
3. Verify signal appears in Telegram channel

**Next Steps:**
- Add message formatting options (HTML vs Markdown)
- Add retry logic for failed sends
- Add message queue for rate limiting