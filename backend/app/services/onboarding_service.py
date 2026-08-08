from typing import Tuple, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import UserService
from app.services.profile_extractor import ProfileExtractorService
from app.services.memory_service import MemoryService
from app.core.logging import logger

class OnboardingService:
    @staticmethod
    def process_onboarding_message(db: Session, user: User, message_text: str) -> str:
        """
        Processes incoming onboarding text message, extracts profile fields, updates state,
        and returns the next natural response.
        """
        current_state = user.onboarding_state or "NEW"
        logger.info(f"Processing onboarding for user_id={user.id}, state={current_state}")

        # Extract profile information from current message
        extracted = ProfileExtractorService.extract_profile_info(message_text, current_state)

        # Update DB records with extracted attributes
        if extracted.role:
            UserService.update_user_preferences(db, user.id, role=extracted.role)
            MemoryService.save_memory(db, user.id, "role", extracted.role, memory_type="profile")

        if extracted.markets:
            UserService.update_user_preferences(db, user.id, markets=extracted.markets)
            MemoryService.save_memory(db, user.id, "markets", ", ".join(extracted.markets), memory_type="profile")

        if extracted.watchlist:
            UserService.add_watchlist_symbols(db, user.id, extracted.watchlist)
            MemoryService.save_memory(db, user.id, "watchlist", ", ".join(extracted.watchlist), memory_type="profile")

        if extracted.interests:
            UserService.add_user_interests(db, user.id, extracted.interests)
            MemoryService.save_memory(db, user.id, "interests", ", ".join(extracted.interests), memory_type="profile")

        if extracted.briefing_time:
            UserService.update_user_preferences(db, user.id, briefing_time=extracted.briefing_time)
            MemoryService.save_memory(db, user.id, "briefing_time", extracted.briefing_time, memory_type="profile")

        if extracted.response_style:
            UserService.update_user_preferences(db, user.id, response_style=extracted.response_style)
            MemoryService.save_memory(db, user.id, "response_style", extracted.response_style, memory_type="profile")

        # Determine next missing requirement
        pref = UserService.get_user_preferences(db, user.id)
        watchlists = user.watchlists
        interests = user.interests

        # If user is brand new (NEW state) and hasn't provided role yet
        if current_state == "NEW" and not pref.role:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            return (
                "Hi! I'm your financial intelligence assistant.\n\n"
                "I'll help you track the companies, markets, and financial topics that matter to you.\n\n"
                "First — what best describes your role? (e.g. equity research analyst, portfolio manager, trader, investor)"
            )

        # Check missing fields sequentially
        if not pref.role:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            return "Could you clarify what best describes your role?"

        if not pref.markets or len(pref.markets) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_MARKETS")
            return "What markets or regions do you mainly follow? (e.g. US, India, Europe, Global Technology)"

        if not watchlists or len(watchlists) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_WATCHLIST")
            return "Which key companies or ticker symbols should I monitor for you? (e.g. NVDA, MSFT, GOOGL, RELIANCE)"

        if not interests or len(interests) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_INTERESTS")
            return "Which topics matter most to your research? (e.g. AI, Earnings, M&A, Interest Rates, Inflation)"

        if not pref.briefing_time:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_BRIEFING_TIME")
            return "When would you prefer to receive your daily financial briefing? (e.g. 8:00 AM, 9:00 AM)"

        if not pref.response_style:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_RESPONSE_STYLE")
            return "Do you prefer quick, standard, or detailed updates?"

        # All fields are complete! Complete onboarding.
        UserService.update_user_onboarding_status(db, user.id, completed=True, state="COMPLETED")

        symbols_str = ", ".join([w.symbol for w in watchlists])
        topics_str = ", ".join([i.topic for i in interests])
        markets_str = ", ".join(pref.markets) if isinstance(pref.markets, list) else str(pref.markets)

        return (
            f"You're all set! Here is your personalized profile:\n\n"
            f"• Role: {pref.role.replace('_', ' ').title()}\n"
            f"• Markets: {markets_str}\n"
            f"• Watchlist: {symbols_str}\n"
            f"• Interests: {topics_str}\n"
            f"• Daily Briefing: {pref.briefing_time}\n"
            f"• Response Style: {pref.response_style.capitalize()}\n\n"
            "I'll focus on the companies, markets, and topics you selected. "
            "You can now ask me about any company, market update, or financial topic!"
        )
