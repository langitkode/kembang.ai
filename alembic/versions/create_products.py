"""create_products_table

Create products table for sales catalog.

Revision ID: create_products
Revises: add_conversation_state
Create Date: 2026-03-09 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'create_products'
down_revision: Union[str, None] = 'add_conversation_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('sku', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('discount_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_products_tenant_id', 'products', ['tenant_id'])
    op.create_index('idx_products_sku_tenant', 'products', ['tenant_id', 'sku'])  # Unique per tenant
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_is_active', 'products', ['is_active'])
    op.create_index('idx_products_price', 'products', ['price'])


def downgrade() -> None:
    op.drop_index('idx_products_price')
    op.drop_index('idx_products_is_active')
    op.drop_index('idx_products_category')
    op.drop_index('idx_products_sku')
    op.drop_index('idx_products_tenant_id')
    op.drop_table('products')
