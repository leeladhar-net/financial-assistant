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
    async def process_onboarding_message(db: Session, user: User, message_text: str) -> str:
        """
        Processes incoming onboarding text message, extracts profile fields, updates state,
        and returns the next natural response.
        """
        current_state = user.onboarding_state or "NEW"
        logger.info(f"Processing onboarding for user_id={user.id}, state={current_state}")

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

        # If brand new user and no info was parsed from the first message, ask the first question
        if current_state == "NEW" and not parsed.get("role"):
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            return (
                "Hi! I'm your personal financial advisor. 💼\n\n"
                "I'll help you track companies, global markets, and financial trends that align with your goals.\n\n"
                "To get started, what best describes your current investment role or background? (e.g. retail investor, student, day trader, analyst)"
            )

        # 3. Update DB records with extracted attributes
        if parsed.get("preferred_language"):
            UserService.update_user_preferences(db, user.id, preferred_language=parsed["preferred_language"])
            MemoryService.save_memory(db, user.id, "preferred_language", parsed["preferred_language"], memory_type="profile")

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
        target_lang = pref.preferred_language or "English"

        # If brand new user and no info was parsed from the first message, ask the first question
        if current_state == "NEW" and not parsed.get("role"):
            UserService.update_user_onboarding_status(db, user.id, completed=False, state="ASK_ROLE")
            welcome_msg = (
                "Hi! I'm your personal financial advisor. 💼\n\n"
                "I'll help you track companies, global markets, and financial trends that align with your goals.\n\n"
                "To get started, what best describes your current investment role or background? (e.g. retail investor, student, day trader, analyst)"
            )
            return await OnboardingService.translate_text(welcome_msg, target_lang)

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
            return await OnboardingService.translate_text(next_question, target_lang)

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
            f"Generate the recap in {target_lang}."
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

        final_msg = (
            f"🎉 **Your assistant profile is set up!**\n\n"
            f"{recap_content}\n\n"
            f"Ask me about any company, market update, or financial topic to begin!"
        )
        return await OnboardingService.translate_text(final_msg, target_lang)

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """
        Translates text into the target language using Groq LLM.
        Keeps stock tickers and emojis intact.
        """
        if not target_language or target_language.lower() == "english":
            return text
        
        prompt = (
            f"Translate the following text into fluent, warm, natural {target_language}. "
            f"If translating to Hindi or Telugu, write in their native script (Devanagari/Telugu script) "
            f"but naturally leave common financial or interface words (like 'stock', 'price', 'portfolio', "
            f"'watchlist', 'briefing', 'standard', 'detailed', 'quick') in English alphabet or phonetics "
            f"if it sounds more natural and conversational (matching real-world Hinglish/Telglish speech).\n"
            f"Do NOT change stock tickers (e.g. AAPL, NVDA, RELIANCE) or emojis.\n"
            f"Return ONLY the translated text without any explanation or extra symbols:\n\n{text}"
        )
        try:
            llm = LLMProvider()
            translated = await llm.generate_response(prompt, system_prompt="You are a warm, helpful translator.", fast=True)
            if translated:
                return translated.strip()
        except Exception as e:
            logger.error(f"Failed translation to {target_language}: {e}")
        return text
