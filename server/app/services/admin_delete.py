from sqlalchemy.orm import Session

from ..config import get_settings
from ..exceptions import conflict, not_found
from ..models import (
    AnswerField,
    Attempt,
    AttemptAnswer,
    AttemptCodeSubmission,
    AttemptEvent,
    CodeTest,
    ConversionTable,
    Student,
    Task,
    TaskFile,
    User,
    Variant,
    utcnow,
)
from .audit import log_action


def _delete_attempts_hard(db: Session, attempt_ids: list[int]) -> int:
    if not attempt_ids:
        return 0
    db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id.in_(attempt_ids)).delete(
        synchronize_session=False
    )
    db.query(AttemptEvent).filter(AttemptEvent.attempt_id.in_(attempt_ids)).delete(
        synchronize_session=False
    )
    db.query(AttemptCodeSubmission).filter(
        AttemptCodeSubmission.attempt_id.in_(attempt_ids)
    ).delete(synchronize_session=False)
    db.query(Attempt).filter(Attempt.id.in_(attempt_ids)).delete(
        synchronize_session=False
    )
    return len(attempt_ids)


def delete_student(db: Session, user: User, student_id: int) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise not_found("ученик не найден")
    attempt_ids = [
        a.id for a in db.query(Attempt).filter(Attempt.student_id == student_id).all()
    ]
    deleted = _delete_attempts_hard(db, attempt_ids)
    db.delete(student)
    db.commit()
    log_action(
        db,
        user.id,
        "delete_student",
        "students",
        student_id,
        {"attempts_deleted": deleted},
    )
    return {"deleted_student": student_id, "attempts_deleted": deleted}


def delete_all_students(db: Session, user: User) -> dict:
    students_count = db.query(Student).count()
    attempt_ids = [a.id for a in db.query(Attempt).all()]
    deleted = _delete_attempts_hard(db, attempt_ids)
    db.query(Student).delete(synchronize_session=False)
    db.commit()
    log_action(
        db,
        user.id,
        "delete_all_students",
        "students",
        None,
        {"students": students_count, "attempts_deleted": deleted},
    )
    return {"students_deleted": students_count, "attempts_deleted": deleted}


def delete_attempt(db: Session, user: User, attempt_id: int) -> dict:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.deleted_at is not None:
        raise not_found("попытка не найдена")
    attempt.deleted_at = utcnow()
    db.commit()
    log_action(db, user.id, "delete_attempt", "attempts", attempt_id, None)
    return {"deleted": attempt_id}


def delete_variant(db: Session, user: User, variant_id: int) -> dict:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise not_found("вариант не найден")
    if variant.archived_at is None:
        raise conflict("удалять можно только вариант из архива: сначала архивируйте")
    live = (
        db.query(Attempt)
        .filter(Attempt.variant_id == variant_id, Attempt.deleted_at.is_(None))
        .count()
    )
    if live:
        raise conflict(
            f"у варианта есть попытки ({live}). Сначала очистите результаты."
        )

    tasks = db.query(Task).filter(Task.variant_id == variant_id).all()
    task_ids = [t.id for t in tasks]
    if task_ids:
        settings = get_settings()
        files = db.query(TaskFile).filter(TaskFile.task_id.in_(task_ids)).all()
        for f in files:
            try:
                (settings.task_files_dir / f.file_path).unlink(missing_ok=True)
            except OSError:
                pass
        db.query(TaskFile).filter(TaskFile.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
        db.query(AnswerField).filter(AnswerField.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
        db.query(CodeTest).filter(CodeTest.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)

    db.delete(variant)
    db.commit()
    log_action(
        db,
        user.id,
        "delete_variant",
        "variants",
        variant_id,
        {"tasks_deleted": len(task_ids)},
    )
    return {"deleted": variant_id, "tasks_deleted": len(task_ids)}


def delete_conversion_table(db: Session, user: User, table_id: int) -> dict:
    table = db.get(ConversionTable, table_id)
    if table is None:
        raise not_found("Таблица перевода не найдена")

    # проверяем, есть ли попытки, которые используют эту таблицу.
    # до этого был необработанный трейсбек из-за этого
    linked_attempts = (
        db.query(Attempt)
        .filter(
            Attempt.conversion_table_id == table_id,
            Attempt.deleted_at.is_(None),
        )
        .count()
    )
    if linked_attempts > 0:
        raise conflict(
            f"Таблица используется {linked_attempts} попытками. "
            "Сначала удалите эти попытки."
        )

    for entry in list(table.entries):
        db.delete(entry)
    db.delete(table)
    db.commit()
    log_action(
        db, user.id, "delete_conversion_table", "conversion_tables", table_id, None
    )
    return {"deleted": table_id}
