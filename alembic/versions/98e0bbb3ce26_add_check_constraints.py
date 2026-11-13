
"""add check constraints

Revision ID: 98e0bbb3ce26
Revises: fdb45aedbeb3
Create Date: 2026-11-11 18:35:20.911735

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '98e0bbb3ce26'
down_revision: Union[str, Sequence[str], None] = 'fdb45aedbeb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CHECK constraints."""

    # Documents
    op.create_check_constraint(
        'ck_document_file_size',
        'documents',
        'file_size >= 0'
    )

    op.create_check_constraint(
        'ck_document_character_count',
        'documents',
        'character_count >= 0'
    )

    # Jobs
    op.create_check_constraint(
        'ck_job_question_count',
        'jobs',
        'question_count > 0'
    )

    op.create_check_constraint(
        'ck_job_retry_count',
        'jobs',
        'retry_count >= 0'
    )

    # Quizzes
    op.create_check_constraint(
        'ck_quiz_question_count',
        'quizzes',
        'question_count > 0'
    )

    # Questions
    op.create_check_constraint(
        'ck_question_order',
        'questions',
        'question_order > 0'
    )

    op.create_check_constraint(
        'ck_question_correct_answer',
        'questions',
        "correct_answer IN ('A', 'B', 'C', 'D')"
    )


def downgrade() -> None:
    """Remove CHECK constraints."""

    op.drop_constraint(
        'ck_question_correct_answer',
        'questions',
        type_='check'
    )

    op.drop_constraint(
        'ck_question_order',
        'questions',
        type_='check'
    )

    op.drop_constraint(
        'ck_quiz_question_count',
        'quizzes',
        type_='check'
    )

    op.drop_constraint(
        'ck_job_retry_count',
        'jobs',
        type_='check'
    )

    op.drop_constraint(
        'ck_job_question_count',
        'jobs',
        type_='check'
    )

    op.drop_constraint(
        'ck_document_character_count',
        'documents',
        type_='check'
    )

    op.drop_constraint(
        'ck_document_file_size',
        'documents',
        type_='check'
    )
