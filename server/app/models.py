from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# enum подобные строки

SCORING_ALL_OR_NOTHING = "all_or_nothing"
SCORING_PARTIAL_SUM = "partial_sum"

INPUT_STRING = "string"
INPUT_NUMBER = "number"

STATUS_IN_PROGRESS = "in_progress"
STATUS_FINISHED = "finished"
STATUS_TIME_EXPIRED = "time_expired"
STATUS_ABORTED = "aborted"

ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """администратор/преподаватель"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Курган")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="school")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (Index("ix_students_normalized_name", "normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)

    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    school: Mapped["School"] = relationship(back_populates="students")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="student")


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="variant",
        order_by="Task.number",
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("variant_id", "number", name="uq_task_variant_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), nullable=False)

    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    statement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    instruction_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_data_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scoring_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SCORING_ALL_OR_NOTHING
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    variant: Mapped["Variant"] = relationship(back_populates="tasks")
    fields: Mapped[list["AnswerField"]] = relationship(
        back_populates="task",
        order_by="AnswerField.sort_order",
    )
    files: Mapped[list["TaskFile"]] = relationship(back_populates="task")


class AnswerField(Base):
    __tablename__ = "answer_fields"
    __table_args__ = (UniqueConstraint("task_id", "code", name="uq_answer_field_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    input_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=INPUT_STRING
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    task: Mapped["Task"] = relationship(back_populates="fields")


class TaskFile(Base):
    __tablename__ = "task_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    task: Mapped["Task"] = relationship(back_populates="files")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), nullable=False)
    machine_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_IN_PROGRESS
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    primary_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secondary_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_primary_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversion_table_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversion_tables.id"), nullable=True
    )

    finish_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="attempts")
    variant: Mapped["Variant"] = relationship()
    answers: Mapped[list["AttemptAnswer"]] = relationship(back_populates="attempt")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "answers_field_id", name="uq_attempt_answer_field"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    answers_field_id: Mapped[int] = mapped_column(
        ForeignKey("answer_fields.id"), nullable=False
    )

    raw_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    attempt: Mapped["Attempt"] = relationship(back_populates="answers")


class ConversionTable(Base):
    __tablename__ = "conversion_tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_primary: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    entries: Mapped[list["ConversionEntry"]] = relationship(
        back_populates="table",
        order_by="ConversionEntry.primary_score",
    )


class ConversionEntry(Base):
    __tablename__ = "conversion_entries"
    __table_args__ = (
        UniqueConstraint(
            "conversion_table_id", "primary_score", name="uq_conversion_entry"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversion_table_id: Mapped[int] = mapped_column(
        ForeignKey("conversion_tables.id"), nullable=False
    )
    primary_score: Mapped[int] = mapped_column(Integer, nullable=False)
    secondary_score: Mapped[int] = mapped_column(Integer, nullable=False)

    table: Mapped["ConversionTable"] = relationship(back_populates="entries")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AttemptEvent(Base):
    """телеметрия: события хода экзамена"""

    __tablename__ = "attempt_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("attempts.id"), nullable=True
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Machine(Base):
    """компьютер ученика"""

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
