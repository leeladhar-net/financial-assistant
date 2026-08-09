import json
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.portfolio import PortfolioTransaction
from app.schemas.portfolio import PortfolioHolding, PortfolioSummary
from app.integrations.llm_provider import LLMProvider
from app.integrations.market_data import MarketDataProvider
from app.core.config import settings
from app.core.logging import logger

TRADE_PARSER_PROMPT = """You are a precise financial trade execution parser. 
Your job is to read natural language user updates and extract transaction details.
You must output a raw JSON object containing:
- is_transaction: boolean (true if the text represents a buy or sell trade log, false otherwise)
- symbol: string (uppercase ticker symbol, e.g. "AAPL", "NVDA", "RELIANCE")
- quantity: float (number of shares bought or sold)
- price: float (price per share)
- transaction_type: string ("BUY" or "SELL")

Rules:
1. Translate company names to standard stock symbols (e.g. "Tesla" -> "TSLA", "Apple" -> "AAPL").
2. Only set is_transaction to true if there is a clear trade action (buy/sell), a symbol, a quantity, and a price (or if the user says "bought at market" you can infer the current price or leave it to be filled). If any critical details are missing, or if it is just a question about price, set is_transaction to false.
3. Return ONLY the raw JSON block without markdown formatting or other text."""

class PortfolioService:
    @staticmethod
    async def parse_and_log_transaction(db: Session, user_id: int, text: str) -> Optional[PortfolioTransaction]:
        """
        Parses natural language updates using Groq to log a new trade transaction.
        """
        if not settings.LLM_API_KEY:
            logger.warning("No LLM_API_KEY configured. Cannot parse portfolio trade conversational entry.")
            return None

        try:
            llm = LLMProvider()
            response_text = await llm.generate_response(text, system_prompt=TRADE_PARSER_PROMPT, fast=True)
            if not response_text:
                return None

            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)

            data = json.loads(cleaned)
            logger.info(f"Parsed trade entry: {data}")

            if not data.get("is_transaction"):
                return None

            # Resolve ticker
            raw_sym = data["symbol"].upper()
            resolved_sym = MarketDataProvider._resolve_symbol(raw_sym)
            if resolved_sym.startswith("BSE:"):
                # Standardize to short symbol for display in portfolio
                symbol_display = raw_sym
            else:
                symbol_display = raw_sym

            # Log transaction in DB
            txn = PortfolioTransaction(
                user_id=user_id,
                symbol=symbol_display,
                quantity=float(data["quantity"]),
                price=float(data["price"]),
                transaction_type=data["transaction_type"].upper()
            )
            db.add(txn)
            db.commit()
            db.refresh(txn)
            return txn
        except Exception as e:
            logger.error(f"Failed to parse and log transaction: {e}")
            return None

    @staticmethod
    async def get_portfolio_summary(db: Session, user_id: int) -> PortfolioSummary:
        """
        Aggregates user transactions, fetches live market quotes, and computes holdings P&L.
        """
        txns = db.query(PortfolioTransaction).filter(PortfolioTransaction.user_id == user_id).all()
        if not txns:
            return PortfolioSummary(
                holdings=[], total_cost=0.0, total_value=0.0, total_pnl_amount=0.0, total_pnl_percent=0.0
            )

        # 1. Group transactions by symbol
        grouped_txns: Dict[str, List[PortfolioTransaction]] = {}
        for t in txns:
            sym = t.symbol.upper()
            if sym not in grouped_txns:
                grouped_txns[sym] = []
            grouped_txns[sym].append(t)

        holdings: List[PortfolioHolding] = []
        for symbol, s_txns in grouped_txns.items():
            # Calculate holdings
            net_qty = 0.0
            total_buy_cost = 0.0
            total_buy_qty = 0.0

            for t in s_txns:
                if t.transaction_type == "BUY":
                    net_qty += t.quantity
                    total_buy_cost += t.quantity * t.price
                    total_buy_qty += t.quantity
                elif t.transaction_type == "SELL":
                    net_qty -= t.quantity

            # If the user has completely closed the position, skip active holdings list
            if net_qty <= 0:
                continue

            avg_buy_price = total_buy_cost / total_buy_qty if total_buy_qty > 0 else 0.0
            total_cost = avg_buy_price * net_qty

            # Fetch live quote
            quote = await MarketDataProvider.get_stock_quote(symbol)
            current_price = quote.price if quote else avg_buy_price
            market_value = current_price * net_qty
            pnl_amount = market_value - total_cost
            pnl_percent = (pnl_amount / total_cost) * 100 if total_cost > 0 else 0.0

            holdings.append(PortfolioHolding(
                symbol=symbol,
                quantity=net_qty,
                avg_buy_price=round(avg_buy_price, 2),
                current_price=round(current_price, 2),
                market_value=round(market_value, 2),
                total_cost=round(total_cost, 2),
                pnl_amount=round(pnl_amount, 2),
                pnl_percent=round(pnl_percent, 2)
            ))

        total_cost = sum(h.total_cost for h in holdings)
        total_value = sum(h.market_value for h in holdings)
        total_pnl_amount = total_value - total_cost
        total_pnl_percent = (total_pnl_amount / total_cost) * 100 if total_cost > 0 else 0.0

        return PortfolioSummary(
            holdings=holdings,
            total_cost=round(total_cost, 2),
            total_value=round(total_value, 2),
            total_pnl_amount=round(total_pnl_amount, 2),
            total_pnl_percent=round(total_pnl_percent, 2)
        )
