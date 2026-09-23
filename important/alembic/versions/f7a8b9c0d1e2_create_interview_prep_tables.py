"""create_interview_prep_tables

Revision ID: f7a8b9c0d1e2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-18 18:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create interview_questions and interview_explanations tables."""
    # Create interview_questions table
    op.create_table(
        'interview_questions',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('track', sa.String(50), nullable=False, index=True),
        sa.Column('category', sa.String(100), nullable=False, index=True),
        sa.Column('difficulty', sa.String(50), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('source_reference', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create interview_explanations table for cached visual AI breakdowns
    op.create_table(
        'interview_explanations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('question_id', sa.String(100), nullable=False, index=True),
        sa.Column('language', sa.String(10), nullable=False, index=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('question_id', 'language', 'model_name', 'schema_version', name='uq_interview_exp_q_lang_model_ver'),
    )


def downgrade() -> None:
    """Drop tables."""
    op.drop_table('interview_explanations')
    op.drop_table('interview_questions')
