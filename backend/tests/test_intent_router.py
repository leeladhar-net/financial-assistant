import pytest
from app.agents.intent_router import IntentRouter

@pytest.mark.asyncio
async def test_intent_router_classification():
    # Stock Quote Intent
    r1 = await IntentRouter.classify_intent("What is the price of NVDA?")
    assert r1.intent == "STOCK_QUOTE"
    assert r1.primary_symbol == "NVDA"

    # Company Comparison Intent
    r2 = await IntentRouter.classify_intent("Compare Microsoft and Google from an investment perspective")
    assert r2.intent == "COMPANY_COMPARISON"
    assert r2.primary_symbol == "MSFT"
    assert r2.secondary_symbol == "GOOGL"

    # Company Research Intent
    r3 = await IntentRouter.classify_intent("What is happening with Nvidia today?")
    assert r3.intent == "COMPANY_RESEARCH"
    assert r3.primary_symbol == "NVDA"

    # News Search Intent
    r4 = await IntentRouter.classify_intent("Show me the latest AI earnings news")
    assert r4.intent == "NEWS_SEARCH"
    assert r4.topic == "AI" or r4.topic == "Earnings"

    # Watchlist Summary Intent
    r5 = await IntentRouter.classify_intent("Anything important today on my watchlist?")
    assert r5.intent == "WATCHLIST_SUMMARY"
