from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import UserService
from app.services.profile_extractor import ProfileExtractorService
from app.services.memory_service import MemoryService
from app.integrations.llm_provider import LLMProvider
from app.core.logging import logger

RECAP_SYSTEM_PROMPT = """You are a warm, elite personal financial advisor.
Based on the user's finalized preferences, write a friendly 3-sentence summary of their profile. 
Explain naturally *why* you selected these settings for them, and end with a conversational invitation to start.
Refer to the user as "you". Do not use bullet points or lists in your summary. Keep it warm and human-like."""

class OnboardingService:
    @staticmethod
    async def process_onboarding_message(db: Session, user: User, message_text: str, pre_parsed: Optional[Dict[str, Any]] = None) -> str:
        """
        Processes incoming onboarding text message, extracts profile fields, updates state,
        and returns the next natural response.
        """
        current_state = user.onboarding_state or "NEW"
        logger.info(f"Processing onboarding for user_id={user.id}, state={current_state}")

        if pre_parsed is not None:
            parsed = pre_parsed
        else:
            # Fetch conversation history to pass as context
            from app.services.conversation_service import ConversationService
            conv = ConversationService.get_or_create_active_conversation(db, user.id)
            recent_msgs = ConversationService.get_recent_messages(db, conv.id, limit=5)
            history = [f"{m.role.upper()}: {m.content}" for m in recent_msgs]

            # 1. Parse and validate the response using Groq LLM with history context
            parsed = await ProfileExtractorService.extract_profile_info_llm(message_text, current_state, history)
        
        # 2. Check validation
        if not parsed.get("is_valid", True):
            # If the user input was invalid/gibberish, return the LLM's clarification question
            clarification = parsed.get("clarification") or "Sorry, I didn't quite catch that. Could you clarify that for me?"
            return clarification

        # 3. Update DB records with extracted attributes
        if parsed.get("role"):
            UserService.update_user_preferences(db, user.id, role=parsed["role"])
            MemoryService.save_memory(db, user.id, "role", parsed["role"], memory_type="profile")

        if parsed.get("markets"):
            UserService.update_user_preferences(db, user.id, markets=parsed["markets"])
            MemoryService.save_memory(db, user.id, "markets", ", ".join(parsed["markets"]), memory_type="profile")

        if parsed.get("watchlist"):
            UserService.add_watchlist_symbols(db, user.id, parsed["watchlist"])
            MemoryService.save_memory(db, user.id, "watchlist", ", ".join(parsed["watchlist"]), memory_type="profile")

        if parsed.get("interests"):
            UserService.add_user_interests(db, user.id, parsed["interests"])
            MemoryService.save_memory(db, user.id, "interests", ", ".join(parsed["interests"]), memory_type="profile")

        if parsed.get("briefing_time"):
            UserService.update_user_preferences(db, user.id, briefing_time=parsed["briefing_time"])
            MemoryService.save_memory(db, user.id, "briefing_time", parsed["briefing_time"], memory_type="profile")

        if parsed.get("response_style"):
            UserService.update_user_preferences(db, user.id, response_style=parsed["response_style"])
            MemoryService.save_memory(db, user.id, "response_style", parsed["response_style"], memory_type="profile")

        # 4. Fetch updated profile state
        pref = UserService.get_user_preferences(db, user.id)
        watchlists = user.watchlists
        interests = user.interests

        # If brand new user and no info was parsed from the first message, ask the first question
        if current_state == "NEW" and not parsed.get("role"):
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            return (
                "Hi! I'm your personal financial advisor. 💼\n\n"
                "I'll help you track companies, global markets, and financial trends that align with your goals.\n\n"
                "To get started, what best describes your current investment role or background? (e.g. retail investor, student, day trader, analyst)"
            )

        # Determine next question dynamically in a human-like, conversational tone
        next_question = ""
        
        # Check: Professional Role
        if not pref.role:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            next_question = "To help me tailor my research, what best describes your current investment role or background?"

        # Check: Markets
        elif not pref.markets or len(pref.markets) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_MARKETS")
            role_title = pref.role.replace("_", " ").title()
            next_question = f"Great, a {role_title}! What markets or regions do you follow most closely? (e.g. US, India, Global Tech)"

        # Check: Watchlist Tickers
        elif not watchlists or len(watchlists) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_WATCHLIST")
            markets_str = " and ".join(pref.markets) if isinstance(pref.markets, list) else str(pref.markets)
            next_question = f"Understood, focusing on {markets_str} markets. Which specific companies or stock tickers should I keep an eye on for you?"

        # Check: Interests / Topics
        elif not interests or len(interests) == 0:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_INTERESTS")
            next_question = "Got it. When analyzing these stocks, what financial topics or events matter most to you? (e.g. AI, interest rates, earnings, inflation)"

        # Check: Daily Briefing Time
        elif not pref.briefing_time:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_BRIEFING_TIME")
            next_question = "Perfect. What time of day would you like to receive your personalized daily market briefing? (e.g. 8:00 AM, 9:00 AM)"

        # Check: Response Style
        elif not pref.response_style:
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_RESPONSE_STYLE")
            next_question = "Almost done! Do you prefer quick summaries, standard updates, or highly detailed financial deep-dives?"

        if next_question:
            return next_question

        # 5. Onboarding is fully complete!
        UserService.update_user_onboarding_status(db, user.id, completed=True, state="COMPLETED")

        # Generate a premium, personalized investment recap using Groq
        symbols_str = ", ".join([w.symbol for w in watchlists])
        topics_str = ", ".join([i.topic for i in interests])
        markets_str = ", ".join(pref.markets) if isinstance(pref.markets, list) else str(pref.markets)

        prompt = (
            f"User profile details:\n"
            f"- Role: {pref.role}\n"
            f"- Markets: {markets_str}\n"
            f"- Watchlist: {symbols_str}\n"
            f"- Interests: {topics_str}\n"
            f"- Briefing: {pref.briefing_time}\n"
            f"- Response Style: {pref.response_style}\n"
        )
        
        recap_content = ""
        try:
            llm = LLMProvider()
            recap = await llm.generate_response(prompt, system_prompt=RECAP_SYSTEM_PROMPT, fast=False)
            if recap:
                recap_content = recap
        except Exception as e:
            logger.error(f"Failed to generate custom onboarding recap: {e}")

        if not recap_content:
            recap_content = (
                f"As your personal assistant, I will track *{symbols_str}* and monitor *{topics_str}* "
                f"across the *{markets_str}* markets for you. I've scheduled your daily briefings for *{pref.briefing_time}*."
            )

        return (
            f"🎉 **Your assistant profile is set up!**\n\n"
            f"{recap_content}\n\n"
            f"Ask me about any company, market update, or financial topic to begin!"
        )

    @staticmethod
    def get_current_onboarding_question(db: Session, user: User) -> str:
        """
        Returns the onboarding question for the user's current missing preferences without mutating state.
        """
        pref = UserService.get_user_preferences(db, user.id)
        watchlists = user.watchlists
        interests = user.interests

        if not pref or not pref.role:
            return "what best describes your current investment role or background? (e.g. retail investor, student, day trader, analyst)"
        
        if not pref.markets or len(pref.markets) == 0:
            role_title = pref.role.replace("_", " ").title()
            return f"what markets or regions do you follow most closely? (e.g. US, India, Global Tech)"
            
        if not watchlists or len(watchlists) == 0:
            markets_str = " and ".join(pref.markets) if isinstance(pref.markets, list) else str(pref.markets)
            return f"which specific companies or stock tickers should I keep an eye on for you?"
            
        if not interests or len(interests) == 0:
            return "when analyzing these stocks, what financial topics or events matter most to you? (e.g. AI, interest rates, earnings, inflation)"
            
        if not pref.briefing_time:
            return "what time of day would you like to receive your personalized daily market briefing? (e.g. 8:00 AM, 9:00 AM)"
            
        if not pref.response_style:
            return "do you prefer quick summaries, standard updates, or highly detailed financial deep-dives?"
            
        return "how can I help you today?"

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """Fallback compatibility helper (always returns original English text)."""
        return text
