import pytest
from app.agents.intent_router import IntentRouter

def test_context_memory_intent_resolution():
    # Scenario 1: User says "what about its price?" with context "AAPL"
    r1 = IntentRouter.classify_intent("what about its price?", last_symbol="AAPL")
    assert r1.intent == "STOCK_QUOTE"
    assert r1.primary_symbol == "AAPL"
    assert r1.symbols == ["AAPL"]

    # Scenario 2: User says "any news?" with context "TSLA"
    r2 = IntentRouter.classify_intent("any news?", last_symbol="TSLA")
    assert r2.intent == "NEWS_SEARCH"
    assert r2.primary_symbol == "TSLA"
    assert r2.symbols == ["TSLA"]

    # Scenario 3: User says "should I buy it?" with context "NVDA"
    r3 = IntentRouter.classify_intent("should I buy it?", last_symbol="NVDA")
    assert r3.intent == "DECISION_ADVICE"
    assert r3.primary_symbol == "NVDA"
    assert r3.symbols == ["NVDA"]

    # Scenario 4: User says "Compare it with MSFT" with context "GOOGL"
    # Even if they say "it", "MSFT" is explicit, so IntentRouter should resolve MSFT and GOOGL
    r4 = IntentRouter.classify_intent("Compare it with MSFT", last_symbol="GOOGL")
    assert r4.intent == "COMPANY_COMPARISON"
    assert "MSFT" in r4.symbols
    assert "GOOGL" in r4.symbols
