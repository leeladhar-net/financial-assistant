import pytest
from app.services.user_service import UserService
from app.services.proactive_alert_service import ProactiveAlertService
from app.models.proactive_alert import ProactiveAlert

def test_create_automatic_alerts(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=8800)
    
    # Trigger auto alerts for NVDA at $100.00
    activated = ProactiveAlertService.create_automatic_alerts(db_session, user.id, "NVDA", 100.00)
    
    assert len(activated) == 3 # Support, Target, Earnings
    types = [a["type"] for a in activated]
    assert "Support Price Level" in types
    assert "Target Price Level" in types
    assert "Earnings Catalysts Update" in types

    # Query DB to verify persistence
    alerts = ProactiveAlertService.get_active_alerts(db_session, user.id)
    assert len(alerts) == 3
    
    # Try calling again - should not create duplicates
    activated_again = ProactiveAlertService.create_automatic_alerts(db_session, user.id, "NVDA", 100.00)
    assert len(activated_again) == 0
