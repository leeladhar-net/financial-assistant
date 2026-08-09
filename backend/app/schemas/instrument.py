from pydantic import BaseModel

class CanonicalInstrument(BaseModel):
    """
    Standard format for resolved financial instruments.
    """
    company_name: str
    exchange: str  # E.g. 'NSE', 'BSE', 'NASDAQ', 'NYSE'
    symbol: str    # E.g. 'TMCV', 'AAPL', 'ETERNAL'
    ticker: str    # E.g. 'TMCV.NS', 'AAPL', 'ETERNAL.NS' (fully queryable ticker in Yahoo Finance/Finnhub)
