"""add_user_security_fields

Add security fields to users table for account lockout.

Revision ID: add_user_security_fields
Revises: add_conversation_state
Create Date: 2026-03-09 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_user_security_fields'
down_revision: Union[str, None] = 'add_conversation_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add failed_login_attempts column
    op.add_column(
        'users',
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0')
    )
    
    # Add locked_until column
    op.add_column(
        'users',
        sa.Column('locked_until', sa.DateTime(), nullable=True)
    )
    
    # Create index for locked accounts lookup
    op.create_index('idx_users_locked_until', 'users', ['locked_until'])


def downgrade() -> None:
    op.drop_index('idx_users_locked_until')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
