import hmac
import hashlib
from typing import Optional
from app.core.config import settings

def verify_telegram_webhook_secret(received_secret: Optional[str]) -> bool:
    """
    Verifies Telegram webhook secret token header if configured.
    """
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        return True
    if not received_secret:
        return False
    return hmac.compare_digest(received_secret, settings.TELEGRAM_WEBHOOK_SECRET)

def sanitize_user_input(text: str) -> str:
    """
    Basic input sanitization to strip null bytes and excessive whitespace.
    """
    if not text:
        return ""
    return text.replace("\x00", "").strip()
