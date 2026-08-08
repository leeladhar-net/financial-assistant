import pytest
from app.integrations.market_data import MarketDataProvider

@pytest.mark.asyncio
async def test_get_stock_quote():
    quote = await MarketDataProvider.get_stock_quote("NVDA")
    assert quote.symbol == "NVDA"
    assert quote.price > 0
    assert quote.change_percent is not None

@pytest.mark.asyncio
async def test_get_multiple_quotes():
    quotes = await MarketDataProvider.get_multiple_quotes(["NVDA", "MSFT", "RELIANCE"])
    assert len(quotes) == 3
    symbols = [q.symbol for q in quotes]
    assert "NVDA" in symbols
    assert "MSFT" in symbols
    assert "RELIANCE" in symbols

@pytest.mark.asyncio
async def test_get_market_summary():
    us_sum = await MarketDataProvider.get_market_summary("US")
    assert us_sum.market == "US"
    assert "Nasdaq Composite" in us_sum.indices

    in_sum = await MarketDataProvider.get_market_summary("India")
    assert in_sum.market == "India"
    assert "Nifty 50" in in_sum.indices

@pytest.mark.asyncio
async def test_get_company_news():
    news = await MarketDataProvider.get_company_news("NVDA", limit=2)
    assert len(news) > 0
    assert news[0].symbol == "NVDA"
    assert news[0].headline is not None
