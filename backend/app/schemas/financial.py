from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class StockQuote(BaseModel):
    symbol: str
    price: float
    change_amount: float
    change_percent: float
    volume: Optional[int] = None
    high: Optional[float] = None
    low: Optional[float] = None
    market: Optional[str] = "US"
    source: str = "Live Feed"

class CompanyNews(BaseModel):
    symbol: Optional[str] = None
    headline: str
    summary: Optional[str] = None
    source: str
    url: Optional[str] = None
    published_at: Optional[str] = None

class MarketSummary(BaseModel):
    market: str
    indices: Dict[str, str]  # e.g., {"S&P 500": "+0.8%", "Nasdaq": "+1.2%"}
    top_gainers: List[str] = []
    top_losers: List[str] = []
    commentary: Optional[str] = None

class IntentResult(BaseModel):
    intent: str # STOCK_QUOTE, COMPANY_RESEARCH, COMPANY_COMPARISON, NEWS_SEARCH, WATCHLIST_SUMMARY, GENERAL_FINANCIAL
    primary_symbol: Optional[str] = None
    secondary_symbol: Optional[str] = None
    symbols: List[str] = []
    topic: Optional[str] = None

class RelevanceScoreResult(BaseModel):
    importance_score: float # 0 - 100
    market_impact: float
    user_relevance: float
    action: str # IGNORE, BRIEFING, IMPORTANT, IMMEDIATE_ALERT
    is_duplicate: bool = False
