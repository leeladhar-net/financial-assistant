import pytest
from sqlalchemy.orm import Session
from app.models.portfolio import PortfolioTransaction
from app.services.portfolio_service import PortfolioService
from app.services.user_service import UserService
from app.schemas.portfolio import PortfolioTransactionCreate

@pytest.mark.asyncio
async def test_portfolio_transaction_db_logging(db_session: Session):
    # Create test user
    user = UserService.get_or_create_user(db_session, telegram_user_id=12301)
    
    # Manually log a BUY transaction
    txn1 = PortfolioTransaction(
        user_id=user.id,
        symbol="AAPL",
        quantity=10.0,
        price=150.0,
        transaction_type="BUY"
    )
    db_session.add(txn1)
    
    # Manually log a SELL transaction
    txn2 = PortfolioTransaction(
        user_id=user.id,
        symbol="AAPL",
        quantity=3.0,
        price=180.0,
        transaction_type="SELL"
    )
    db_session.add(txn2)
    db_session.commit()

    # Query holdings
    txns = db_session.query(PortfolioTransaction).filter(PortfolioTransaction.user_id == user.id).all()
    assert len(txns) == 2
    assert txns[0].symbol == "AAPL"
    assert txns[0].quantity == 10.0
    assert txns[1].transaction_type == "SELL"

@pytest.mark.asyncio
async def test_portfolio_summary_calculations(db_session: Session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=12302)
    
    # Buy 10 shares of NVDA at $100
    db_session.add(PortfolioTransaction(
        user_id=user.id, symbol="NVDA", quantity=10.0, price=100.0, transaction_type="BUY"
    ))
    # Buy another 5 shares of NVDA at $130
    db_session.add(PortfolioTransaction(
        user_id=user.id, symbol="NVDA", quantity=5.0, price=130.0, transaction_type="BUY"
    ))
    db_session.commit()

    # Calculate portfolio summary
    summary = await PortfolioService.get_portfolio_summary(db_session, user.id)
    assert len(summary.holdings) == 1
    nvda_holding = summary.holdings[0]
    
    assert nvda_holding.symbol == "NVDA"
    assert nvda_holding.quantity == 15.0
    # Average buy price: (10*100 + 5*130) / 15 = 1650 / 15 = 110.0
    assert nvda_holding.avg_buy_price == 110.0
    assert nvda_holding.total_cost == 1650.0

    # P&L should match current market price (which will be > 0 and calculated correctly)
    assert nvda_holding.current_price > 0
    assert nvda_holding.market_value == nvda_holding.current_price * 15.0
    expected_pnl = (nvda_holding.current_price * 15.0) - 1650.0
    assert abs(nvda_holding.pnl_amount - expected_pnl) < 0.01
