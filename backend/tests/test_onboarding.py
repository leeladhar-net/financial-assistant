import pytest
from app.services.user_service import UserService
from app.services.profile_extractor import ProfileExtractorService
from app.services.onboarding_service import OnboardingService

def test_profile_extractor_rule_based():
    text = "I am an equity research analyst covering US tech stocks like NVDA and MSFT, focused on AI and M&A."
    extracted = ProfileExtractorService.extract_profile_info(text)
    
    assert extracted.role == "equity_research"
    assert "US" in extracted.markets or "Technology" in extracted.markets
    assert "NVDA" in extracted.watchlist
    assert "MSFT" in extracted.watchlist
    assert "AI" in extracted.interests
    assert "M&A" in extracted.interests

@pytest.mark.asyncio
async def test_step_by_step_onboarding_flow(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=5001)
    
    # Step 1: Initial message
    res1 = await OnboardingService.process_onboarding_message(db_session, user, "Hello")
    assert "role" in res1.lower()
    assert user.onboarding_state == "ASK_ROLE"

    # Step 2: Provide role
    res2 = await OnboardingService.process_onboarding_message(db_session, user, "I'm a portfolio manager")
    assert "markets" in res2.lower()
    assert user.onboarding_state == "ASK_MARKETS"

    # Step 3: Provide markets
    res3 = await OnboardingService.process_onboarding_message(db_session, user, "US and Europe")
    assert "companies" in res3.lower() or "symbols" in res3.lower() or "watchlist" in res3.lower()
    assert user.onboarding_state == "ASK_WATCHLIST"

    # Step 4: Provide watchlist
    res4 = await OnboardingService.process_onboarding_message(db_session, user, "NVDA, MSFT, GOOGL")
    assert "topics" in res4.lower() or "financial topics" in res4.lower() or "interest" in res4.lower()
    assert user.onboarding_state == "ASK_INTERESTS"

    # Step 5: Provide interests
    res5 = await OnboardingService.process_onboarding_message(db_session, user, "AI and Earnings")
    assert "briefing" in res5.lower()
    assert user.onboarding_state == "ASK_BRIEFING_TIME"

    # Step 6: Provide briefing time
    res6 = await OnboardingService.process_onboarding_message(db_session, user, "8 AM")
    assert "quick" in res6.lower() or "detailed" in res6.lower() or "style" in res6.lower()
    assert user.onboarding_state == "ASK_RESPONSE_STYLE"

    # Step 7: Provide response style
    res7 = await OnboardingService.process_onboarding_message(db_session, user, "quick")
    assert "profile is set up" in res7.lower() or "personalized profile" in res7.lower()
    assert user.onboarding_completed is True
    assert user.onboarding_state == "COMPLETED"

@pytest.mark.asyncio
async def test_flexible_multi_field_onboarding(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=5002)
    
    # Send a comprehensive single response
    msg = "I'm an equity research analyst covering US and Indian equities. I follow NVDA, MSFT, and RELIANCE, focusing on AI and M&A."
    res = await OnboardingService.process_onboarding_message(db_session, user, msg)

    # System extracted role, markets, watchlists, interests automatically and jumps straight to briefing time!
    assert "briefing" in res.lower()
    assert user.onboarding_state == "ASK_BRIEFING_TIME"
