import pytest
from app.services.relevance_engine import RelevanceEngine

def test_relevance_scoring_and_thresholds(db_session):
    # High impact event -> IMMEDIATE_ALERT or IMPORTANT
    res_high = RelevanceEngine.evaluate_event(
        db=db_session,
        symbol="NVDA",
        headline="Nvidia Reports 200% Revenue Surge in Q3",
        summary="Data center demand reaches record highs.",
        source="Reuters",
        market_impact=1.0,
        user_relevance=1.0,
        urgency=1.0,
        novelty=1.0
    )
    assert res_high.importance_score == 100.0
    assert res_high.action == "IMMEDIATE_ALERT"

    # Low impact event -> IGNORE (Zero-Spam Rule)
    res_low = RelevanceEngine.evaluate_event(
        db=db_session,
        symbol="GENERIC",
        headline="Routine SEC Form 4 filing for minor executive share grant",
        summary="Minor administrative filing.",
        source="SEC EDGAR",
        market_impact=0.1,
        user_relevance=0.1,
        urgency=0.1,
        novelty=0.1
    )
    assert res_low.importance_score < 30.0
    assert res_low.action == "IGNORE"

def test_relevance_deduplication(db_session):
    headline = "Major M&A deal announced in semiconductor sector"
    
    # First time event is processed
    r1 = RelevanceEngine.evaluate_event(
        db=db_session, symbol="NVDA", headline=headline, summary="Deal details", source="Bloomberg",
        market_impact=0.8, user_relevance=0.8
    )
    assert r1.is_duplicate is False

    # Second time exact same event is received
    r2 = RelevanceEngine.evaluate_event(
        db=db_session, symbol="NVDA", headline=headline, summary="Deal details", source="Reuters",
        market_impact=0.8, user_relevance=0.8
    )
    assert r2.is_duplicate is True
    assert r2.action == "IGNORE"
