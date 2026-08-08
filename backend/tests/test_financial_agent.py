import pytest
from app.services.user_service import UserService
from app.agents.intent_router import IntentRouter
from app.agents.financial_research_agent import FinancialResearchAgent

@pytest.mark.asyncio
async def test_financial_research_agent_end_to_end(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=9901)
    UserService.update_user_onboarding_status(db_session, user.id, completed=True, state="COMPLETED")
    UserService.add_watchlist_symbols(db_session, user.id, ["NVDA", "MSFT"])

    # 1. Test Stock Quote Query
    msg1 = "What is NVDA price?"
    intent1 = IntentRouter.classify_intent(msg1, ["NVDA", "MSFT"])
    res1 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg1, intent1)
    assert "NVDA Stock Quote" in res1
    assert "Price" in res1

    # 2. Test Company Comparison Query
    msg2 = "Compare Microsoft and Google from an investment research perspective"
    intent2 = IntentRouter.classify_intent(msg2, ["NVDA", "MSFT"])
    res2 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg2, intent2)
    assert "Comparative Analysis: MSFT vs GOOGL" in res2

    # 3. Test Company Research Query
    msg3 = "What happened with Nvidia today?"
    intent3 = IntentRouter.classify_intent(msg3, ["NVDA", "MSFT"])
    res3 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg3, intent3)
    assert "Nvidia" in res3 or "NVDA" in res3
    assert "Research Update" in res3

    # 4. Test Buy/Sell Decision Query
    msg4 = "Should I sell NVDA today?"
    intent4 = IntentRouter.classify_intent(msg4, ["NVDA", "MSFT"])
    assert intent4.intent == "DECISION_ADVICE"
    res4 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg4, intent4)
    assert "Selling NVDA Today" in res4
    assert "YES, consider selling" in res4 or "NO, hold your position" in res4
