"""add_mock_interview_and_star_breakdown

Revision ID: g8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-09-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection


# revision identifiers, used by Alembic.
revision: str = 'g8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    tables = insp.get_table_names()

    # 1. mock_interview_sessions
    if 'mock_interview_sessions' not in tables:
        op.create_table(
            'mock_interview_sessions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('domain_id', sa.String(100), nullable=False, index=True),
            sa.Column('role', sa.String(255), nullable=True),
            sa.Column('difficulty', sa.String(50), nullable=False),
            sa.Column('duration_minutes', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='setup'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('interview_plan', sa.JSON(), nullable=True),
            sa.Column('evaluation_status', sa.String(50), nullable=False, server_default='pending'),
        )

    # 2. mock_interview_turns
    if 'mock_interview_turns' not in tables:
        op.create_table(
            'mock_interview_turns',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('mock_interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('turn_index', sa.Integer(), nullable=False),
            sa.Column('question_id', sa.String(100), nullable=False),
            sa.Column('question_domain_id', sa.String(100), nullable=False),
            sa.Column('question_title', sa.String(500), nullable=False),
            sa.Column('question_category', sa.String(255), nullable=False),
            sa.Column('question_topic', sa.String(255), nullable=False),
            sa.Column('question_difficulty', sa.String(50), nullable=False),
            sa.Column('is_follow_up', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('follow_up_focus', sa.String(500), nullable=True),
            sa.Column('transcript_text', sa.Text(), nullable=True),
            sa.Column('stt_engine', sa.String(50), nullable=True),
            sa.Column('stt_confidence', sa.Float(), nullable=True),
            sa.Column('asked_at', sa.DateTime(), nullable=True),
            sa.Column('answered_at', sa.DateTime(), nullable=True),
            sa.Column('answer_duration_seconds', sa.Float(), nullable=True),
            sa.Column('followup_verdict', sa.JSON(), nullable=True),
        )

    # 3. mock_answer_evaluations
    if 'mock_answer_evaluations' not in tables:
        op.create_table(
            'mock_answer_evaluations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('turn_id', sa.Integer(), sa.ForeignKey('mock_interview_turns.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
            sa.Column('correctness', sa.Float(), nullable=True),
            sa.Column('completeness', sa.Float(), nullable=True),
            sa.Column('relevance', sa.Float(), nullable=True),
            sa.Column('technical_depth', sa.Float(), nullable=True),
            sa.Column('clarity', sa.Float(), nullable=True),
            sa.Column('star_breakdown', sa.JSON(), nullable=True),
            sa.Column('missing_concepts', sa.JSON(), nullable=True),
            sa.Column('incorrect_claims', sa.JSON(), nullable=True),
            sa.Column('positive_points', sa.JSON(), nullable=True),
            sa.Column('improvement_points', sa.JSON(), nullable=True),
            sa.Column('better_answer_notes', sa.Text(), nullable=True),
            sa.Column('ai_model_used', sa.String(100), nullable=True),
            sa.Column('evaluated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('evaluation_error', sa.String(500), nullable=True),
        )
    else:
        # Check if star_breakdown column is missing
        columns = [c['name'] for c in insp.get_columns('mock_answer_evaluations')]
        if 'star_breakdown' not in columns:
            op.add_column('mock_answer_evaluations', sa.Column('star_breakdown', sa.JSON(), nullable=True))

    # 4. mock_interview_assessments
    if 'mock_interview_assessments' not in tables:
        op.create_table(
            'mock_interview_assessments',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('mock_interview_sessions.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
            sa.Column('overall_score', sa.Float(), nullable=True),
            sa.Column('skill_matrix', sa.JSON(), nullable=True),
            sa.Column('weak_areas', sa.JSON(), nullable=True),
            sa.Column('recommendations', sa.JSON(), nullable=True),
            sa.Column('summary_text', sa.Text(), nullable=True),
            sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('ai_model_used', sa.String(100), nullable=True),
        )

    # 5. mock_question_rubrics
    if 'mock_question_rubrics' not in tables:
        op.create_table(
            'mock_question_rubrics',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('question_id', sa.String(100), nullable=False, index=True),
            sa.Column('domain_id', sa.String(100), nullable=False),
            sa.Column('key_concepts', sa.JSON(), nullable=True),
            sa.Column('extraction_method', sa.String(50), nullable=False, server_default='heuristic'),
            sa.Column('model_used', sa.String(100), nullable=True),
            sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('question_id', 'domain_id', name='uq_mock_rubric_q_domain'),
        )


def downgrade() -> None:
    op.drop_table('mock_question_rubrics')
    op.drop_table('mock_interview_assessments')
    op.drop_table('mock_answer_evaluations')
    op.drop_table('mock_interview_turns')
    op.drop_table('mock_interview_sessions')
