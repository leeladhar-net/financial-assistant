import asyncio
import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import init_db, SessionLocal
from app.api.router import api_router
from app.schemas.telegram import TelegramUpdate
from app.telegram.message_handler import TelegramMessageHandler

async def _run_polling():
    """Background polling task — runs Telegram bot inside the web server process."""
    if settings.TELEGRAM_BOT_TOKEN in ("demo_bot_token", "your_telegram_bot_token_here", ""):
        logger.warning("No valid TELEGRAM_BOT_TOKEN. Polling disabled.")
        return

    base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    offset = 0
    logger.info("Background Telegram polling started.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(f"{base_url}/deleteWebhook")
        while True:
            try:
                res = await client.get(
                    f"{base_url}/getUpdates",
                    params={"offset": offset, "timeout": 20}
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        for update_raw in data.get("result", []):
                            offset = update_raw["update_id"] + 1
                            try:
                                update = TelegramUpdate.model_validate(update_raw)
                                with SessionLocal() as db:
                                    await TelegramMessageHandler.process_update(db, update)
                            except Exception as e:
                                logger.error(f"Error handling update: {e}")
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Background polling stopped.")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENVIRONMENT}] mode.")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Start Telegram polling in background
    polling_task = asyncio.create_task(_run_polling())

    yield

    # Shutdown
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down Financial Intelligence Assistant.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Financial Intelligence Assistant Telegram bot",
    version="1.0.0",
    lifespan=lifespan
)

# Global Exception Handler to prevent leakage of internal stack traces / credentials
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Include main router
app.include_router(api_router)

# Mount root endpoint
@app.get("/", status_code=status.HTTP_200_OK, tags=["Root"])
def root():
    return {
        "message": "Welcome to the Financial Intelligence Assistant API",
        "health_check": "/health",
        "api_v1_health": "/api/v1/health",
        "documentation": "/docs"
    }

# Mount root health endpoint for convenience
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def root_health():
    return {"status": "ok", "app_name": settings.APP_NAME}

# Debug endpoint to diagnose bot issues on Render
@app.get("/debug", status_code=status.HTTP_200_OK, tags=["Debug"])
def debug_info():
    from app.database.session import SessionLocal
    from app.models.user import User
    from app.models.conversation import Message
    
    db_status = "unknown"
    user_count = 0
    message_count = 0
    
    try:
        with SessionLocal() as db:
            user_count = db.query(User).count()
            message_count = db.query(Message).count()
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    def mask_key(k: Optional[str]) -> str:
        if not k:
            return "not_configured"
        if len(k) < 8:
            return "configured_but_short"
        return f"{k[:4]}...{k[-4:]}"

    return {
        "db_status": db_status,
        "user_count": user_count,
        "message_count": message_count,
        "env": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "bot_token": mask_key(settings.TELEGRAM_BOT_TOKEN),
        "llm_provider": settings.LLM_PROVIDER,
        "llm_key": mask_key(settings.LLM_API_KEY),
        "finnhub_key": mask_key(settings.FINNHUB_API_KEY),
        "newsapi_key": mask_key(settings.NEWSAPI_KEY)
    }
