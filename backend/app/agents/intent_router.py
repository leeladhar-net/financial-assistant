import json
import re
from typing import List, Optional, Dict, Any
from app.schemas.financial import IntentResult
from app.integrations.llm_provider import LLMProvider
from app.core.config import settings
from app.core.logging import logger

class IntentRouter:
    """
    Classifies natural language user messages into financial intents and extracts entities (symbols, topics).
    Uses selective LLM resolution to map arbitrary company names to symbols.
    """

    @staticmethod
    async def resolve_company_to_symbol_llm(text: str) -> Optional[str]:
        """
        Uses CompanyMappingEngine to resolve a company name from text to its standard stock symbol.
        """
        from app.services.mapping_engine import CompanyMappingEngine

        # Clean query
        query = text.strip()
        
        # Avoid calling resolver for simple greetings, commands, or watchlist lookups
        greetings = {"hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening", "/start"}
        if query.lower() in greetings or query.startswith("/"):
            return None

        # Clean standard patterns to extract the company name for optimal search matching
        patterns = [
            r'^what is the price of ', r'^what is price of ', r'^price of ',
            r'^cost of ', r'^share price of ', r'^stock price of ',
            r'^get news on ', r'^news on ', r'^analyze ', r'^research '
        ]
        for pat in patterns:
            query = re.sub(pat, '', query, flags=re.IGNORECASE)
        
        # Clean trailing share/stock/share price terms
        query = re.sub(r'\b(share price|stock price|share|stock|price)\b', '', query, flags=re.IGNORECASE).strip()
        
        if not query:
            return None

        instrument = await CompanyMappingEngine.resolve_instrument(query)
        if instrument:
            # We return the ticker (which includes suffixes like .NS)
            return instrument.ticker
        return None

    @staticmethod
    async def classify_intent(
        text: str,
        user_watchlist: Optional[List[str]] = None,
        last_symbol: Optional[str] = None
    ) -> IntentResult:
        if not text:
            return IntentResult(intent="GENERAL_FINANCIAL")

        text_upper = text.upper()
        text_lower = text.lower()

        # Check for simple greetings or start command
        greetings = {"hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening", "/start"}
        if text_lower.strip().rstrip(".!?") in greetings:
            return IntentResult(intent="GREETING")

        # 1. Extract stock symbols from text
        found_symbols = []
        potential_tickers = re.findall(r'\b[A-Z]{2,6}\b', text)
        stop_words = {"AND", "THE", "FOR", "INC", "CORP", "LTD", "PLC", "USA", "PM", "AM", "AI", "MA", "VS", "COMPARE", "PRICE", "NEWS"}
        for t in potential_tickers:
            if t not in stop_words:
                found_symbols.append(t)

        company_name_map = {
            "nvidia": "NVDA",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "apple": "AAPL",
            "amazon": "AMZN",
            "tesla": "TSLA",
            "reliance": "RELIANCE.NS",
            "tcs": "TCS.NS",
            "hdfc": "HDFCBANK.NS",
            "tata steel": "TATASTEEL.NS",
            "tata motors": "TMCV.NS",
            "zomato": "ETERNAL.NS",
            "infosys": "INFY.NS",
            "wipro": "WIPRO.NS",
            "sbi": "SBIN.NS",
            "state bank": "SBIN.NS",
            "icici": "ICICIBANK.NS",
            "adani": "ADANIENT.NS",
            "meta": "META",
            "netflix": "NFLX",
            "intel": "INTC",
        }
        for comp, sym in company_name_map.items():
            if comp in text_lower and sym not in found_symbols:
                found_symbols.append(sym)

        # Selective LLM Symbol Resolution: If no symbols found, run LLM resolution
        # But skip resolution if it is a referential query (using pronouns) or a short follow-up
        is_referential = False
        if last_symbol:
            pronouns = ["it", "its", "their", "them", "this stock", "that stock", "company", "they"]
            is_pronoun_query = any(p in text_lower for p in pronouns)
            is_short_follow_up = len(text.strip().split()) <= 3 and any(kw in text_lower for kw in ["price", "quote", "news", "earnings", "chart"])
            if is_pronoun_query or is_short_follow_up:
                is_referential = True

        if not found_symbols and not is_referential:
            llm_symbol = await IntentRouter.resolve_company_to_symbol_llm(text)
            if llm_symbol:
                found_symbols = [llm_symbol]
                logger.info(f"Selective LLM Symbol Resolution resolved '{text}' to symbol '{llm_symbol}'")

        # 2. Check for Portfolio Logging Intent (PORTFOLIO_ADD)
        trade_keywords = ["bought", "sold", "purchased", "logged"]
        is_add_portfolio = False
        if any(w in text_lower for w in trade_keywords):
            is_add_portfolio = True
        elif ("buy" in text_lower or "sell" in text_lower or "add" in text_lower) and any(c.isdigit() for c in text):
            is_add_portfolio = True

        if is_add_portfolio:
            prim = found_symbols[0] if found_symbols else (last_symbol or "NVDA")
            return IntentResult(
                intent="PORTFOLIO_ADD",
                primary_symbol=prim,
                symbols=[prim] if prim else []
            )

        # 3. Check for Portfolio Viewing Intent (PORTFOLIO_VIEW)
        portfolio_keywords = ["portfolio", "holdings", "my shares", "pnl", "p&l", "investment value", "positions"]
        if any(kw in text_lower for kw in portfolio_keywords):
            return IntentResult(
                intent="PORTFOLIO_VIEW",
                symbols=user_watchlist or []
            )

        # 4. Smart Context: Inject last_symbol if no symbol is explicitly found
        using_context = False
        if not found_symbols and last_symbol:
            pronouns = ["it", "its", "their", "them", "this stock", "that stock", "company", "they"]
            is_pronoun_query = any(p in text_lower for p in pronouns)
            
            # Simple short follow-ups like "price?", "news?", "chart?"
            is_short_follow_up = len(text.strip().split()) <= 3 and any(kw in text_lower for kw in ["price", "quote", "news", "earnings", "chart"])
            
            if is_pronoun_query or is_short_follow_up:
                found_symbols = [last_symbol]
                using_context = True
                logger.info(f"Context memory activated: resolved referential query using last_symbol='{last_symbol}'")

        # 5. Check for Buy/Sell/Hold Decision Intent
        decision_keywords = ["sell", "buy", "hold", "should i", "good time to", "what should i do", "take profit", "exit position"]
        if any(kw in text_lower for kw in decision_keywords):
            prim = found_symbols[0] if found_symbols else (user_watchlist[0] if user_watchlist else "NVDA")
            action_type = "SELL" if "sell" in text_lower or "exit" in text_lower or "take profit" in text_lower else ("BUY" if "buy" in text_lower else "HOLD_OR_DECIDE")
            return IntentResult(
                intent="DECISION_ADVICE",
                primary_symbol=prim,
                symbols=[prim] if prim else [],
                topic=action_type
            )

        # 6. Check for Comparison Intent
        if "compare" in text_lower or " vs " in text_lower or " versus " in text_lower:
            prim = found_symbols[0] if len(found_symbols) > 0 else "MSFT"
            sec = found_symbols[1] if len(found_symbols) > 1 else "GOOGL"
            return IntentResult(
                intent="COMPANY_COMPARISON",
                primary_symbol=prim,
                secondary_symbol=sec,
                symbols=[prim, sec]
            )

        # 7. Check for Stock Quote Intent
        if any(kw in text_lower for kw in ["price", "quote", "stock", "trading at", "how much is"]):
            prim = found_symbols[0] if found_symbols else (user_watchlist[0] if user_watchlist else "NVDA")
            return IntentResult(
                intent="STOCK_QUOTE",
                primary_symbol=prim,
                symbols=[prim] if prim else []
            )

        # 8. Check for News / Topic Intent
        if any(kw in text_lower for kw in ["news", "headline", "earnings", "m&a", "merger", "acquisition"]):
            topic_found = None
            if "ai" in text_lower:
                topic_found = "AI"
            elif "earnings" in text_lower:
                topic_found = "Earnings"
            elif "m&a" in text_lower or "merger" in text_lower:
                topic_found = "M&A"

            return IntentResult(
                intent="NEWS_SEARCH",
                primary_symbol=found_symbols[0] if found_symbols else None,
                symbols=found_symbols,
                topic=topic_found
            )

        # 9. Check for Watchlist / Daily Summary Intent
        watchlist_keywords = [
            "anything important", "any think important", "any thing important",
            "watchlist", "summary", "briefing", "my stocks", "important today",
            "what is new", "what's new", "update me", "daily report", "news today"
        ]
        if any(kw in text_lower for kw in watchlist_keywords):
            return IntentResult(
                intent="WATCHLIST_SUMMARY",
                symbols=user_watchlist or []
            )

        # 10. Specific Company Research Intent
        if found_symbols:
            return IntentResult(
                intent="COMPANY_RESEARCH",
                primary_symbol=found_symbols[0],
                symbols=found_symbols
            )

        # Fallback to general financial query
        return IntentResult(intent="GENERAL_FINANCIAL")
