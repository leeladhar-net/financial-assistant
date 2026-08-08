import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="watchlists")


class UserInterest(Base):
    __tablename__ = "user_interests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="interests")
