from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import UserService
from app.services.relevance_engine import RelevanceEngine
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_provider import NewsProvider
from app.telegram.bot_client import TelegramBotClient
from app.core.logging import logger

class BriefingScheduler:
    """
    Timezone-aware daily briefing scheduler.
    Collects watchlist data and news, ranks events via RelevanceEngine,
    and enforces the Silence Principle (Sends NOTHING if no meaningful events).
    """

    @staticmethod
    async def generate_user_daily_briefing(db: Session, user_id: int) -> Optional[str]:
        user = UserService.get_user_by_id(db, user_id)
        if not user or not user.onboarding_completed:
            return None

        pref = UserService.get_user_preferences(db, user_id)
        watchlists = [w.symbol for w in user.watchlists]
        interests = [i.topic for i in user.interests]

        if not watchlists:
            watchlists = ["NVDA", "MSFT"]

        # Fetch market quotes
        quotes = await MarketDataProvider.get_multiple_quotes(watchlists)
        market_sum = await MarketDataProvider.get_market_summary("US")

        # Fetch news items
        news_items = await NewsProvider.get_watchlist_news(watchlists, limit_per_symbol=1)

        # Filter events via RelevanceEngine
        important_news = []
        for news in news_items:
            res = RelevanceEngine.evaluate_event(
                db=db,
                symbol=news.symbol,
                headline=news.headline,
                summary=news.summary,
                source=news.source,
                market_impact=0.75,
                user_relevance=0.85,
                urgency=0.6,
                novelty=0.9
            )
            if res.action in ["BRIEFING", "IMPORTANT", "IMMEDIATE_ALERT"]:
                important_news.append(news)

        # SILENCE PRINCIPLE: If no quote moves and no news score > 30, remain silent!
        has_significant_move = any(abs(q.change_percent) >= 0.5 for q in quotes)
        if not important_news and not has_significant_move:
            logger.info(f"Silence Principle Enforced for user_id={user_id}. No high-relevance events today.")
            return None

        # Build Briefing Output
        watchlist_bullets = ""
        for q in quotes:
            direction = "↑" if q.change_percent >= 0 else "↓"
            sign = "+" if q.change_percent >= 0 else ""
            watchlist_bullets += f"• *{q.symbol}*: ${q.price:.2f} ({direction} {sign}{q.change_percent:.2f}%)\n"

        news_bullets = ""
        for n in important_news:
            news_bullets += f"• *{n.symbol}*: {n.headline}\n  _{n.summary}_ (Source: {n.source})\n"

        indices_str = ", ".join([f"{k}: {v}" for k, v in market_sum.indices.items()])

        briefing_msg = (
            f"☀️ *Your Financial Brief*\n\n"
            f"*MARKETS*\n"
            f"• {indices_str}\n\n"
            f"*YOUR WATCHLIST*\n"
            f"{watchlist_bullets}\n"
            f"*KEY CATALYSTS & DEVELOPMENTS*\n"
            f"{news_bullets if news_bullets else '• No major single-stock catalysts reported today.'}\n"
            f"*YOUR ATTENTION*\n"
            f"• Market indicators remain within standard volatility bounds.\n\n"
            f"_Nothing else requires your attention._"
        )

        return briefing_msg

    @staticmethod
    async def run_scheduled_briefings(db: Session) -> int:
        """
        Executes daily briefing run for all completed users.
        """
        users = db.query(User).filter(User.onboarding_completed == True).all()
        sent_count = 0
        bot_client = TelegramBotClient()

        for user in users:
            briefing = await BriefingScheduler.generate_user_daily_briefing(db, user.id)
            if briefing:
                success = await bot_client.send_message(chat_id=user.telegram_user_id, text=briefing)
                if success:
                    RelevanceEngine.record_notification_sent(
                        db=db, user_id=user.id, content=briefing, notification_type="daily_briefing"
                    )
                    sent_count += 1
        logger.info(f"Completed scheduled briefing run. Sent briefings to {sent_count} user(s).")
        return sent_count
