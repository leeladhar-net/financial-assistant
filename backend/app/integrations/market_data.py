import httpx
from typing import Dict, Any, List, Optional
from app.schemas.financial import StockQuote, MarketSummary, CompanyNews
from app.core.config import settings
from app.core.logging import logger

class MarketDataProvider:
    """
    Market Data Provider supporting live API integration (Alpha Vantage / FMP)
    with seamless realistic fallback data for DEMO_MODE.
    """
    
    @staticmethod
    async def get_stock_quote(symbol: str) -> StockQuote:
        clean_sym = symbol.strip().upper()
        
        # If API key is present and not DEMO_MODE, make live API call
        if not settings.DEMO_MODE and settings.LLM_API_KEY:
            try:
                # Live Alpha Vantage quote fetch example
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={clean_sym}&apikey={settings.LLM_API_KEY}"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json().get("Global Quote", {})
                        if data and "05. price" in data:
                            price = float(data.get("05. price", 0))
                            change_amt = float(data.get("09. change", 0))
                            change_pct = float(data.get("10. change percent", "0%").replace("%", ""))
                            return StockQuote(
                                symbol=clean_sym,
                                price=price,
                                change_amount=change_amt,
                                change_percent=change_pct,
                                source="AlphaVantage Live"
                            )
            except Exception as e:
                logger.warning(f"Live market data fetch failed for {clean_sym}: {str(e)}. Falling back to demo data.")

        # Realistic Fallback / DEMO_MODE data provider
        mock_data: Dict[str, Dict[str, Any]] = {
            "NVDA": {"price": 128.50, "change_amount": 4.20, "change_percent": 3.38, "high": 130.00, "low": 125.10},
            "MSFT": {"price": 448.20, "change_amount": 6.80, "change_percent": 1.54, "high": 450.00, "low": 443.50},
            "GOOGL": {"price": 178.40, "change_amount": -1.10, "change_percent": -0.61, "high": 180.20, "low": 177.00},
            "AAPL": {"price": 224.30, "change_amount": 2.10, "change_percent": 0.95, "high": 225.50, "low": 222.00},
            "RELIANCE": {"price": 3050.00, "change_amount": 45.00, "change_percent": 1.50, "high": 3075.00, "low": 3020.00},
            "TCS": {"price": 4250.00, "change_amount": -20.00, "change_percent": -0.47, "high": 4290.00, "low": 4230.00},
            "HDFC": {"price": 1650.00, "change_amount": 12.00, "change_percent": 0.73, "high": 1665.00, "low": 1640.00},
            "TSLA": {"price": 210.00, "change_amount": -8.50, "change_percent": -3.89, "high": 220.00, "low": 208.50},
        }

        quote_info = mock_data.get(clean_sym, {"price": 150.00, "change_amount": 1.50, "change_percent": 1.01, "high": 152.00, "low": 148.00})
        return StockQuote(
            symbol=clean_sym,
            price=quote_info["price"],
            change_amount=quote_info["change_amount"],
            change_percent=quote_info["change_percent"],
            high=quote_info.get("high"),
            low=quote_info.get("low"),
            source="Demo Market Feed"
        )

    @staticmethod
    async def get_multiple_quotes(symbols: List[str]) -> List[StockQuote]:
        quotes = []
        for sym in symbols:
            q = await MarketDataProvider.get_stock_quote(sym)
            quotes.append(q)
        return quotes

    @staticmethod
    async def get_market_summary(market: str = "US") -> MarketSummary:
        market_upper = market.upper()
        if "INDIA" in market_upper:
            return MarketSummary(
                market="India",
                indices={"Nifty 50": "+0.65%", "BSE Sensex": "+0.58%"},
                top_gainers=["RELIANCE (+1.5%)", "INFY (+1.8%)"],
                top_losers=["TCS (-0.47%)"],
                commentary="Indian equity benchmarks closed higher led by IT and banking stocks."
            )
        return MarketSummary(
            market="US",
            indices={"Nasdaq Composite": "+1.25%", "S&P 500": "+0.82%", "Dow Jones": "+0.35%"},
            top_gainers=["NVDA (+3.38%)", "MSFT (+1.54%)"],
            top_losers=["TSLA (-3.89%)"],
            commentary="Tech rally led by AI sentiment pushed Nasdaq higher."
        )

    @staticmethod
    async def get_company_news(symbol: str, limit: int = 5) -> List[CompanyNews]:
        clean_sym = symbol.strip().upper()
        news_map: Dict[str, List[Dict[str, str]]] = {
            "NVDA": [
                {
                    "headline": "Nvidia Announces Next-Generation Blackwell Ultra Architecture Demand Surge",
                    "summary": "Hyperscalers increase capital expenditure commitments for Nvidia GPU clusters.",
                    "source": "Financial Times",
                    "url": "https://ft.com/nvda-blackwell"
                },
                {
                    "headline": "Analyst Upgrades Nvidia Price Target on Strong Data Center Growth",
                    "summary": "Wall Street research notes point to expanding enterprise AI deployment.",
                    "source": "Reuters",
                    "url": "https://reuters.com/nvda-upgrade"
                }
            ],
            "MSFT": [
                {
                    "headline": "Microsoft Cloud Revenue Accelerates Driven by Copilot Adoption",
                    "summary": "Azure growth exceeds quarterly estimates with expanding enterprise seats.",
                    "source": "Wall Street Journal",
                    "url": "https://wsj.com/msft-azure"
                }
            ],
            "RELIANCE": [
                {
                    "headline": "Reliance Industries Expands Clean Energy Investments & Retail Footprint",
                    "summary": "Jio Financial and retail divisions drive quarterly revenue expansion.",
                    "source": "Economic Times",
                    "url": "https://economictimes.indiatimes.com/reliance"
                }
            ]
        }

        raw_items = news_map.get(clean_sym, [
            {
                "headline": f"{clean_sym} Reports Strong Operational Momentum and Quarterly Progress",
                "summary": f"Key institutional investors evaluate growth prospects for {clean_sym}.",
                "source": "Bloomberg Wire",
                "url": f"https://bloomberg.com/quote/{clean_sym}"
            }
        ])

        results = []
        for item in raw_items[:limit]:
            results.append(CompanyNews(
                symbol=clean_sym,
                headline=item["headline"],
                summary=item["summary"],
                source=item["source"],
                url=item["url"]
            ))
        return results
