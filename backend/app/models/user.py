import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_state: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    # Relationships
    preference: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    watchlists: Mapped[List["Watchlist"]] = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    interests: Mapped[List["UserInterest"]] = relationship(
        "UserInterest", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    memories: Mapped[List["UserMemory"]] = relationship(
        "UserMemory", back_populates="user", cascade="all, delete-orphan"
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    markets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    briefing_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    response_style: Mapped[Optional[str]] = mapped_column(String(50), default=None, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(50), default="English", nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="preference")
