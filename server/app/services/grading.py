from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from ..models import (
    SCORING_PARTIAL_SUM,
    AnswerField,
    Attempt,
    AttemptAnswer,
    Task,
)
from .conversion import get_active_conversion_table


def normalize_string(raw: str) -> str:
    return "".join((raw or "").split())


def parse_decimal(raw: str) -> Decimal:
    text = "".join((raw or "").split())
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def check_field_is_correct(field: AnswerField, raw: str) -> bool:
    if field.input_type == "number":
        expected = parse_decimal(field.expected_answer)
        given = parse_decimal(raw)
        return expected is not None and given is not None and expected == given
    return normalize_string(raw) == normalize_string(field.expected_answer)


def compute_task_score(
    scoring_type: str,
    max_score: int,
    parts: list[tuple[int, bool]],
) -> int:
    if not parts:
        return 0

    if scoring_type == SCORING_PARTIAL_SUM:
        return min(sum(points for points, ok in parts if ok), max_score)

    return max_score if all(ok for _, ok in parts) else 0


@dataclass
class FieldGrade:
    field_id: int
    raw_value: str
    normalized_value: str
    is_correct: bool
    score: int


@dataclass
class TaskGrade:
    task_id: int
    number: int
    score: int
    max_score: int
    fields: list[FieldGrade] = field(default_factory=list)


@dataclass
class GradeResult:
    primary_score: int
    max_primary_score: int
    secondary_score: int | None
    max_secondary_score: int | None
    conversion_table_id: int | None
    tasks: list[TaskGrade] = field(default_factory=list)


def grade_attempt(db: Session, attempt: Attempt) -> GradeResult:
    tasks = (
        db.query(Task)
        .filter(
            Task.variant_id == attempt.variant_id,
            Task.archived_at.is_(None),
        )
        .order_by(Task.number)
        .all()
    )

    existing_answers = {
        aa.answers_field_id: aa
        for aa in db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    }

    total_primary = 0
    max_primary = 0
    task_grades: list[TaskGrade] = []

    for task in tasks:
        max_primary += task.max_score

        fields = (
            db.query(AnswerField)
            .filter(AnswerField.task_id == task.id)
            .order_by(AnswerField.sort_order, AnswerField.id)
            .all()
        )

        field_grades: list[FieldGrade] = []
        for f in fields:
            aa = existing_answers.get(f.id)
            raw = aa.raw_value if aa else ""

            fg = FieldGrade(
                field_id=f.id,
                raw_value=raw,
                normalized_value=normalize_string(raw),
                is_correct=check_field_is_correct(f, raw),
                score=0,
            )
            field_grades.append(fg)
        if not fields:
            task_score = 0
        elif task.scoring_type == SCORING_PARTIAL_SUM:
            for fg, f in zip(field_grades, fields):
                fg.score = f.points if fg.is_correct else 0
            task_score = min(sum(fg.score for fg in field_grades), task.max_score)
        else:
            all_correct = all(fg.is_correct for fg in field_grades)
            task_score = task.max_score if all_correct else 0
            for fg, f in zip(field_grades, fields):
                fg.score = f.points if all_correct else 0
        for f, fg in zip(fields, field_grades):
            aa = existing_answers.get(f.id)
            if aa is None:
                aa = AttemptAnswer(
                    attempt_id=attempt.id,
                    task_id=task.id,
                    answers_field_id=f.id,
                )
                db.add(aa)
                existing_answers[f.id] = aa

            aa.raw_value = fg.raw_value
            aa.normalized_value = fg.normalized_value
            aa.is_correct = fg.is_correct
            aa.score = fg.score
        total_primary += task_score
        task_grades.append(
            TaskGrade(
                task_id=task.id,
                number=task.number,
                score=task_score,
                max_score=task.max_score,
                fields=field_grades,
            )
        )
    table = get_active_conversion_table(db, max_primary)

    secondary_score: int | None = None
    max_secondary: int | None = None
    table_id: int | None = None

    if table is not None:
        table_id = table.id
        entry = next(
            (e for e in table.entries if e.primary_score == total_primary),
            None,
        )
        secondary_score = entry.secondary_score if entry else None
        max_secondary = max(
            (e.secondary_score for e in table.entries),
            default=None,
        )
    attempt.primary_score = total_primary
    attempt.max_primary_score = max_primary
    attempt.secondary_score = secondary_score
    attempt.conversion_table_id = table_id

    return GradeResult(
        primary_score=total_primary,
        max_primary_score=max_primary,
        secondary_score=secondary_score,
        max_secondary_score=max_secondary,
        conversion_table_id=table_id,
        tasks=task_grades,
    )
