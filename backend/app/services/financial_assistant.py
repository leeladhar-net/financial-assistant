from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import UserService
from app.services.memory_service import MemoryService
from app.core.logging import logger

class FinancialAssistantService:
    """
    Core Financial Assistant Engine.
    Handles user messages post-onboarding and provides stubs for Part 2 and Part 3 capabilities.
    """

    @staticmethod
    def handle_message(
        db: Session,
        user: User,
        conversation_id: int,
        user_message_text: str
    ) -> str:
        logger.info(f"FinancialAssistantService handling message for user_id={user.id}")

        pref = UserService.get_user_preferences(db, user.id)
        watchlists = [w.symbol for w in user.watchlists]
        interests = [i.topic for i in user.interests]

        text_lower = user_message_text.strip().lower()

        # Greetings or simple check-ins
        if text_lower in ["hello", "hi", "hey", "help", "start"]:
            wl_str = ", ".join(watchlists) if watchlists else "your watchlist"
            return (
                f"I'm ready! I'm actively monitoring {wl_str} and key topics like {', '.join(interests) if interests else 'markets'}.\n\n"
                "You can ask me about companies, market summaries, financial news, or general research."
            )

        # Basic query acknowledging user's personalized watchlist / role
        return (
            f"Received: \"{user_message_text}\"\n\n"
            f"[Demomode Active] I am currently operating in Part 1 mode. "
            f"I have noted your request under your {pref.role.replace('_', ' ').title() if pref and pref.role else 'user'} profile. "
            f"Real-time financial market data and deep research agents will be unlocked in Part 2!"
        )

    # ==========================================
    # Stubs prepared for Part 2 and Part 3
    # ==========================================

    @staticmethod
    def research_company(symbol: str) -> Dict[str, Any]:
        """Part 2 Stub: Detailed company financial research."""
        return {"symbol": symbol, "status": "stub_pending_part2"}

    @staticmethod
    def market_summary(market: str) -> Dict[str, Any]:
        """Part 2 Stub: Regional / sector market summary."""
        return {"market": market, "status": "stub_pending_part2"}

    @staticmethod
    def generate_daily_briefing(user_id: int) -> Dict[str, Any]:
        """Part 2 Stub: Personalized daily briefing generator."""
        return {"user_id": user_id, "status": "stub_pending_part2"}

    @staticmethod
    def analyze_document(document_id: str) -> Dict[str, Any]:
        """Part 3 Stub: Financial document analysis (10-K, 10-Q, transcript)."""
        return {"document_id": document_id, "status": "stub_pending_part3"}

    @staticmethod
    def analyze_sheet(sheet_id: str) -> Dict[str, Any]:
        """Part 3 Stub: Google Sheets financial model analysis."""
        return {"sheet_id": sheet_id, "status": "stub_pending_part3"}
