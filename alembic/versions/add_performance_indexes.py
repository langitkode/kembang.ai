"""add_performance_indexes

Add indexes for query performance optimization.

Revision ID: add_performance_indexes
Revises: 4e08150adc0c
Create Date: 2026-03-09 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = '4e08150adc0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index for product category grouping
    op.create_index(
        'idx_products_category',
        'products',
        ['category'],
        if_not_exists=True
    )
    
    # Add index for low stock queries
    op.create_index(
        'idx_products_stock_quantity',
        'products',
        ['stock_quantity'],
        if_not_exists=True
    )
    
    # Add index for API key lookups
    op.create_index(
        'idx_tenants_api_key',
        'tenants',
        ['api_key'],
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('idx_tenants_api_key', 'tenants')
    op.drop_index('idx_products_stock_quantity', 'products')
    op.drop_index('idx_products_category', 'products')
