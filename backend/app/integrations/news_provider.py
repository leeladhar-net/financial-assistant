import httpx
from typing import List, Optional
from app.schemas.financial import CompanyNews
from app.integrations.market_data import MarketDataProvider
from app.core.config import settings
from app.core.logging import logger

NEWSAPI_BASE = "https://newsapi.org/v2"

# Company name map for better NewsAPI search queries
COMPANY_NAMES = {
    "NVDA": "Nvidia",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google Alphabet",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "META": "Meta Facebook",
    "NFLX": "Netflix",
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "HDFC": "HDFC Bank",
    "WIPRO": "Wipro",
    "TATAMOTORS": "Tata Motors",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "BAJFINANCE": "Bajaj Finance",
    "ADANIENT": "Adani Enterprises",
}


class NewsProvider:
    """
    Aggregates real financial news from:
    1. Finnhub — company-specific news (primary for stock symbols)
    2. NewsAPI — broad financial & market headlines (secondary & general)
    """

    @staticmethod
    async def get_company_news(symbol: str, limit: int = 5) -> List[CompanyNews]:
        """
        Fetch company-specific news. Uses Finnhub first (most relevant),
        then fills remaining slots from NewsAPI if needed.
        """
        results: List[CompanyNews] = []

        # 1. Finnhub company news (most accurate for symbol)
        finnhub_news = await MarketDataProvider.get_company_news(symbol, limit=limit)
        valid_finnhub = [n for n in finnhub_news if "No recent news" not in n.headline]
        results.extend(valid_finnhub)

        # 2. If Finnhub returned less than limit, fill with NewsAPI
        if len(results) < limit and settings.NEWSAPI_KEY:
            company_query = COMPANY_NAMES.get(symbol.upper(), symbol)
            newsapi_items = await NewsProvider._fetch_newsapi(
                query=f"{company_query} stock finance",
                limit=limit - len(results)
            )
            # Deduplicate by headline
            existing_headlines = {n.headline for n in results}
            for item in newsapi_items:
                if item.headline not in existing_headlines:
                    results.append(item)
                    existing_headlines.add(item.headline)

        return results[:limit] if results else [CompanyNews(
            symbol=symbol,
            headline=f"No recent news found for {symbol}",
            summary="Try again later or check another symbol.",
            source="System",
            url=""
        )]

    @staticmethod
    async def get_watchlist_news(symbols: List[str], limit_per_symbol: int = 2) -> List[CompanyNews]:
        """Fetch news for all symbols in watchlist."""
        all_news = []
        for sym in symbols:
            news_items = await NewsProvider.get_company_news(sym, limit=limit_per_symbol)
            all_news.extend(news_items)
        return all_news

    @staticmethod
    async def get_top_financial_headlines(limit: int = 5) -> List[CompanyNews]:
        """
        Fetch top global financial/business headlines from NewsAPI.
        Falls back to Finnhub general news if NewsAPI key not set.
        """
        if settings.NEWSAPI_KEY:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(
                        f"{NEWSAPI_BASE}/top-headlines",
                        params={
                            "category": "business",
                            "language": "en",
                            "pageSize": limit,
                            "apiKey": settings.NEWSAPI_KEY
                        }
                    )
                    if res.status_code == 200:
                        articles = res.json().get("articles", [])
                        results = []
                        for a in articles:
                            title = (a.get("title") or "").strip()
                            if not title or title == "[Removed]":
                                continue
                            results.append(CompanyNews(
                                symbol=None,
                                headline=title,
                                summary=(a.get("description") or "")[:200],
                                source=a.get("source", {}).get("name", "NewsAPI"),
                                url=a.get("url", ""),
                                published_at=a.get("publishedAt", "")
                            ))
                        if results:
                            return results[:limit]
            except Exception as e:
                logger.warning(f"NewsAPI top-headlines failed: {e}")

        # Fallback to Finnhub general news
        return await MarketDataProvider.get_general_market_news(limit=limit)

    @staticmethod
    async def search_topic_news(topic: str, limit: int = 5) -> List[CompanyNews]:
        """Search for news about any financial topic (e.g. 'AI stocks', 'India GDP')."""
        results = []

        if settings.NEWSAPI_KEY:
            results = await NewsProvider._fetch_newsapi(
                query=f"{topic} finance market",
                limit=limit
            )

        if not results:
            # Fallback to Finnhub general news
            results = await MarketDataProvider.get_general_market_news(limit=limit)

        return results[:limit]

    @staticmethod
    async def _fetch_newsapi(query: str, limit: int = 5) -> List[CompanyNews]:
        """Internal helper to call NewsAPI /everything endpoint."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={
                        "q": query,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": limit * 2,  # fetch extra to allow dedup
                        "apiKey": settings.NEWSAPI_KEY
                    }
                )
                if res.status_code == 200:
                    articles = res.json().get("articles", [])
                    results = []
                    seen = set()
                    for a in articles:
                        title = (a.get("title") or "").strip()
                        if not title or title == "[Removed]" or title in seen:
                            continue
                        seen.add(title)
                        results.append(CompanyNews(
                            symbol=None,
                            headline=title,
                            summary=(a.get("description") or "")[:200],
                            source=a.get("source", {}).get("name", "NewsAPI"),
                            url=a.get("url", ""),
                            published_at=a.get("publishedAt", "")
                        ))
                        if len(results) >= limit:
                            break
                    return results
                else:
                    logger.warning(f"NewsAPI returned {res.status_code}: {res.text[:200]}")
        except Exception as e:
            logger.warning(f"NewsAPI _fetch_newsapi failed: {e}")
        return []
