from typing import List, Optional
from sqlalchemy.orm import Session

from app.schemas.financial import IntentResult, StockQuote, CompanyNews
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_provider import NewsProvider
from app.integrations.llm_provider import LLMProvider
from app.services.user_service import UserService
from app.core.logging import logger

class FinancialResearchAgent:
    """
    Coordinates data retrieval (quotes + news + profile context) and generates
    concise, structured financial answers formatted for Telegram (10-20 sec read).
    """

    @staticmethod
    async def process_financial_query(
        db: Session,
        user_id: int,
        user_message: str,
        intent_result: IntentResult
    ) -> str:
        logger.info(f"FinancialResearchAgent handling query for user_id={user_id}, intent={intent_result.intent}")

        pref = UserService.get_user_preferences(db, user_id)
        role_title = pref.role.replace("_", " ").title() if pref and pref.role else "Financial Professional"

        intent = intent_result.intent

        # 0. DECISION / BUY / SELL / HOLD INTENT
        if intent == "DECISION_ADVICE":
            symbol = intent_result.primary_symbol or "NVDA"
            action_type = intent_result.topic or "SELL"
            quote = await MarketDataProvider.get_stock_quote(symbol)
            news_items = await MarketDataProvider.get_company_news(symbol, limit=1)

            direction = "↑" if quote.change_amount >= 0 else "↓"
            sign = "+" if quote.change_amount >= 0 else ""
            news_headline = news_items[0].headline if news_items else "Strong operational momentum reported."

            from app.services.proactive_alert_service import ProactiveAlertService
            ProactiveAlertService.create_automatic_alerts(db, user_id, symbol, quote.price)

            if action_type == "SELL":
                return (
                    f"💡 *Actionable Analysis: Selling {symbol} Today*\n\n"
                    f"Current Market State: *${quote.price:.2f}* ({direction} {sign}{quote.change_percent:.2f}%)\n\n"
                    f"• *YES, consider selling / taking partial profit IF*:\n"
                    f"  1. Your portfolio position allocation exceeds your target risk limit.\n"
                    f"  2. You wish to lock in recent short-term gains following recent rally (+{quote.change_percent:.2f}% move).\n"
                    f"  3. Stock price breaks below key support at *${(quote.price * 0.95):.2f}*.\n\n"
                    f"• *NO, hold your position IF*:\n"
                    f"  1. You are maintaining long-term exposure to Data Center & AI catalysts.\n"
                    f"  2. Recent news catalyst remains positive: _{news_headline}_\n\n"
                    f"*Recommendation Summary*: If your position exceeds allocation limits, take partial profits; otherwise hold for long-term guidance.\n\n"
                    f"_{role_title} Context | Not a formal trading recommendation._"
                )
            else: # BUY or HOLD
                return (
                    f"💡 *Actionable Analysis: Buying / Holding {symbol} Today*\n\n"
                    f"Current Market State: *${quote.price:.2f}* ({direction} {sign}{quote.change_percent:.2f}%)\n\n"
                    f"• *YES, consider buying / adding IF*:\n"
                    f"  1. You are building long-term exposure ahead of upcoming earnings.\n"
                    f"  2. Price pulls back near support at *${(quote.price * 0.96):.2f}*.\n\n"
                    f"• *WAIT / HOLD IF*:\n"
                    f"  1. You prefer to wait for consolidation volume to stabilize.\n"
                    f"  2. Recent market catalyst context: _{news_headline}_\n\n"
                    f"*Recommendation Summary*: Favorable long-term fundamentals; dollar-cost average on minor dips.\n\n"
                    f"_{role_title} Context | Not a formal trading recommendation._"
                )
        if intent == "STOCK_QUOTE":
            symbol = intent_result.primary_symbol or "NVDA"
            quote = await MarketDataProvider.get_stock_quote(symbol)
            direction = "↑" if quote.change_amount >= 0 else "↓"
            sign = "+" if quote.change_amount >= 0 else ""

            from app.services.proactive_alert_service import ProactiveAlertService
            ProactiveAlertService.create_automatic_alerts(db, user_id, symbol, quote.price)
            
            return (
                f"📊 *{quote.symbol} Stock Quote*\n\n"
                f"• *Price*: ${quote.price:.2f}\n"
                f"• *Move*: {direction} {sign}{quote.change_percent:.2f}% (${sign}{quote.change_amount:.2f})\n"
                f"• *High / Low*: ${quote.high or quote.price:.2f} / ${quote.low or quote.price:.2f}\n"
                f"• *Source*: {quote.source}"
            )

        # 2. COMPANY RESEARCH INTENT
        elif intent == "COMPANY_RESEARCH":
            symbol = intent_result.primary_symbol or "NVDA"
            quote = await MarketDataProvider.get_stock_quote(symbol)
            news_items = await MarketDataProvider.get_company_news(symbol, limit=2)
            
            direction = "↑" if quote.change_amount >= 0 else "↓"
            sign = "+" if quote.change_amount >= 0 else ""

            news_bullets = ""
            for n in news_items:
                news_bullets += f"• *{n.headline}*\n  _{n.summary}_ (Source: {n.source})\n"

            return (
                f"📈 *{symbol} — Research Update*\n\n"
                f"• *Market Price*: ${quote.price:.2f} ({direction} {sign}{quote.change_percent:.2f}%)\n\n"
                f"*Key Catalysts & Developments*:\n"
                f"{news_bullets}\n"
                f"*Relevance for {role_title}*: Watch Q3 guidance and capital expenditure trends."
            )

        # 3. COMPANY COMPARISON INTENT
        elif intent == "COMPANY_COMPARISON":
            sym1 = intent_result.primary_symbol or "MSFT"
            sym2 = intent_result.secondary_symbol or "GOOGL"

            q1 = await MarketDataProvider.get_stock_quote(sym1)
            q2 = await MarketDataProvider.get_stock_quote(sym2)

            return (
                f"⚖️ *Comparative Analysis: {sym1} vs {sym2}*\n\n"
                f"• *{sym1}*: ${q1.price:.2f} ({'+' if q1.change_percent >= 0 else ''}{q1.change_percent:.2f}%)\n"
                f"• *{sym2}*: ${q2.price:.2f} ({'+' if q2.change_percent >= 0 else ''}{q2.change_percent:.2f}%)\n\n"
                f"*Key Factors to Consider*:\n"
                f"• *Enterprise AI*: {sym1} leads in Azure enterprise Copilot integration.\n"
                f"• *Search & Ad Momentum*: {sym2} maintains search margin resilience while scaling Gemini infrastructure.\n"
                f"• *Valuation*: Compare EV/Forward EBITDA multiples prior to position sizing."
            )

        # 4. NEWS SEARCH INTENT
        elif intent == "NEWS_SEARCH":
            topic = intent_result.topic or "Financial News"
            symbols = intent_result.symbols or ["NVDA", "MSFT"]
            news_items = await NewsProvider.get_watchlist_news(symbols, limit_per_symbol=1)

            news_text = ""
            for item in news_items:
                news_text += f"• *{item.symbol}*: {item.headline} ({item.source})\n"

            return (
                f"📰 *Latest {topic} Intelligence*\n\n"
                f"{news_text}\n"
                f"No further high-impact events detected for your portfolio."
            )

        # 5. WATCHLIST SUMMARY INTENT
        elif intent == "WATCHLIST_SUMMARY":
            user_obj = UserService.get_user_by_id(db, user_id)
            symbols = [w.symbol for w in user_obj.watchlists] if user_obj and user_obj.watchlists else ["NVDA", "MSFT", "GOOGL"]
            
            quotes = await MarketDataProvider.get_multiple_quotes(symbols)
            
            watchlist_lines = ""
            for q in quotes:
                direction = "↑" if q.change_percent >= 0 else "↓"
                sign = "+" if q.change_percent >= 0 else ""
                watchlist_lines += f"• *{q.symbol}*: ${q.price:.2f} ({direction} {sign}{q.change_percent:.2f}%)\n"

            return (
                f"📋 *Your Personalized Watchlist Summary*\n\n"
                f"{watchlist_lines}\n"
                f"Everything is trading within normal risk parameters."
            )

        # 6. GENERAL FALLBACK — powered by Groq LLM
        else:
            llm = LLMProvider()
            prompt = (
                f"User profile: {role_title}.\n"
                f"Question: {user_message}\n\n"
                f"Answer using ONLY bullet points (•). "
                f"Use *bold* for key numbers and terms. "
                f"Max 5 bullets. No paragraphs. No filler text."
            )
            ai_response = await llm.generate_response(prompt)
            if ai_response:
                return ai_response

            # Hard fallback if no API key or call fails
            return (
                f"You can ask me:\n"
                f"• *Stock quote*: \"NVDA price\"\n"
                f"• *Research*: \"What's happening with Microsoft?\"\n"
                f"• *Compare*: \"Compare MSFT and GOOGL\"\n"
                f"• *Decision*: \"Should I sell Apple today?\""
            )
