from typing import List, Optional
from app.schemas.financial import CompanyNews
from app.integrations.market_data import MarketDataProvider

class NewsProvider:
    """
    Aggregates financial news from multiple feeds and company symbols.
    """
    @staticmethod
    async def get_watchlist_news(symbols: List[str], limit_per_symbol: int = 2) -> List[CompanyNews]:
        all_news = []
        for sym in symbols:
            news_items = await MarketDataProvider.get_company_news(sym, limit=limit_per_symbol)
            all_news.extend(news_items)
        return all_news

    @staticmethod
    async def search_topic_news(topic: str) -> List[CompanyNews]:
        clean_topic = topic.strip()
        return [
            CompanyNews(
                symbol=None,
                headline=f"Major Market Developments in {clean_topic}",
                summary=f"Key sector trends and macroeconomic shifts surrounding {clean_topic}.",
                source="Financial News Aggregator",
                url="https://financialnews.com/topics"
            )
        ]
