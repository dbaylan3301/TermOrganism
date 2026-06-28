"""Tests for Telegram integration."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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


@pytest.mark.asyncio
@patch("core.integrations.telegram.httpx.AsyncClient")
async def test_send_message_success(mock_client_cls):
    """Test successful message sending."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    
    notifier = TelegramNotifier("token", "channel")
    result = await notifier.send_message("test message")
    
    assert result is True


@pytest.mark.asyncio
@patch("core.integrations.telegram.httpx.AsyncClient")
async def test_send_message_failure(mock_client_cls):
    """Test failed message sending."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    
    notifier = TelegramNotifier("token", "channel")
    result = await notifier.send_message("test message")
    
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