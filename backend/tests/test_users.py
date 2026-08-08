import pytest
from app.services.user_service import UserService
from app.models.user import User

def test_get_or_create_new_user(db_session):
    telegram_id = 99887766
    user = UserService.get_or_create_user(
        db=db_session,
        telegram_user_id=telegram_id,
        username="test_trader",
        first_name="Alice",
        last_name="Smith"
    )
    assert user is not None
    assert user.telegram_user_id == telegram_id
    assert user.username == "test_trader"
    assert user.onboarding_completed is False
    assert user.onboarding_state == "NEW"

    # User preferences auto-initialized
    pref = UserService.get_user_preferences(db_session, user.id)
    assert pref is not None
    assert pref.user_id == user.id

def test_get_existing_user(db_session):
    telegram_id = 11223344
    user1 = UserService.get_or_create_user(db_session, telegram_id, username="old_name")
    user2 = UserService.get_or_create_user(db_session, telegram_id, username="new_name")
    
    assert user1.id == user2.id
    assert user2.username == "new_name"

def test_user_isolation(db_session):
    user_a = UserService.get_or_create_user(db_session, telegram_user_id=101)
    user_b = UserService.get_or_create_user(db_session, telegram_user_id=102)

    UserService.add_watchlist_symbols(db_session, user_a.id, ["NVDA", "AAPL"])
    UserService.add_watchlist_symbols(db_session, user_b.id, ["RELIANCE"])

    user_a_watchlists = [w.symbol for w in user_a.watchlists]
    user_b_watchlists = [w.symbol for w in user_b.watchlists]

    assert "NVDA" in user_a_watchlists
    assert "AAPL" in user_a_watchlists
    assert "RELIANCE" not in user_a_watchlists

    assert "RELIANCE" in user_b_watchlists
    assert "NVDA" not in user_b_watchlists
