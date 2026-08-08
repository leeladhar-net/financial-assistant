import re
from typing import Optional, List
from app.schemas.onboarding import ExtractedProfileData
from app.core.logging import logger

class ProfileExtractorService:
    @staticmethod
    def extract_profile_info(text: str, current_state: Optional[str] = None) -> ExtractedProfileData:
        """
        Parses text for profile fields. Supports multi-field extraction from single text messages.
        Rule-based parsing ensures reliable operation in DEMO_MODE without external API calls.
        """
        extracted = ExtractedProfileData()
        if not text:
            return extracted

        text_lower = text.lower()

        # 1. Extract Role
        role_map = {
            "equity research": "equity_research",
            "equity analyst": "equity_research",
            "research analyst": "equity_research",
            "portfolio manager": "portfolio_manager",
            "hedge fund": "hedge_fund_analyst",
            "investment banker": "investment_banker",
            "investment banking": "investment_banker",
            "venture capital": "venture_capitalist",
            "venture capitalist": "venture_capitalist",
            "financial advisor": "financial_advisor",
            "wealth manager": "wealth_manager",
            "risk manager": "risk_manager",
            "trader": "trader",
            "cfo": "cfo",
            "analyst": "equity_research",
            "investor": "investor",
        }
        for keyword, role_val in role_map.items():
            if keyword in text_lower:
                extracted.role = role_val
                break

        if not extracted.role and current_state == "ASK_ROLE":
            # Fallback for short direct role answers like "Analyst" or "PM"
            if len(text.strip().split()) <= 4:
                extracted.role = text.strip()

        # 2. Extract Markets
        markets_found = []
        market_keywords = {
            "us": "US",
            "usa": "US",
            "united states": "US",
            "india": "India",
            "indian": "India",
            "europe": "Europe",
            "european": "Europe",
            "uk": "UK",
            "asia": "Asia",
            "asian": "Asia",
            "global": "Global",
            "tech": "Technology",
            "technology": "Technology",
            "crypto": "Crypto",
            "forex": "Forex",
            "commodities": "Commodities",
        }
        for kw, val in market_keywords.items():
            # Match word boundaries or substring in context
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                if val not in markets_found:
                    markets_found.append(val)
        if markets_found:
            extracted.markets = markets_found
        elif current_state == "ASK_MARKETS":
            # Direct response fallback for markets
            extracted.markets = [m.strip() for m in text.split(",") if m.strip()]

        # 3. Extract Watchlist Tickers / Companies
        watchlist_symbols = []
        # Pattern to match capitalized tickers e.g. NVDA, MSFT, GOOGL, TCS, AAPL
        potential_tickers = re.findall(r'\b[A-Z]{2,6}\b', text)
        stop_words = {
            "AND", "THE", "FOR", "INC", "CORP", "LTD", "PLC", "USA", "PM", "AM", "AI", "MA",
            "US", "UK", "EU", "IN", "APAC", "EMEA", "LATAM", "GLOBAL"
        }
        for t in potential_tickers:
            if t not in stop_words:
                watchlist_symbols.append(t)

        # Common company name extractions
        company_map = {
            "nvidia": "NVDA",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "apple": "AAPL",
            "amazon": "AMZN",
            "tesla": "TSLA",
            "meta": "META",
            "reliance": "RELIANCE",
            "tcs": "TCS",
            "hdfc": "HDFC",
            "infosys": "INFY",
        }
        for comp, sym in company_map.items():
            if comp in text_lower and sym not in watchlist_symbols:
                watchlist_symbols.append(sym)

        if watchlist_symbols:
            extracted.watchlist = watchlist_symbols
        elif current_state == "ASK_WATCHLIST":
            # If user replied with plain text comma separated list
            extracted.watchlist = [s.strip().upper() for s in text.replace("and", ",").split(",") if s.strip()]

        # 4. Extract Interests / Topics
        interests_found = []
        interest_keywords = {
            "ai": "AI",
            "artificial intelligence": "AI",
            "earnings": "Earnings",
            "m&a": "M&A",
            "mergers": "M&A",
            "acquisitions": "M&A",
            "interest rates": "Interest Rates",
            "fed": "Interest Rates",
            "inflation": "Inflation",
            "macro": "Macroeconomics",
            "esg": "ESG",
            "biotech": "Biotech",
            "semiconductors": "Semiconductors",
            "banking": "Banking",
        }
        for kw, topic in interest_keywords.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                if topic not in interests_found:
                    interests_found.append(topic)
        if interests_found:
            extracted.interests = interests_found
        elif current_state == "ASK_INTERESTS":
            extracted.interests = [i.strip() for i in text.replace("and", ",").split(",") if i.strip()]

        # 5. Extract Briefing Time
        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b', text)
        if time_match:
            extracted.briefing_time = time_match.group(1).upper()
        elif "morning" in text_lower:
            extracted.briefing_time = "8:00 AM"
        elif "evening" in text_lower:
            extracted.briefing_time = "6:00 PM"
        elif current_state == "ASK_BRIEFING_TIME":
            extracted.briefing_time = text.strip()

        # 6. Extract Response Style
        if "quick" in text_lower or "brief" in text_lower or "short" in text_lower:
            extracted.response_style = "quick"
        elif "detailed" in text_lower or "deep" in text_lower or "thorough" in text_lower:
            extracted.response_style = "detailed"
        elif "standard" in text_lower or "normal" in text_lower or "regular" in text_lower:
            extracted.response_style = "standard"
        elif current_state == "ASK_RESPONSE_STYLE":
            extracted.response_style = "standard"

        logger.debug(f"Extracted profile info from text: {extracted}")
        return extracted
