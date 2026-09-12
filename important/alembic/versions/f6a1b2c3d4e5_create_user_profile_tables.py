"""create_user_profile_tables

Revision ID: f6a1b2c3d4e5
Revises: e5efb7c8a123
Create Date: 2026-09-11 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e5efb7c8a123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_experience',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('experience_type', sa.String(100), nullable=True, server_default='professional'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index('idx_user_experience_user', 'user_experience', ['user_id'])

    op.create_table(
        'user_education',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('institution', sa.String(255), nullable=False),
        sa.Column('degree', sa.String(255), nullable=True),
        sa.Column('field_of_study', sa.String(255), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index('idx_user_education_user', 'user_education', ['user_id'])

    op.create_table(
        'user_languages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language', sa.String(100), nullable=False),
        sa.Column('proficiency', sa.String(50), nullable=True, server_default='fluent'),
    )
    op.create_index('idx_user_languages_user', 'user_languages', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_languages')
    op.drop_table('user_education')
    op.drop_table('user_experience')
