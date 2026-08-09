import re
from typing import List, Optional
from app.schemas.financial import IntentResult
from app.core.logging import logger

class IntentRouter:
    """
    Classifies natural language user messages into financial intents and extracts entities (symbols, topics).
    Supports Smart Context Memory through injection of last_symbol.
    """

    @staticmethod
    def classify_intent(
        text: str,
        user_watchlist: Optional[List[str]] = None,
        last_symbol: Optional[str] = None
    ) -> IntentResult:
        if not text:
            return IntentResult(intent="GENERAL_FINANCIAL")

        text_upper = text.upper()
        text_lower = text.lower()

        # 1. Extract stock symbols from text
        # Regex matching capitalized tickers or company names
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
            "reliance": "RELIANCE",
            "tcs": "TCS",
            "hdfc": "HDFC",
        }
        for comp, sym in company_name_map.items():
            if comp in text_lower and sym not in found_symbols:
                found_symbols.append(sym)

        # 2. Check for Portfolio Logging Intent (PORTFOLIO_ADD)
        trade_keywords = ["bought", "sold", "purchased", "logged"]
        is_add_portfolio = False
        if any(w in text_lower for w in trade_keywords):
            is_add_portfolio = True
        elif ("buy" in text_lower or "sell" in text_lower or "add" in text_lower) and any(c.isdigit() for c in text):
            # e.g. "buy 10 AAPL" or "add 5 shares"
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
            # If they use pronouns / referential terms OR if it's a context-dependent query
            pronouns = ["it", "its", "their", "them", "this stock", "that stock", "company", "they"]
            query_keywords = ["price", "quote", "stock", "news", "headline", "earnings", "m&a", "merger", "buy", "sell", "hold"]
            
            if any(p in text_lower for p in pronouns) or any(kw in text_lower for kw in query_keywords):
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
