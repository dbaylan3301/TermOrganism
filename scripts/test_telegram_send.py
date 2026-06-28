"""Manual test script for Telegram integration."""

import asyncio
from core.integrations.telegram import TelegramNotifier


async def test_send():
    """Send test message to Telegram channel."""
    BOT_TOKEN = "8346013289:AAHLbunkU_lSUTDDCcoVsOKbJxZ39TeMGXc"
    CHANNEL_ID = "-1003561214306"
    
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
