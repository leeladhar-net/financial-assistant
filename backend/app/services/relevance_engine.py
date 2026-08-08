import hashlib
import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.financial_event import FinancialEvent, NotificationHistory
from app.schemas.financial import RelevanceScoreResult
from app.core.logging import logger

class RelevanceEngine:
    """
    Intelligence scoring layer. Evaluates event importance (0-100), prevents duplicates,
    and enforces the Zero-Spam Silence Principle ("If nothing important, remain silent").
    """

    @staticmethod
    def evaluate_event(
        db: Session,
        symbol: Optional[str],
        headline: str,
        summary: Optional[str],
        source: str,
        market_impact: float,   # 0.0 - 1.0
        user_relevance: float,  # 0.0 - 1.0
        urgency: float = 0.5,   # 0.0 - 1.0
        novelty: float = 0.8    # 0.0 - 1.0
    ) -> RelevanceScoreResult:
        # Calculate fingerprint for deduplication
        raw_fp = f"{symbol or 'GENERIC'}_{headline.strip().lower()}"
        fingerprint = hashlib.sha256(raw_fp.encode('utf-8')).hexdigest()[:32]

        # Check for existing duplicate event in DB
        existing = db.query(FinancialEvent).filter(FinancialEvent.fingerprint == fingerprint).first()
        if existing:
            logger.info(f"Duplicate event detected for fingerprint={fingerprint}. Action=IGNORE")
            return RelevanceScoreResult(
                importance_score=existing.importance_score,
                market_impact=market_impact,
                user_relevance=user_relevance,
                action="IGNORE",
                is_duplicate=True
            )

        # Compute normalized importance score (0 to 100)
        # Weights: Market Impact (30%), User Relevance (30%), Urgency (20%), Novelty (20%)
        importance_score = round(
            (market_impact * 30) +
            (user_relevance * 30) +
            (urgency * 20) +
            (novelty * 20),
            2
        )

        # Determine action threshold
        if importance_score >= 80.0:
            action = "IMMEDIATE_ALERT"
        elif importance_score >= 60.0:
            action = "IMPORTANT"
        elif importance_score >= 30.0:
            action = "BRIEFING"
        else:
            action = "IGNORE"  # Silence principle!

        # Persist event in DB
        event = FinancialEvent(
            event_type="news" if symbol else "macro",
            symbol=symbol,
            headline=headline,
            summary=summary,
            source=source,
            market_impact=market_impact,
            user_relevance=user_relevance,
            importance_score=importance_score,
            fingerprint=fingerprint
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(
            f"Evaluated event for symbol={symbol}: score={importance_score}, action={action}"
        )
        return RelevanceScoreResult(
            importance_score=importance_score,
            market_impact=market_impact,
            user_relevance=user_relevance,
            action=action,
            is_duplicate=False
        )

    @staticmethod
    def record_notification_sent(
        db: Session, user_id: int, content: str, notification_type: str = "alert", event_id: Optional[int] = None
    ) -> NotificationHistory:
        hist = NotificationHistory(
            user_id=user_id,
            event_id=event_id,
            notification_type=notification_type,
            content=content
        )
        db.add(hist)
        db.commit()
        db.refresh(hist)
        return hist
