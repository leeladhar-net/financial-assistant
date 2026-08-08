from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User, UserPreference
from app.models.watchlist import Watchlist, UserInterest
from app.core.logging import logger

class UserService:
    @staticmethod
    def get_or_create_user(
        db: Session,
        telegram_user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            logger.info(f"Creating new user for telegram_user_id: {telegram_user_id}")
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                onboarding_completed=False,
                onboarding_state="NEW"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Initialize preferences row
            pref = UserPreference(user_id=user.id, markets=[])
            db.add(pref)
            db.commit()
            db.refresh(user)
        else:
            # Update profile metadata if changed
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                db.commit()
                db.refresh(user)
        return user

    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> Optional[User]:
        return db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user_onboarding_status(
        db: Session, user_id: int, completed: bool, state: str
    ) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.onboarding_completed = completed
            user.onboarding_state = state
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def get_user_preferences(db: Session, user_id: int) -> UserPreference:
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if not pref:
            pref = UserPreference(user_id=user_id, markets=[])
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_user_preferences(
        db: Session,
        user_id: int,
        role: Optional[str] = None,
        markets: Optional[List[str]] = None,
        briefing_time: Optional[str] = None,
        response_style: Optional[str] = None,
    ) -> UserPreference:
        pref = UserService.get_user_preferences(db, user_id)
        if role is not None:
            pref.role = role
        if markets is not None:
            # Merge with existing markets without duplicates
            existing = pref.markets or []
            if isinstance(existing, list):
                combined = list(dict.fromkeys(existing + markets))
                pref.markets = combined
            else:
                pref.markets = markets
        if briefing_time is not None:
            pref.briefing_time = briefing_time
        if response_style is not None:
            pref.response_style = response_style
        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def add_watchlist_symbols(
        db: Session, user_id: int, symbols: List[str], market: Optional[str] = None
    ) -> List[Watchlist]:
        added = []
        for sym in symbols:
            clean_sym = sym.strip().upper()
            if not clean_sym:
                continue
            existing = db.query(Watchlist).filter(
                Watchlist.user_id == user_id,
                Watchlist.symbol == clean_sym
            ).first()
            if not existing:
                w = Watchlist(user_id=user_id, symbol=clean_sym, market=market)
                db.add(w)
                added.append(w)
        if added:
            db.commit()
        return added

    @staticmethod
    def add_user_interests(db: Session, user_id: int, topics: List[str]) -> List[UserInterest]:
        added = []
        for topic in topics:
            clean_topic = topic.strip()
            if not clean_topic:
                continue
            existing = db.query(UserInterest).filter(
                UserInterest.user_id == user_id,
                UserInterest.topic.ilike(clean_topic)
            ).first()
            if not existing:
                ui = UserInterest(user_id=user_id, topic=clean_topic)
                db.add(ui)
                added.append(ui)
        if added:
            db.commit()
        return added
