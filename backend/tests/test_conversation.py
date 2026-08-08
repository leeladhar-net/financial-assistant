import pytest
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService

def test_conversation_and_messages(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=6001)
    conv = ConversationService.get_or_create_active_conversation(db_session, user.id)
    assert conv is not None

    m1 = ConversationService.save_message(db_session, conv.id, user.id, "user", "What is NVDA price?")
    m2 = ConversationService.save_message(db_session, conv.id, user.id, "assistant", "NVDA is trading at $120.")

    history = ConversationService.get_recent_messages(db_session, conv.id, limit=10)
    assert len(history) == 2
    assert history[0].content == "What is NVDA price?"
    assert history[1].content == "NVDA is trading at $120."

def test_recent_messages_limit(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=6002)
    conv = ConversationService.get_or_create_active_conversation(db_session, user.id)

    for i in range(15):
        ConversationService.save_message(db_session, conv.id, user.id, "user", f"Msg {i}")

    history = ConversationService.get_recent_messages(db_session, conv.id, limit=5)
    assert len(history) == 5
    assert history[-1].content == "Msg 14"
