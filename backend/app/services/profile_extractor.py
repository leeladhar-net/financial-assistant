import json
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.schemas.onboarding import ExtractedProfileData
from app.integrations.llm_provider import LLMProvider
from app.core.config import settings
from app.core.logging import logger

PARSING_SYSTEM_PROMPT = """You are a highly intelligent natural language parser for a personal financial advisor onboarding chat.
Analyze the user's latest response in the context of the recent conversation history and the current onboarding step. Clean up any typos, translate names to stock tickers, and output a clean JSON object.

Onboarding Steps & Validation Rules:
1. ASK_ROLE: User specifies their investment role (e.g. "equity researcher", "retail investor").
   - Valid: Must describe an investment style or job. A greeting like "ji" or gibberish like "ok" is INVALID.
   - Standardize to a professional title (e.g. "PM" -> "Portfolio Manager").
2. ASK_MARKETS: User specifies regions or sectors (e.g. "us and india", "tech").
   - Valid: Plausible countries, regions, or sectors.
   - Standardize to a list of clean strings.
3. ASK_WATCHLIST: User specifies companies or stock tickers.
   - Valid: Must list company names or tickers.
   - Translate names to stock symbols (e.g. "apple" -> "AAPL", "adani" -> "ADANIENT", "tata steel" -> "TATASTEEL").
4. ASK_INTERESTS: User specifies topics they care about (e.g. "infaltions", "market crash").
   - Valid: Plausible finance/market themes. *Short answers like "ai" or "stocks" are 100% VALID.*
   - Correct spelling/typos and standardize (e.g. "infaltions" -> ["Inflation"]).
5. ASK_BRIEFING_TIME: User specifies update time.
   - Valid: A time or time range (e.g. "8 AM").
6. ASK_RESPONSE_STYLE: User specifies response style (quick, standard, detailed).
   - Valid: Expresses preference for detail level.

CRITICAL INSTRUCTIONS FOR USER ANSWERS LIKE 'yes', 'no', 'sure', 'yes like that', OR IF THE USER IS UNSURE:
- If the user says 'yes', 'sure', 'yes like that', or agrees with the assistant's previous suggestion (found in the history), look at the assistant's previous message. Extract the topics/options the assistant suggested as the user's choices.
  For example, if the assistant suggested "AI trends or AI stocks" and the user replied "yes like that", set interests to ["AI Trends", "AI Stocks"] and set is_valid to true.
- If the user says 'no', 'i don't know', 'whatever', or seems confused/unsure, OR if they have failed validation previously, DO NOT mark it as invalid. Instead, set is_valid to true and assign a sensible default value so the user does not get stuck in a loop:
  - Default Role: "Retail Investor"
  - Default Markets: ["Global Markets"]
  - Default Watchlist: ["AAPL", "NVDA"]
  - Default Interests: ["General Market News", "Technology Trends"]
  - Default Briefing Time: "8:00 AM"
  - Default Response Style: "standard"

Your JSON output structure must be:
{
  "is_valid": true/false,
  "clarification": "Polite, warm, human-like clarification response if is_valid is false, otherwise empty string.",
  "role": "string or null",
  "markets": ["string"] or null,
  "watchlist": ["string"] or null,
  "interests": ["string"] or null,
  "briefing_time": "string or null",
  "response_style": "string or null"
}
Return raw JSON only."""

