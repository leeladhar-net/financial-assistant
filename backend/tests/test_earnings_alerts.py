import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.scheduler.briefing_scheduler import BriefingScheduler
from app.models.financial_event import NotificationHistory

@pytest.mark.asyncio
async def test_upcoming_earnings_alerts_trigger(db_session: Session):
    # Setup completed user with watchlisted stock
    user = UserService.get_or_create_user(db_session, telegram_user_id=12401)
    UserService.update_user_preferences(db_session, user.id, role="retail_investor", markets=["US"])
    UserService.add_watchlist_symbols(db_session, user.id, ["NVDA"])
    UserService.update_user_onboarding_status(db_session, user.id, completed=True, state="COMPLETED")
    db_session.commit()

    # Mock send_message to return True so the test passes without a real Telegram chat id
    with patch("app.telegram.bot_client.TelegramBotClient.send_message") as mock_send:
        mock_send.return_value = True

        # Trigger proactive check (NVDA will mock earnings for tomorrow in tests)
        sent_count = await BriefingScheduler.check_upcoming_earnings_alerts(db_session)
        assert sent_count == 1
        assert mock_send.called

        # Verify notification history entry was recorded
        history = db_session.query(NotificationHistory).filter(NotificationHistory.user_id == user.id).all()
        assert len(history) == 1
        assert "earnings_alert_NVDA" in history[0].notification_type

        # Running check again should NOT trigger another alert (deduplication)
        sent_count_again = await BriefingScheduler.check_upcoming_earnings_alerts(db_session)
        assert sent_count_again == 0
