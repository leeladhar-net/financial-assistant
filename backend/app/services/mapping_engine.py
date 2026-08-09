import re
import httpx
from typing import Optional, Dict, Any, List
from app.schemas.instrument import CanonicalInstrument
from app.integrations.llm_provider import LLMProvider
from app.core.config import settings
from app.core.logging import logger

class CompanyMappingEngine:
    """
    Structured Company Mapping Engine to resolve company name queries to Canonical Instruments.
    """

    # Layer 1: Common Aliases & Mappings
    ALIASES: Dict[str, Dict[str, str]] = {
        "zomato": {
            "company_name": "Eternal Limited",
            "exchange": "NSE",
            "symbol": "ETERNAL",
            "ticker": "ETERNAL.NS"
        },
        "tata motors": {
            "company_name": "Tata Motors Limited (Commercial)",
            "exchange": "NSE",
            "symbol": "TMCV",
            "ticker": "TMCV.NS"
        },
        "tata steel": {
            "company_name": "Tata Steel Limited",
            "exchange": "NSE",
            "symbol": "TATASTEEL",
            "ticker": "TATASTEEL.NS"
        },
        "reliance": {
            "company_name": "Reliance Industries Limited",
            "exchange": "NSE",
            "symbol": "RELIANCE",
            "ticker": "RELIANCE.NS"
        },
        "tcs": {
            "company_name": "Tata Consultancy Services Limited",
            "exchange": "NSE",
            "symbol": "TCS",
            "ticker": "TCS.NS"
        },
        "hdfc": {
            "company_name": "HDFC Bank Limited",
            "exchange": "NSE",
            "symbol": "HDFCBANK",
            "ticker": "HDFCBANK.NS"
        },
        "hdfc bank": {
            "company_name": "HDFC Bank Limited",
            "exchange": "NSE",
            "symbol": "HDFCBANK",
            "ticker": "HDFCBANK.NS"
        },
        "wipro": {
            "company_name": "Wipro Limited",
            "exchange": "NSE",
            "symbol": "WIPRO",
            "ticker": "WIPRO.NS"
        },
        "infosys": {
            "company_name": "Infosys Limited",
            "exchange": "NSE",
            "symbol": "INFY",
            "ticker": "INFY.NS"
        },
        "sbi": {
            "company_name": "State Bank of India",
            "exchange": "NSE",
            "symbol": "SBIN",
            "ticker": "SBIN.NS"
        },
        "state bank": {
            "company_name": "State Bank of India",
            "exchange": "NSE",
            "symbol": "SBIN",
            "ticker": "SBIN.NS"
        },
        "icici": {
            "company_name": "ICICI Bank Limited",
            "exchange": "NSE",
            "symbol": "ICICIBANK",
            "ticker": "ICICIBANK.NS"
        },
        "adani": {
            "company_name": "Adani Enterprises Limited",
            "exchange": "NSE",
            "symbol": "ADANIENT",
            "ticker": "ADANIENT.NS"
        },
        "nvidia": {
            "company_name": "NVIDIA Corporation",
            "exchange": "NASDAQ",
            "symbol": "NVDA",
            "ticker": "NVDA"
        },
        "apple": {
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "symbol": "AAPL",
            "ticker": "AAPL"
        },
        "microsoft": {
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "symbol": "MSFT",
            "ticker": "MSFT"
        },
        "google": {
            "company_name": "Alphabet Inc.",
            "exchange": "NASDAQ",
            "symbol": "GOOGL",
            "ticker": "GOOGL"
        },
        "alphabet": {
            "company_name": "Alphabet Inc.",
            "exchange": "NASDAQ",
            "symbol": "GOOGL",
            "ticker": "GOOGL"
        },
        "amazon": {
            "company_name": "Amazon.com, Inc.",
            "exchange": "NASDAQ",
            "symbol": "AMZN",
            "ticker": "AMZN"
        },
        "tesla": {
            "company_name": "Tesla, Inc.",
            "exchange": "NASDAQ",
            "symbol": "TSLA",
            "ticker": "TSLA"
        },
        "meta": {
            "company_name": "Meta Platforms, Inc.",
            "exchange": "NASDAQ",
            "symbol": "META",
            "ticker": "META"
        },
        "netflix": {
            "company_name": "Netflix, Inc.",
            "exchange": "NASDAQ",
            "symbol": "NFLX",
            "ticker": "NFLX"
        },
        "intel": {
            "company_name": "Intel Corporation",
            "exchange": "NASDAQ",
            "symbol": "INTC",
            "ticker": "INTC"
        }
    }

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalizes company names to strip punctuation, extra spaces, and business suffixes.
        """
        # Clean text
        low = name.strip().lower()
        # Remove common corporate suffixes
        low = re.sub(r'\b(ltd|limited|inc|incorporated|corp|corporation|co|company|plc|pvt|private)\b', '', low)
        # Clean punctuation and compress spaces
        low = re.sub(r'[^\w\s]', '', low)
        return " ".join(low.split())

    @staticmethod
    async def _query_yahoo_search(query: str) -> Optional[CanonicalInstrument]:
        """
        Queries Yahoo Finance search endpoint to locate matching instruments (Layer 3).
        """
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"q": query}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    quotes = res.json().get("quotes", [])
                    if quotes:
                        # Find the first quote that has a symbol and name
                        for q in quotes:
                            symbol = q.get("symbol")
                            shortname = q.get("shortname") or q.get("longname") or symbol
                            exchange = q.get("exchange") or "UNKNOWN"
                            if symbol and shortname:
                                # Standardize exchange labels
                                if exchange in ("NSI", "NSE"):
                                    exchange_clean = "NSE"
                                elif exchange in ("BSE", "BO"):
                                    exchange_clean = "BSE"
                                else:
                                    exchange_clean = exchange
                                
                                # Standardize symbol display (remove exchange suffixes from base symbol)
                                base_symbol = symbol.split(".")[0].split(":")[0]
                                
                                logger.info(f"Yahoo Search Match: {shortname} ({symbol}) on {exchange_clean}")
                                return CanonicalInstrument(
                                    company_name=shortname,
                                    exchange=exchange_clean,
                                    symbol=base_symbol,
                                    ticker=symbol
                                )
        except Exception as e:
            logger.warning(f"Yahoo search lookup failed for query '{query}': {e}")
        return None

    @staticmethod
    async def _resolve_via_llm(query: str) -> Optional[CanonicalInstrument]:
        """
        Groq Semantic Resolver fallback (Layer 4).
        """
        if not settings.LLM_API_KEY:
            return None

        prompt = (
            f"Resolve the company name '{query}' to its standard stock market ticker. "
            f"Output a valid JSON matching this schema: "
            f'{{"company_name": "Official Company Name", "exchange": "NSE/BSE/NASDAQ/NYSE", "symbol": "TICKER", "ticker": "TICKER_WITH_SUFFIX"}} '
            f"Examples:\n"
            f"- Zomato -> {{\"company_name\": \"Eternal Limited\", \"exchange\": \"NSE\", \"symbol\": \"ETERNAL\", \"ticker\": \"ETERNAL.NS\"}}\n"
            f"- Tata Motors -> {{\"company_name\": \"Tata Motors Limited\", \"exchange\": \"NSE\", \"symbol\": \"TMCV\", \"ticker\": \"TMCV.NS\"}}\n"
            f"- Nvidia -> {{\"company_name\": \"NVIDIA Corporation\", \"exchange\": \"NASDAQ\", \"symbol\": \"NVDA\", \"ticker\": \"NVDA\"}}\n"
            f"Ensure to append '.NS' for Indian stocks. Do not include markdown blocks or extra text."
        )

        try:
            llm = LLMProvider()
            res = await llm.generate_response(prompt, system_prompt="You are a stock symbol mapping assistant. Output JSON only.", fast=True)
            if res:
                cleaned = res.strip()
                if cleaned.startswith("```"):
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
                    if match:
                        cleaned = match.group(1)
                
                import json
                data = json.loads(cleaned)
                logger.info(f"LLM Semantic Match: parsed={data}")
                return CanonicalInstrument(
                    company_name=data.get("company_name", query.title()),
                    exchange=data.get("exchange", "UNKNOWN"),
                    symbol=data.get("symbol", "").upper(),
                    ticker=data.get("ticker", "").upper()
                )
        except Exception as e:
            logger.warning(f"LLM semantic match failed: {e}")
        return None

    @classmethod
    async def resolve_instrument(cls, query: str) -> Optional[CanonicalInstrument]:
        """
        Main entry point. Resolves a company name or query to a CanonicalInstrument.
        """
        if not query:
            return None

        clean_query = query.strip()
        normalized = cls._normalize_name(clean_query)

        # Layer 1: Exact Alias check (original query)
        alias_match = cls.ALIASES.get(clean_query.lower())
        if alias_match:
            logger.info(f"Mapping Layer 1 (Exact Match): resolved '{clean_query}' to {alias_match['ticker']}")
            return CanonicalInstrument(**alias_match)

        # Layer 2: Normalized Alias check
        normalized_match = cls.ALIASES.get(normalized)
        if normalized_match:
            logger.info(f"Mapping Layer 2 (Normalized Match): resolved '{clean_query}' ('{normalized}') to {normalized_match['ticker']}")
            return CanonicalInstrument(**normalized_match)

        # Layer 3: Live Verification Search via Yahoo Finance search API
        live_match = await cls._query_yahoo_search(clean_query)
        if live_match:
            logger.info(f"Mapping Layer 3 (Live Search Match): resolved '{clean_query}' to {live_match.ticker}")
            return live_match

        # Layer 4: LLM Semantic Match fallback
        llm_match = await cls._resolve_via_llm(clean_query)
        if llm_match and llm_match.symbol:
            logger.info(f"Mapping Layer 4 (LLM Semantic Match): resolved '{clean_query}' to {llm_match.ticker}")
            return llm_match

        return None
