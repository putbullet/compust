"""create_customized_resumes_table

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4
Create Date: 2026-09-11 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'customized_resumes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('base_resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('pdf_filename', sa.String(255), nullable=True),
        sa.Column('docx_filename', sa.String(255), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsed_sections', sa.JSON(), nullable=True),
        sa.Column('ats_analysis', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_cust_resume_user_job', 'customized_resumes', ['user_id', 'job_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('customized_resumes')
