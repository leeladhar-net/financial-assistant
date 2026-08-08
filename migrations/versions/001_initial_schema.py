"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-08 19:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=False, server_default='UTC'),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('onboarding_state', sa.String(length=50), nullable=False, server_default='NEW'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_telegram_user_id'), 'users', ['telegram_user_id'], unique=True)

    # User Preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('markets', sa.JSON(), nullable=True),
        sa.Column('briefing_time', sa.String(length=50), nullable=True),
        sa.Column('response_style', sa.String(length=50), nullable=True, server_default='standard'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)

    # Watchlists table
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('market', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlists_id'), 'watchlists', ['id'], unique=False)
    op.create_index(op.f('ix_watchlists_user_id'), 'watchlists', ['user_id'], unique=False)

    # User Interests table
    op.create_table(
        'user_interests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_interests_id'), 'user_interests', ['id'], unique=False)
    op.create_index(op.f('ix_user_interests_user_id'), 'user_interests', ['user_id'], unique=False)

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=False, server_default='text'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'], unique=False)

    # User Memory table
    op.create_table(
        'user_memory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('memory_key', sa.String(length=100), nullable=False),
        sa.Column('memory_value', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(length=50), nullable=False, server_default='preference'),
        sa.Column('importance', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_memory_id'), 'user_memory', ['id'], unique=False)
    op.create_index(op.f('ix_user_memory_memory_key'), 'user_memory', ['memory_key'], unique=False)
    op.create_index(op.f('ix_user_memory_user_id'), 'user_memory', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_table('user_memory')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('user_interests')
    op.drop_table('watchlists')
    op.drop_table('user_preferences')
    op.drop_table('users')
