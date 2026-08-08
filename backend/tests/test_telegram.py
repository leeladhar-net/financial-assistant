import pytest
from unittest.mock import patch, AsyncMock
from app.schemas.telegram import TelegramUpdate
from app.telegram.message_handler import TelegramMessageHandler
from app.services.user_service import UserService

@pytest.mark.asyncio
async def test_telegram_message_handler_pipeline(db_session):
    raw_update = {
        "update_id": 10001,
        "message": {
            "message_id": 55,
            "from": {
                "id": 888999,
                "is_bot": False,
                "first_name": "Bob",
                "username": "bob_analyst"
            },
            "chat": {
                "id": 888999,
                "type": "private"
            },
            "date": 1700000000,
            "text": "Hello, starting onboarding!"
        }
    }

    update = TelegramUpdate.model_validate(raw_update)

    with patch("app.telegram.bot_client.TelegramBotClient.send_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        response = await TelegramMessageHandler.process_update(db_session, update)
        assert response is not None
        assert "role" in response.lower()

        # Verify user was created in DB
        user = UserService.get_user_by_telegram_id(db_session, 888999)
        assert user is not None
        assert user.username == "bob_analyst"
        assert user.onboarding_completed is False
