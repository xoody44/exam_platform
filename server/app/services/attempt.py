import json
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session, selectinload

from ..exceptions import bad_request, not_found
from ..models import (
    STATUS_ABORTED,
    STATUS_FINISHED,
    STATUS_IN_PROGRESS,
    STATUS_TIME_EXPIRED,
    AnswerField,
    Attempt,
    AttemptAnswer,
    AttemptEvent,
    ConversionTable,
    Machine,
    Student,
    Task,
    Variant,
    utcnow,
)
from ..schemas import (
    AnswerItemIn,
    AttemptInfoOut,
    AttemptResultOut,
    AttemptStateOut,
    EventItemIn,
    ScoresOut,
    StudentAnswerOut,
    StudentTaskOut,
    TaskResultOut,
)
from .grading import compute_task_score, grade_attempt
from .settings import get_setting
from .variant import choose_variant


def add_event(
    db: Session,
    *,
    attempt_id: int | None,
    student_id: int | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
    client_timestamp=None,
) -> None:
    """сохраняет событие попытки в AttemptEvent"""
    db.add(
        AttemptEvent(
            attempt_id=attempt_id,
            student_id=student_id,
            event_type=event_type,
            payload_json=(
                json.dumps(payload, ensure_ascii=False, default=str)
                if payload is not None
                else None
            ),
            client_timestamp=client_timestamp,
        )
    )
    db.commit()


def _load_tasks(db: Session, variant_id: int) -> list[Task]:
    """загружает неархивированные задания варианта с полями и файлами"""
    return (
        db.query(Task)
        .options(selectinload(Task.fields), selectinload(Task.files))
        .filter(
            Task.variant_id == variant_id,
            Task.archived_at.is_(None),
        )
        .order_by(Task.number)
        .all()
    )


def _register_machine(db: Session, machine_id: str | None) -> None:
    """закрывает или обновляет запись о машине ученика"""
    if not machine_id:
        return
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    now = utcnow()
    if machine is None:
        db.add(Machine(machine_id=machine_id, name=machine_id, last_seen_at=now))
    else:
        machine.last_seen_at = now
        db.commit()


def _finalize(
    db: Session,
    attempt: Attempt,
    status: str,
    reason: str,
    grade: bool,
) -> None:
    """помечает попытку завершённой, считает длительность и опционально проверяет"""
    attempt.status = status
    attempt.finished_at = utcnow()
    attempt.finish_reason = reason
    if attempt.started_at is not None:
        attempt.duration_seconds = int(
            (attempt.finished_at - attempt.started_at).total_seconds()
        )
    if grade:
        grade_attempt(db, attempt)
    db.commit()


def expire_if_needed(db: Session, attempt: Attempt) -> Attempt:
    """автоматически завершает попытку, если время вышло"""
    if (
        attempt.status == STATUS_IN_PROGRESS
        and attempt.expires_at is not None
        and attempt.expires_at <= utcnow()
    ):
        _finalize(db, attempt, STATUS_TIME_EXPIRED, "time_expired", grade=True)
        add_event(
            db,
            attempt_id=attempt.id,
            student_id=attempt.student_id,
            event_type="exam_time_expired",
        )
        db.refresh(attempt)
    return attempt


def _validate_answers(
    db: Session,
    attempt: Attempt,
    items: list[AnswerItemIn],
) -> list[tuple[int, int, str]]:
    """отбрасывает ответы, которые не относятся к заданиям варианта попытки"""
    if not items:
        return []

    tasks = {
        t.id: t
        for t in db.query(Task).filter(Task.variant_id == attempt.variant_id).all()
    }
    fields = {
        f.id: f
        for f in db.query(AnswerField)
        .filter(AnswerField.id.in_([i.field_id for i in items]))
        .all()
    }

    result: list[tuple[int, int, str]] = []
    for item in items:
        task = tasks.get(item.task_id)
        field = fields.get(item.field_id)
        if task is None or field is None or field.task_id != task.id:
            continue
        result.append((task.id, field.id, item.value))
    return result


def _upset_answers(
    db: Session,
    attempt: Attempt,
    validated: list[tuple[int, int, str]],
) -> None:
    """вставляет или обновляет сохранённые ответы ученика"""
    existing = {
        aa.answers_field_id: aa
        for aa in db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    }
    for task_id, field_id, value in validated:
        aa = existing.get(field_id)
        if aa is None:
            aa = AttemptAnswer(
                attempt_id=attempt.id,
                task_id=task_id,
                answers_field_id=field_id,
                raw_value=value,
            )
            db.add(aa)
            existing[field_id] = aa
        else:
            aa.raw_value = value
    db.commit()


def build_state(db: Session, attempt: Attempt) -> AttemptStateOut:
    """собирает полное состояние попытки для клиента ученика"""
    variant = db.get(Variant, attempt.variant_id)
    tasks = _load_tasks(db, attempt.variant_id)
    return AttemptStateOut(
        attempt=AttemptInfoOut.model_validate(attempt),
        variant_title=variant.title if variant else "",
        instruction_text=str(get_setting(db, "instruction_text")),
        server_time=utcnow(),
        tasks=[StudentTaskOut.model_validate(t) for t in tasks],
    )