class ProfileExtractorService:
    @staticmethod
    async def extract_profile_info_llm(text: str, current_state: str, history: List[str] = []) -> Dict[str, Any]:
        """
        Uses Groq LLM to parse and validate onboarding responses in a friendly, conversational manner.
        Passes conversation history to allow resolving context (e.g. 'yes like that', 'sure').
        """
        if current_state == "NEW":
            return ProfileExtractorService.extract_profile_info_fallback(text, current_state)

        if not text or not settings.LLM_API_KEY:
            return ProfileExtractorService.extract_profile_info_fallback(text, current_state)

        history_context = "\n".join(history[-4:]) if history else "No history"
        prompt = (
            f"Recent Conversation History:\n{history_context}\n\n"
            f"Current Step: {current_state}\n"
            f"User Latest Response: \"{text}\"\n\n"
            f"Parse this and output the JSON object."
        )
        
        try:
            llm = LLMProvider()
            response_text = await llm.generate_response(prompt, system_prompt=PARSING_SYSTEM_PROMPT, fast=True)
            
            if response_text:
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```"):
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_text, re.DOTALL)
                    if match:
                        cleaned_text = match.group(1)
                
                data = json.loads(cleaned_text)
                logger.info(f"LLM Onboarding Extraction: state={current_state}, parsed={data}")
                return data
        except Exception as e:
            logger.error(f"Failed to parse onboarding response with LLM: {e}")

        return ProfileExtractorService.extract_profile_info_fallback(text, current_state)

    @staticmethod
    def extract_profile_info_fallback(text: str, current_state: str) -> Dict[str, Any]:
        """Rule-based parsing that matches the original functionality to ensure full test compatibility."""
        text_lower = text.lower()
        extracted = {
            "is_valid": True,
            "clarification": "",
            "role": None, "markets": None, "watchlist": None, "interests": None, "briefing_time": None, "response_style": None
        }

        # 1. Extract Role
        role_map = {
            "equity research": "equity_research",
            "equity analyst": "equity_research",
            "research analyst": "equity_research",
            "portfolio manager": "portfolio_manager",
            "hedge fund": "hedge_fund_analyst",
            "investment banker": "investment_banker",
            "trader": "trader",
            "investor": "investor",
        }
        for kw, val in role_map.items():
            if kw in text_lower:
                extracted["role"] = val
                break
        
        if not extracted["role"] and current_state == "ASK_ROLE":
            if len(text.strip().split()) <= 4:
                extracted["role"] = text.strip()

        # 2. Extract Markets
        markets_found = []
        market_keywords = {
            "us": "US", "usa": "US", "united states": "US",
            "india": "India", "indian": "India",
            "europe": "Europe", "european": "Europe",
            "global": "Global", "tech": "Technology", "technology": "Technology",
        }
        for kw, val in market_keywords.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                if val not in markets_found:
                    markets_found.append(val)
        if markets_found:
            extracted["markets"] = markets_found
        elif current_state == "ASK_MARKETS":
            extracted["markets"] = [m.strip() for m in text.split(",") if m.strip()]

        # 3. Extract Watchlist
        watchlist_symbols = []
        potential_tickers = re.findall(r'\b[A-Z]{2,6}\b', text)
        stop_words = {"AND", "THE", "FOR", "INC", "CORP", "LTD", "PLC", "USA", "PM", "AM", "AI", "US", "UK", "IN"}
        for t in potential_tickers:
            if t not in stop_words:
                watchlist_symbols.append(t)

        company_map = {
            "nvidia": "NVDA", "microsoft": "MSFT", "google": "GOOGL",
            "apple": "AAPL", "amazon": "AMZN", "tesla": "TSLA",
            "reliance": "RELIANCE", "tcs": "TCS",
        }
        for comp, sym in company_map.items():
            if comp in text_lower and sym not in watchlist_symbols:
                watchlist_symbols.append(sym)

        if watchlist_symbols:
            extracted["watchlist"] = watchlist_symbols
        elif current_state == "ASK_WATCHLIST":
            extracted["watchlist"] = [s.strip().upper() for s in text.replace("and", ",").split(",") if s.strip()]

        # 4. Extract Interests
        interests_found = []
        interest_keywords = {
            "ai": "AI", "artificial intelligence": "AI",
            "earnings": "Earnings", "m&a": "M&A", "mergers": "M&A",
            "interest rates": "Interest Rates", "fed": "Interest Rates",
            "inflation": "Inflation", "macro": "Macroeconomics",
        }
        for kw, topic in interest_keywords.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                if topic not in interests_found:
                    interests_found.append(topic)
        if interests_found:
            extracted["interests"] = interests_found
        elif current_state == "ASK_INTERESTS":
            extracted["interests"] = [i.strip() for i in text.replace("and", ",").split(",") if i.strip()]

        # 5. Extract Briefing Time
        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b', text)
        if time_match:
            extracted["briefing_time"] = time_match.group(1).upper()
        elif "morning" in text_lower:
            extracted["briefing_time"] = "8:00 AM"
        elif current_state == "ASK_BRIEFING_TIME":
            extracted["briefing_time"] = text.strip()

        # 6. Extract Response Style
        if "quick" in text_lower or "brief" in text_lower or "short" in text_lower:
            extracted["response_style"] = "quick"
        elif "detailed" in text_lower or "deep" in text_lower or "thorough" in text_lower:
            extracted["response_style"] = "detailed"
        elif "standard" in text_lower or "normal" in text_lower:
            extracted["response_style"] = "standard"
        elif current_state == "ASK_RESPONSE_STYLE":
            extracted["response_style"] = "standard"

        return extracted

    @staticmethod
    def extract_profile_info(text: str, current_state: Optional[str] = None) -> ExtractedProfileData:
        parsed = ProfileExtractorService.extract_profile_info_fallback(text, current_state or "")
        return ExtractedProfileData(
            role=parsed.get("role"),
            markets=parsed.get("markets"),
            watchlist=parsed.get("watchlist"),
            interests=parsed.get("interests"),
            briefing_time=parsed.get("briefing_time"),
            response_style=parsed.get("response_style")
        )
