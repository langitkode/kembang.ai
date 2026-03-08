"""add_conversation_state_fields

Add state and last_topic columns to conversations table for better context management.

Revision ID: add_conversation_state
Revises: add_tenant_faqs
Create Date: 2026-03-09 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_conversation_state'
down_revision: Union[str, None] = 'add_tenant_faqs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add state column (JSONB for flexible conversation state)
    op.add_column(
        'conversations',
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    
    # Add last_topic column
    op.add_column(
        'conversations',
        sa.Column('last_topic', sa.String(100), nullable=True)
    )
    
    # Create index on last_topic for analytics
    op.create_index('idx_conversations_last_topic', 'conversations', ['last_topic'])
    
    # Add comment to columns
    op.alter_column('conversations', 'state',
                    comment='Conversation state (topic, preferences, context)')
    op.alter_column('conversations', 'last_topic',
                    comment='Last discussed topic')


def downgrade() -> None:
    op.drop_index('idx_conversations_last_topic')
    op.drop_column('conversations', 'last_topic')
    op.drop_column('conversations', 'state')
