from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.schemas.telegram import TelegramUpdate
from app.telegram.message_handler import TelegramMessageHandler
from app.core.security import verify_telegram_webhook_secret

router = APIRouter()

@router.post("/telegram/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Telegram webhook receiver endpoint.
    Receives incoming Telegram updates, validates secret token header, and dispatches to handler.
    """
    if not verify_telegram_webhook_secret(x_telegram_bot_api_secret_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret token"
        )

    response_text = await TelegramMessageHandler.process_update(db, update)
    return {"status": "success", "processed": True, "response_sample": response_text[:50] if response_text else None}
