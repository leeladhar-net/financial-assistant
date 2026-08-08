import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class ProactiveAlert(Base):
    __tablename__ = "proactive_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # earnings, price_boundary, macro
    trigger_condition: Mapped[str] = mapped_column(String(255), nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    triggered_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User")
