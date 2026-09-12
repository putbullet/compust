"""add_structured_resume_builder_fields

Revision ID: a1b2c3d4e5f6
Revises: e1f2a3b4c5d6
Create Date: 2026-09-12 01:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely for MySQL and SQLite."""
    # Add new columns to resumes table
    op.add_column('resumes', sa.Column('title', sa.String(255), nullable=False, server_default='My Resume'))
    op.add_column('resumes', sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('resumes', sa.Column('target_job_id', sa.Integer(), nullable=True))
    op.add_column('resumes', sa.Column('source_resume_id', sa.Integer(), nullable=True))
    op.add_column('resumes', sa.Column('structured_data', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('settings', sa.JSON(), nullable=True))

    # Foreign keys
    try:
        op.create_foreign_key('fk_resumes_target_job_id', 'resumes', 'jobs', ['target_job_id'], ['id'], ondelete='SET NULL')
    except Exception:
        pass

    try:
        op.create_foreign_key('fk_resumes_source_resume_id', 'resumes', 'resumes', ['source_resume_id'], ['id'], ondelete='SET NULL')
    except Exception:
        pass

    # Indexes
    try:
        op.create_index('idx_resumes_user_default', 'resumes', ['user_id', 'is_default'])
    except Exception:
        pass

    try:
        op.create_index('idx_resumes_user_target_job', 'resumes', ['user_id', 'target_job_id'])
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_index('idx_resumes_user_target_job', table_name='resumes')
    except Exception:
        pass
    try:
        op.drop_index('idx_resumes_user_default', table_name='resumes')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_resumes_source_resume_id', 'resumes', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_resumes_target_job_id', 'resumes', type_='foreignkey')
    except Exception:
        pass

    op.drop_column('resumes', 'settings')
    op.drop_column('resumes', 'structured_data')
    op.drop_column('resumes', 'source_resume_id')
    op.drop_column('resumes', 'target_job_id')
    op.drop_column('resumes', 'is_default')
    op.drop_column('resumes', 'title')
