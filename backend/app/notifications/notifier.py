from app.telegram.bot_client import TelegramBotClient
from app.core.logging import logger

class NotificationService:
    """
    Push notification dispatch service for smart alerts and briefings.
    """
    def __init__(self):
        self.bot_client = TelegramBotClient()

    async def send_user_notification(self, telegram_user_id: int, message: str) -> bool:
        logger.info(f"Sending notification to telegram_user_id={telegram_user_id}")
        return await self.bot_client.send_message(chat_id=telegram_user_id, text=message)
