import pytest
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.agents import IntentRouter, FinancialResearchAgent

@pytest.mark.asyncio
async def test_financial_agent_processing(db_session: Session):
    # Setup completed user with watchlist
    user = UserService.get_or_create_user(db_session, telegram_user_id=9901)
    UserService.update_user_preferences(db_session, user.id, role="retail_investor", markets=["US"])
    UserService.add_watchlist_symbols(db_session, user.id, ["NVDA", "MSFT"])

    # 1. Test Stock Quote Query
    msg1 = "What is NVDA price?"
    intent1 = await IntentRouter.classify_intent(msg1, ["NVDA", "MSFT"])
    res1 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg1, intent1)
    assert "NVDA" in res1 or "Nvidia" in res1
    assert "Price" in res1 or "price" in res1

    # 2. Test Company Comparison Query
    msg2 = "Compare Microsoft and Google from an investment research perspective"
    intent2 = await IntentRouter.classify_intent(msg2, ["NVDA", "MSFT"])
    res2 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg2, intent2)
    assert "MSFT" in res2 or "Microsoft" in res2
    assert "GOOGL" in res2 or "Google" in res2

    # 3. Test Company Research Query
    msg3 = "What happened with Nvidia today?"
    intent3 = await IntentRouter.classify_intent(msg3, ["NVDA", "MSFT"])
    res3 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg3, intent3)
    assert "Nvidia" in res3 or "NVDA" in res3

    # 4. Test Buy/Sell Decision Query
    msg4 = "Should I sell NVDA today?"
    intent4 = await IntentRouter.classify_intent(msg4, ["NVDA", "MSFT"])
    assert intent4.intent == "DECISION_ADVICE"
    res4 = await FinancialResearchAgent.process_financial_query(db_session, user.id, msg4, intent4)
    assert "NVDA" in res4 or "Nvidia" in res4
    assert len(res4) > 0
