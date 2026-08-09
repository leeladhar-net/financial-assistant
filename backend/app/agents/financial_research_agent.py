import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.schemas.financial import IntentResult, StockQuote, CompanyNews
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_provider import NewsProvider
from app.integrations.llm_provider import LLMProvider
from app.services.user_service import UserService
from app.core.logging import logger

ADVISOR_SYSTEM_PROMPT = """You are a warm, elite personal financial advisor responding via Telegram.
Your goal is to deliver live market data and news to your client in a highly conversational, friendly, and natural manner.

Formatting Rules:
1. Always start with a friendly, natural opening sentence introducing the data (e.g. "I checked the markets for you, and here is how Nvidia is looking today:" or "Apple has some interesting developments today:").
2. Present the key stock prices, changes, or comparisons using clean, well-spaced bullet points (•) with *bold* headers and values.
3. If news headlines are present, summarize them in 1 line per bullet point.
4. Conclude with a helpful, warm summary sentence and a natural, interactive follow-up question (e.g., "Would you like me to analyze their recent earnings report?", "Should we look into their valuation?").
5. Keep response suitables for quick mobile reading (under 150 words total).
6. Avoid raw robotic labels, disclaimers, or system jargon unless absolutely necessary.
7. When generating responses in foreign languages (like Hindi or Telugu), write in their native script but naturally mix in English financial keywords (like stock, price, range, news, EPS, high, low, bullish, bearish) if it sounds more conversational, matching real-world Hinglish/Telglish conversational speech. Ticker symbols (e.g. AAPL, NVDA, RELIANCE) must remain in the English alphabet. Keep markdown styling intact.
"""

class FinancialResearchAgent:
    """
    Coordinates live data retrieval and generates friendly, conversational financial
    advisory responses via Groq LLM.
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
        role_title = pref.role.replace("_", " ").title() if pref and pref.role else "Retail Investor"
        intent = intent_result.intent

        # 1. Gather all necessary raw live data depending on intent
        raw_data_summary = {}

        if intent in ("DECISION_ADVICE", "STOCK_QUOTE", "COMPANY_RESEARCH"):
            symbol = intent_result.primary_symbol or "NVDA"
            quote = await MarketDataProvider.get_stock_quote(symbol)
            news_items = await MarketDataProvider.get_company_news(symbol, limit=3)
            
            # Setup automated alert triggers in background
            from app.services.proactive_alert_service import ProactiveAlertService
            ProactiveAlertService.create_automatic_alerts(db, user_id, symbol, quote.price)

            raw_data_summary = {
                "symbol": symbol,
                "price": quote.price,
                "change_percent": quote.change_percent,
                "change_amount": quote.change_amount,
                "high": quote.high,
                "low": quote.low,
                "open": quote.open,
                "prev_close": quote.prev_close,
                "source": quote.source,
                "news": [{"headline": n.headline, "source": n.source} for n in news_items]
            }

        elif intent == "COMPANY_COMPARISON":
            sym1 = intent_result.primary_symbol or "MSFT"
            sym2 = intent_result.secondary_symbol or "GOOGL"
            q1 = await MarketDataProvider.get_stock_quote(sym1)
            q2 = await MarketDataProvider.get_stock_quote(sym2)
            
            raw_data_summary = {
                "compare_mode": True,
                "stock1": {"symbol": sym1, "price": q1.price, "change_percent": q1.change_percent},
                "stock2": {"symbol": sym2, "price": q2.price, "change_percent": q2.change_percent}
            }

        elif intent == "NEWS_SEARCH":
            topic = intent_result.topic or "general market news"
            news_items = await NewsProvider.search_topic_news(topic, limit=4)
            raw_data_summary = {
                "news_search_topic": topic,
                "news": [{"headline": n.headline, "source": n.source} for n in news_items]
            }

        elif intent == "WATCHLIST_SUMMARY":
            user_obj = UserService.get_user_by_id(db, user_id)
            symbols = [w.symbol for w in user_obj.watchlists] if user_obj and user_obj.watchlists else ["NVDA", "AAPL"]
            quotes = await MarketDataProvider.get_multiple_quotes(symbols)
            
            raw_data_summary = {
                "watchlist_summary": True,
                "stocks": [{"symbol": q.symbol, "price": q.price, "change_percent": q.change_percent} for q in quotes]
            }

        # 2. Use LLM to format the retrieved raw data into a warm conversational advisor response
        llm = LLMProvider()
        lang = pref.preferred_language if pref and pref.preferred_language else "English"
        
        prompt = (
            f"User Profile Role: {role_title}\n"
            f"User Message: \"{user_message}\"\n"
            f"Intent: {intent}\n"
            f"Target Output Language: {lang}\n"
            f"Raw Financial Data Context:\n{json.dumps(raw_data_summary, indent=2)}\n\n"
            f"Generate the conversational, personal assistant response now. You MUST write the response ENTIRELY in {lang}."
        )

        try:
            ai_response = await llm.generate_response(
                prompt, 
                system_prompt=ADVISOR_SYSTEM_PROMPT + f"\n\n7. You MUST write the response ENTIRELY in {lang}. Do not mix languages.", 
                fast=False
            )
            if ai_response:
                return ai_response
        except Exception as e:
            logger.error(f"Failed to generate conversational response via LLM: {e}")

        # Static fallback if LLM fails
        fallback_msg = FinancialResearchAgent._fallback_response(intent, raw_data_summary, role_title)
        from app.services.onboarding_service import OnboardingService
        return await OnboardingService.translate_text(fallback_msg, lang)

    @staticmethod
    def _fallback_response(intent: str, data: dict, role_title: str) -> str:
        """Provide a clean, styled static fallback response if the LLM is down."""
        if intent == "STOCK_QUOTE" and "symbol" in data:
            return (
                f"I checked the price of *{data['symbol']}* for you:\n\n"
                f"• *Current Price*: ${data['price']:.2f}\n"
                f"• *Change*: {data['change_percent']:.2f}%\n"
                f"• *Range*: ${data['low']} - ${data['high']}\n\n"
                f"Would you like me to fetch the latest news on this company?"
            )
        return (
            "I've fetched the latest financial details for you, but I'm currently running in low-power fallback mode. "
            "How else can I assist you with your research today?"
        )
