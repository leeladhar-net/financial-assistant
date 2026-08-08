from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.proactive_alert import ProactiveAlert
from app.core.logging import logger

class ProactiveAlertService:
    """
    Manages autonomous creation and lifecycle of situation-based reminders and alerts.
    """

    @staticmethod
    def create_automatic_alerts(db: Session, user_id: int, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        logger.info(f"Checking proactive alert triggers for user_id={user_id}, symbol={symbol} at current_price=${current_price:.2f}")
        
        # Define support and target limits
        support_price = round(current_price * 0.95, 2)
        target_price = round(current_price * 1.08, 2)
        
        activated_alerts = []

        # 1. Automatic Support Alert
        support_cond = f"price_below_{support_price}"
        existing_support = db.query(ProactiveAlert).filter(
            ProactiveAlert.user_id == user_id,
            ProactiveAlert.symbol == symbol,
            ProactiveAlert.alert_type == "price_boundary",
            ProactiveAlert.trigger_condition == support_cond,
            ProactiveAlert.is_active == True
        ).first()

        if not existing_support:
            alert = ProactiveAlert(
                user_id=user_id,
                symbol=symbol,
                alert_type="price_boundary",
                trigger_condition=support_cond,
                message_template=f"⚠️ *Proactive Alert*: {symbol} has broken below key support level of *${support_price:.2f}* (Live: ${{current_price:.2f}})."
            )
            db.add(alert)
            activated_alerts.append({
                "type": "Support Price Level",
                "detail": f"${support_price:.2f}"
            })

        # 2. Automatic Target/Profit Alert
        target_cond = f"price_above_{target_price}"
        existing_target = db.query(ProactiveAlert).filter(
            ProactiveAlert.user_id == user_id,
            ProactiveAlert.symbol == symbol,
            ProactiveAlert.alert_type == "price_boundary",
            ProactiveAlert.trigger_condition == target_cond,
            ProactiveAlert.is_active == True
        ).first()

        if not existing_target:
            alert = ProactiveAlert(
                user_id=user_id,
                symbol=symbol,
                alert_type="price_boundary",
                trigger_condition=target_cond,
                message_template=f"📈 *Proactive Alert*: {symbol} has reached your profit target of *${target_price:.2f}* (Live: ${{current_price:.2f}})."
            )
            db.add(alert)
            activated_alerts.append({
                "type": "Target Price Level",
                "detail": f"${target_price:.2f}"
            })

        # 3. Automatic Earnings Reminder
        earnings_cond = "upcoming_earnings"
        existing_earnings = db.query(ProactiveAlert).filter(
            ProactiveAlert.user_id == user_id,
            ProactiveAlert.symbol == symbol,
            ProactiveAlert.alert_type == "earnings",
            ProactiveAlert.trigger_condition == earnings_cond,
            ProactiveAlert.is_active == True
        ).first()

        if not existing_earnings:
            alert = ProactiveAlert(
                user_id=user_id,
                symbol=symbol,
                alert_type="earnings",
                trigger_condition=earnings_cond,
                message_template=f"🔔 *Earnings Briefing*: {symbol} is releasing quarterly earnings reports next week. We'll run a RAG briefing on the report contents."
            )
            db.add(alert)
            activated_alerts.append({
                "type": "Earnings Catalysts Update",
                "detail": "Next Week"
            })

        if activated_alerts:
            db.commit()

        return activated_alerts

    @staticmethod
    def get_active_alerts(db: Session, user_id: int) -> List[ProactiveAlert]:
        return db.query(ProactiveAlert).filter(
            ProactiveAlert.user_id == user_id,
            ProactiveAlert.is_active == True
        ).all()
