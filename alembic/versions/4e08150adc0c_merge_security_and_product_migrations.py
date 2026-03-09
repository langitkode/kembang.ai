"""Merge security and product migrations

Revision ID: 4e08150adc0c
Revises: add_user_security_fields, create_products
Create Date: 2026-03-09 10:55:56.828038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e08150adc0c'
down_revision: Union[str, None] = ('add_user_security_fields', 'create_products')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