def build_result(db: Session, attempt: Attempt) -> AttemptResultOut:
    """собирает результаты попытки для экрана итогов ученика"""
    tasks = _load_tasks(db, attempt.variant_id)
    answers = {
        aa.answers_field_id: aa
        for aa in db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    }

    graded = attempt.status in (STATUS_FINISHED, STATUS_TIME_EXPIRED)

    task_results: list[TaskResultOut] = []
    max_primary = 0

    for task in tasks:
        max_primary += task.max_score

        parts: list[tuple[int, bool]] = []
        student_answers: list[StudentAnswerOut] = []

        for f in task.fields:
            aa = answers.get(f.id)
            parts.append((f.points, bool(aa.is_correct) if aa else False))
            student_answers.append(
                StudentAnswerOut(
                    field_id=f.id,
                    label=f.label,
                    value=aa.raw_value if aa else "",
                )
            )

        task_score = (
            compute_task_score(task.scoring_type, task.max_score, parts)
            if graded
            else None
        )

        task_results.append(
            TaskResultOut(
                task_id=task.id,
                number=task.number,
                score=task_score,
                max_score=task.max_score,
                answers=student_answers,
            )
        )

    max_test: int | None = None
    if attempt.conversion_table_id is not None:
        table = db.get(ConversionTable, attempt.conversion_table_id)
        if table is not None:
            max_test = max(
                (e.test_score for e in table.entries),
                default=None,
            )

    scores = ScoresOut(
        primary_score=attempt.primary_score if graded else None,
        max_primary_score=max_primary,
        test_score=attempt.test_score if graded else None,
        max_test_score=max_test if graded else None,
        conversion_table_id=attempt.conversion_table_id if graded else None,
    )

    return AttemptResultOut(
        attempt=AttemptInfoOut.model_validate(attempt),
        scores=scores,
        tasks=task_results,
    )


def start_attempt(
    db: Session, student: Student, machine_id: str | None
) -> AttemptStateOut:
    """закрывает предыдущую незавершённую попытку и создаёт новую с выбранным вариантом"""
    previous = (
        db.query(Attempt)
        .filter(
            Attempt.student_id == student.id,
            Attempt.status == STATUS_IN_PROGRESS,
        )
        .first()
    )

    if previous is not None:
        if previous.expires_at is not None and previous.expires_at <= utcnow():
            _finalize(db, previous, STATUS_TIME_EXPIRED, "time_expired", grade=True)
        else:
            _finalize(
                db, previous, STATUS_ABORTED, "superseded_by_new_attempt", grade=False
            )
        add_event(
            db,
            attempt_id=previous.id,
            student_id=student.id,
            event_type="attempt_closed_on_new_start",
        )

    variant = choose_variant(db, student.id)
    duration_minutes = int(get_setting(db, "exam_duration_minutes"))
    now = utcnow()

    attempt = Attempt(
        student_id=student.id,
        variant_id=variant.id,
        machine_id=machine_id,
        status=STATUS_IN_PROGRESS,
        started_at=now,
        expires_at=now + timedelta(minutes=duration_minutes),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    _register_machine(db, machine_id)
    add_event(
        db,
        attempt_id=attempt.id,
        student_id=student.id,
        event_type="exam_started",
        payload={"variant_id": variant.id, "machine_id": machine_id},
    )

    return build_state(db, attempt)


def get_attempt_for_student(db: Session, attempt_id: int, student: Student) -> Attempt:
    """проверяет принадлежность попытки ученику и обрабатывает истечение времени"""
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.student_id != student.id:
        raise not_found("попытка не найдена")
    return expire_if_needed(db, attempt)


def save_answers(
    db: Session,
    attempt: Attempt,
    items: list[AnswerItemIn],
) -> int:
    """сохраняет ответы активной попытки, возвращает количество сохранённых"""
    if attempt.status != STATUS_IN_PROGRESS:
        raise bad_request("Попытка завершена, изменять ответы нельзя")

    validated = _validate_answers(db, attempt, items)
    _upset_answers(db, attempt, validated)

    add_event(
        db,
        attempt_id=attempt.id,
        student_id=attempt.student_id,
        event_type="answers_saved",
        payload={"count": len(validated)},
    )
    return len(validated)


def send_events(
    db: Session,
    attempt: Attempt,
    student: Student,
    events: list[EventItemIn],
) -> int:
    """принимает пакет событий телеметрии от клиента, возвращает количество принятых"""
    for e in events:
        db.add(
            AttemptEvent(
                attempt_id=attempt.id,
                student_id=student.id,
                event_type=e.event_type,
                payload_json=(
                    json.dumps(e.payload, ensure_ascii=False, default=str)
                    if e.payload is not None
                    else None
                ),
                client_timestamp=e.client_timestamp,
            )
        )
    db.commit()
    return len(events)


def finish_attempt(
    db: Session,
    attempt: Attempt,
    reason: str,
    answers: list[AnswerItemIn] | None,
) -> AttemptResultOut:
    """завершает попытку: финальные ответы, статус, автопроверка и события"""
    attempt = expire_if_needed(db, attempt)

    if attempt.status != STATUS_IN_PROGRESS:
        return build_result(db, attempt)

    if answers:
        validated = _validate_answers(db, attempt, answers)
        _upset_answers(db, attempt, validated)

    if reason == "aborted":
        _finalize(db, attempt, STATUS_ABORTED, "aborted", grade=False)
        add_event(
            db,
            attempt_id=attempt.id,
            student_id=attempt.student_id,
            event_type="attempt_aborted",
        )
        return build_result(db, attempt)
    status = STATUS_TIME_EXPIRED if reason == "time_expired" else STATUS_FINISHED
    _finalize(db, attempt, status, reason, grade=True)

    add_event(
        db,
        attempt_id=attempt.id,
        student_id=attempt.student_id,
        event_type=(
            "exam_finished" if status == STATUS_FINISHED else "exam_time_expired"
        ),
        payload={
            "primary_score": attempt.primary_score,
            "test_score": attempt.test_score,
        },
    )

    return build_result(db, attempt)
