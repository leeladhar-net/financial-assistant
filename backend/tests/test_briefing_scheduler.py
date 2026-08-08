import pytest
from app.services.user_service import UserService
from app.scheduler.briefing_scheduler import BriefingScheduler

@pytest.mark.asyncio
async def test_generate_user_daily_briefing(db_session):
    # Setup complete user
    user = UserService.get_or_create_user(db_session, telegram_user_id=8801)
    UserService.update_user_preferences(db_session, user.id, role="equity_research", markets=["US", "India"], briefing_time="8:00 AM", response_style="detailed")
    UserService.add_watchlist_symbols(db_session, user.id, ["NVDA", "MSFT"])
    UserService.add_user_interests(db_session, user.id, ["AI", "Earnings"])
    UserService.update_user_onboarding_status(db_session, user.id, completed=True, state="COMPLETED")

    briefing = await BriefingScheduler.generate_user_daily_briefing(db_session, user.id)
    assert briefing is not None
    assert "Your Financial Brief" in briefing
    assert "NVDA" in briefing
    assert "MSFT" in briefing
