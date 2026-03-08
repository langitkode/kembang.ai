"""add_tenant_faqs_table

Revision ID: add_tenant_faqs
Revises: fc007e311b38
Create Date: 2026-03-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_tenant_faqs'
down_revision: Union[str, None] = 'fc007e311b38'  # Update this to the latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenant_faqs table
    op.create_table(
        'tenant_faqs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('question_patterns', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_tenant_faqs_tenant_id', 'tenant_faqs', ['tenant_id'])
    op.create_index('idx_tenant_faqs_category', 'tenant_faqs', ['category'])
    op.create_index('idx_tenant_faqs_is_active', 'tenant_faqs', ['is_active'])
    
    # Create composite index for common query pattern
    op.create_index(
        'idx_tenant_faqs_tenant_category_active',
        'tenant_faqs',
        ['tenant_id', 'category', 'is_active']
    )


def downgrade() -> None:
    op.drop_index('idx_tenant_faqs_tenant_category_active')
    op.drop_index('idx_tenant_faqs_is_active')
    op.drop_index('idx_tenant_faqs_category')
    op.drop_index('idx_tenant_faqs_tenant_id')
    op.drop_table('tenant_faqs')
