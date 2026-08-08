from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint returning system status and DB readiness.
    """
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "database": db_status
    }
