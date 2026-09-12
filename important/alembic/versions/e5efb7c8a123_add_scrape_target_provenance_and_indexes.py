"""add_scrape_target_provenance_and_indexes

Revision ID: e5efb7c8a123
Revises: d4cdab5fadff
Create Date: 2026-09-11 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5efb7c8a123'
down_revision: Union[str, Sequence[str], None] = 'd4cdab5fadff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('scrape_target_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_jobs_scrape_target',
        'jobs',
        'scrape_targets',
        ['scrape_target_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('idx_jobs_company_external', 'jobs', ['company_id', 'external_job_id'])
    op.create_index('idx_jobs_company_url', 'jobs', ['company_id', 'job_url'], mysql_length={'job_url': 255})
    op.create_index('idx_jobs_target_seen', 'jobs', ['scrape_target_id', 'last_seen_at'])
    op.create_index('idx_jobs_active', 'jobs', ['active'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_jobs_active', table_name='jobs')
    op.drop_index('idx_jobs_target_seen', table_name='jobs')
    op.drop_index('idx_jobs_company_url', table_name='jobs')
    op.drop_index('idx_jobs_company_external', table_name='jobs')
    op.drop_constraint('fk_jobs_scrape_target', 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'scrape_target_id')
