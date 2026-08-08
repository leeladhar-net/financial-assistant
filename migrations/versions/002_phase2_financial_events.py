"""002_phase2_financial_events

Revision ID: 002_phase2_financial_events
Revises: 001_initial_schema
Create Date: 2026-08-08 21:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_phase2_financial_events'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Financial Events table
    op.create_table(
        'financial_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('headline', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('market_impact', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('user_relevance', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('fingerprint', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financial_events_event_type'), 'financial_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_financial_events_fingerprint'), 'financial_events', ['fingerprint'], unique=True)
    op.create_index(op.f('ix_financial_events_id'), 'financial_events', ['id'], unique=False)
    op.create_index(op.f('ix_financial_events_importance_score'), 'financial_events', ['importance_score'], unique=False)
    op.create_index(op.f('ix_financial_events_symbol'), 'financial_events', ['symbol'], unique=False)

    # Notification History table
    op.create_table(
        'notification_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['financial_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_history_id'), 'notification_history', ['id'], unique=False)
    op.create_index(op.f('ix_notification_history_user_id'), 'notification_history', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_table('notification_history')
    op.drop_table('financial_events')
