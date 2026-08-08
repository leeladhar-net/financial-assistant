import asyncio
import sys
import os
import httpx

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import SessionLocal, init_db
from app.schemas.telegram import TelegramUpdate
from app.telegram.message_handler import TelegramMessageHandler

async def run_polling():
    setup_logging()
    init_db()
    logger.info("Starting Telegram Bot Polling mode for local development...")

    if settings.TELEGRAM_BOT_TOKEN in ("demo_bot_token", "your_telegram_bot_token_here", ""):
        logger.warning(
            "TELEGRAM_BOT_TOKEN is set to default placeholder. "
            "Polling requires a real Telegram bot token from @BotFather. DEMO_MODE is active."
        )
        return

    base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Clear webhook before polling
        await client.post(f"{base_url}/deleteWebhook")
        logger.info("Cleared existing Telegram webhooks. Listening for messages...")

        while True:
            try:
                res = await client.get(f"{base_url}/getUpdates", params={"offset": offset, "timeout": 20})
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update_raw in updates:
                            offset = update_raw["update_id"] + 1
                            try:
                                update = TelegramUpdate.model_validate(update_raw)
                                with SessionLocal() as db:
                                    await TelegramMessageHandler.process_update(db, update)
                            except Exception as e:
                                logger.error(f"Error handling update ID {update_raw.get('update_id')}: {str(e)}")
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Polling loop terminated.")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Polling runner stopped by user.")
