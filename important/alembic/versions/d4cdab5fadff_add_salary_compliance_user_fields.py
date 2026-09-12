"""add_salary_compliance_user_fields

Revision ID: d4cdab5fadff
Revises: 
Create Date: 2026-09-11 14:57:19.547917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4cdab5fadff'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('salary_min', sa.Numeric(12, 2), nullable=True))
    op.add_column('jobs', sa.Column('salary_max', sa.Numeric(12, 2), nullable=True))
    op.add_column('jobs', sa.Column('salary_currency', sa.CHAR(3), nullable=True))
    op.add_column('jobs', sa.Column('salary_period', sa.String(20), nullable=True))

    op.add_column('user_preferences', sa.Column('salary_currency', sa.CHAR(3), nullable=True))

    op.add_column('scrape_targets', sa.Column('robots_txt_allowed', sa.Boolean(), nullable=True))
    op.add_column('scrape_targets', sa.Column('robots_txt_checked_at', sa.DateTime(), nullable=True))

    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'email_verified')
    op.drop_column('scrape_targets', 'robots_txt_checked_at')
    op.drop_column('scrape_targets', 'robots_txt_allowed')
    op.drop_column('user_preferences', 'salary_currency')
    op.drop_column('jobs', 'salary_period')
    op.drop_column('jobs', 'salary_currency')
    op.drop_column('jobs', 'salary_max')
    op.drop_column('jobs', 'salary_min')
