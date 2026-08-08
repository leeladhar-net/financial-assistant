from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.telegram_webhook import router as telegram_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(telegram_router, tags=["Telegram Webhook"])
