from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.logging import logger

class TelegramBotClient:
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """
        Sends text message to Telegram user via Telegram Bot API with optional inline keyboard.
        """
        if self.bot_token in ("demo_bot_token", "your_telegram_bot_token_here", "", None):
            logger.info(f"[DEMO_MODE Telegram Client] Sent message to chat_id={chat_id} (reply_markup={reply_markup}):\n{text}")
            return True

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    logger.info(f"Successfully sent Telegram message to chat_id={chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error ({res.status_code}): {res.text}")
                    payload.pop("parse_mode", None)
                    res_fallback = await client.post(url, json=payload)
                    return res_fallback.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message to chat_id={chat_id}: {str(e)}")
            return False

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """
        Acknowledge Telegram callback query.
        """
        if self.bot_token in ("demo_bot_token", "your_telegram_bot_token_here", "", None):
            return True

        url = f"{self.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to answer callback query: {str(e)}")
            return False

    async def set_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> bool:
        if settings.DEMO_MODE or self.bot_token in ("demo_bot_token", ""):
            logger.info(f"[DEMO_MODE Telegram Client] Webhook set to {webhook_url}")
            return True

        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {str(e)}")
            return False
