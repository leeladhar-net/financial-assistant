import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class FinancialEvent(Base):
    __tablename__ = "financial_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # news, earnings, price_move, macro
    symbol: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    market_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    user_relevance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False) # briefing, alert, news
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User")
    event: Mapped[Optional["FinancialEvent"]] = relationship("FinancialEvent")
