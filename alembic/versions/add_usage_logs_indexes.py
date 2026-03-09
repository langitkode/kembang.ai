"""add_usage_logs_indexes

Add indexes for usage_logs query performance.

Revision ID: add_usage_logs_indexes
Revises: add_performance_indexes
Create Date: 2026-03-09 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_usage_logs_indexes'
down_revision: Union[str, None] = 'add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Critical index for tenant-based usage queries
    op.create_index(
        'idx_usage_logs_tenant_id',
        'usage_logs',
        ['tenant_id'],
        if_not_exists=True
    )
    
    # Index for timestamp-based filtering
    op.create_index(
        'idx_usage_logs_timestamp',
        'usage_logs',
        ['timestamp'],
        if_not_exists=True
    )
    
    # Composite index for tenant + timestamp queries (most common)
    op.create_index(
        'idx_usage_logs_tenant_timestamp',
        'usage_logs',
        ['tenant_id', 'timestamp'],
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('idx_usage_logs_tenant_timestamp', 'usage_logs')
    op.drop_index('idx_usage_logs_timestamp', 'usage_logs')
    op.drop_index('idx_usage_logs_tenant_id', 'usage_logs')
