from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class PortfolioTransactionCreate(BaseModel):
    symbol: str
    quantity: float
    price: float
    transaction_type: str  # "BUY" or "SELL"

class PortfolioHolding(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    current_price: float
    market_value: float
    total_cost: float
    pnl_amount: float
    pnl_percent: float

class PortfolioSummary(BaseModel):
    holdings: List[PortfolioHolding]
    total_cost: float
    total_value: float
    total_pnl_amount: float
    total_pnl_percent: float
