
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


def utc_now():
    return datetime.now(timezone.utc)


# =========================================================
# DOCUMENT
# =========================================================

class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "file_size >= 0",
            name="ck_document_file_size"
        ),
        CheckConstraint(
            "character_count >= 0",
            name="ck_document_character_count"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    character_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="document",
    )


# =========================================================
# JOB
# =========================================================

class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            "question_count > 0",
            name="ck_job_question_count"
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_job_retry_count"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="queued",
        nullable=False,
    )

    llm_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    total_time_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        default="mock",
        nullable=False
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    question_count: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        back_populates="jobs"
    )

    quiz: Mapped["Quiz | None"] = relationship(
        back_populates="job",
        uselist=False,
    )


# =========================================================
# QUIZ
# =========================================================

class Quiz(Base):
    __tablename__ = "quizzes"

    __table_args__ = (
        CheckConstraint(
            "question_count > 0",
            name="ck_quiz_question_count"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
        unique=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
    )

    topic_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    question_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    job: Mapped["Job"] = relationship(
        back_populates="quiz"
    )

    document: Mapped["Document"] = relationship(
        back_populates="quizzes"
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="Question.question_order",
    )


# =========================================================
# QUESTION
# =========================================================

class Question(Base):
    __tablename__ = "questions"

    __table_args__ = (
        UniqueConstraint(
            "quiz_id",
            "question_order",
            name="uq_question_quiz_order"
        ),
        CheckConstraint(
            "question_order > 0",
            name="ck_question_order"
        ),
        CheckConstraint(
            "correct_answer IN ('A', 'B', 'C', 'D')",
            name="ck_question_correct_answer"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id"),
        nullable=False,
        index=True,
    )

    question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    option_a: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    option_b: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    option_c: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    option_d: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    correct_answer: Mapped[str] = mapped_column(
        String(1),
        nullable=False
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    quiz: Mapped["Quiz"] = relationship(
        back_populates="questions"
    )
