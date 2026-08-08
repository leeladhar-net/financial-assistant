from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import init_db
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENVIRONMENT}] mode. DEMO_MODE={settings.DEMO_MODE}")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {str(e)}")
    yield
    # Shutdown tasks
    logger.info("Shutting down Financial Intelligence Assistant backend.")

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
