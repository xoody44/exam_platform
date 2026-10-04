import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..exceptions import bad_request, conflict, not_found
from ..models import (
    SCORING_PARTIAL_SUM,
    STATUS_FINISHED,
    STATUS_TIME_EXPIRED,
    AnswerField,
    Attempt,
    ConversionEntry,
    ConversionTable,
    Task,
    TaskFile,
    User,
    Variant,
    utcnow,
)
from ..schemas import (
    AdminFieldOut,
    AdminTaskOut,
    ConversionTableCreateIn,
    ConversionTableOut,
    ConversionTablePatchIn,
    FieldCreateIn,
    FieldPatchIn,
    SettingsOut,
    SettingsPatchIn,
    TaskCreateIn,
    TaskPatchIn,
    TaskFileOut,
    VariantCreateIn,
    VariantDetailOut,
    VariantOut,
    VariantPatchIn,
)
from .audit import log_action
from .settings import apply_settings_patch, get_setting, get_settings_out

ALLOWED_EXTENSIONS = {
    "txt", "doc", "docx", "xls", "xlsx", "csv", "odt", "png", "jpg", "jpeg",
}
PARTIAL_SUM_ALLOWED_NUMBERS = {26, 27}

def _variant_or_404(db: Session, variant_id: int) -> Variant:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise not_found("Вариант не найден")
    return variant

def _task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found("Задание не найдено")
    return task

def _field_or_404(db: Session, field_id: int) -> AnswerField:
    field = db.get(AnswerField, field_id)
    if field is None:
        raise not_found("Поле ответа не найдено")
    return field

def variant_has_finished_attempts(db: Session, variant_id: int) -> bool:
    return (
        db.query(Attempt.id)
        .filter(
            Attempt.variant_id == variant_id,
            Attempt.status.in_([STATUS_FINISHED, STATUS_TIME_EXPIRED]),
        )
        .first()
        is not None
    )

def _check_partial_sum_rules(number: int, scoring_type: str) -> None:
    if scoring_type == SCORING_PARTIAL_SUM and number not in PARTIAL_SUM_ALLOWED_NUMBERS:
        raise bad_request("частичный балл разрешён только для заданий 26 и 27")

def _load_task(db: Session, task_id: int) -> Task:
    return (
        db.query(Task)
        .options(selectinload(Task.fields), selectinload(Task.files))
        .filter(Task.id == task_id)
        .one()
    )


def _variant_out(db: Session, variant: Variant) -> VariantOut:
    return VariantOut(
        id=variant.id,
        title=variant.title,
        is_active=variant.is_active,
        created_at=variant.created_at,
        archived_at=variant.archived_at,
        tasks_count=(
            db.query(Task)
            .filter(Task.variant_id == variant.id, Task.archived_at.is_(None))
            .count()
        ),
        attempts_count=(
            db.query(Attempt).filter(Attempt.variant_id == variant.id).count()
        ),
    )


def list_variants(db: Session) -> list[VariantOut]:
    variants = db.query(Variant).order_by(Variant.id.desc()).all()
    return [_variant_out(db, v) for v in variants]


def create_variant(db: Session, user: User, payload: VariantCreateIn) -> VariantOut:
    variant = Variant(title=payload.title, is_active=True)
    db.add(variant)
    db.commit()
    db.refresh(variant)
    log_action(db, user.id, "create_variant", "variant", variant.id, {"title": variant.title})
    return _variant_out(db, variant)


def get_variant(db: Session, variant_id: int) -> VariantDetailOut:
    variant = _variant_or_404(db, variant_id)
    tasks = (
        db.query(Task)
        .options(selectinload(Task.fields), selectinload(Task.files))
        .filter(Task.variant_id == variant.id)
        .order_by(Task.number)
        .all()
    )
    base = _variant_out(db, variant)
    return VariantDetailOut(
        **base.model_dump(),
        tasks=[AdminTaskOut.model_validate(t) for t in tasks],
    )


def patch_variant(
    db: Session, user: User, variant_id: int, payload: VariantPatchIn,
) -> VariantOut:
    variant = _variant_or_404(db, variant_id)
    used = variant_has_finished_attempts(db, variant.id)

    if payload.title is not None:
        if used:
            raise conflict(
                "вариант использован в завершённых попытках: переименование запрещено "
                "доступны только деактивация и архивирование"
            )
        variant.title = payload.title

    if payload.is_active is not None:
        variant.is_active = payload.is_active

    db.commit()
    db.refresh(variant)
    log_action(db, user.id, "update_variant", "variant", variant.id, payload.model_dump(exclude_unset=True))
    return _variant_out(db, variant)


def archive_variant(db: Session, user: User, variant_id: int) -> VariantOut:
    variant = _variant_or_404(db, variant_id)
    variant.archived_at = utcnow()
    variant.is_active = False
    db.commit()
    db.refresh(variant)
    log_action(db, user.id, "archive_variant", "variant", variant.id, {"title": variant.title})
    return _variant_out(db, variant)


def list_tasks(db: Session, variant_id: int) -> list[AdminTaskOut]:
    _variant_or_404(db, variant_id)
    tasks = (
        db.query(Task)
        .options(selectinload(Task.fields), selectinload(Task.files))
        .filter(Task.variant_id == variant_id)
        .order_by(Task.number)
        .all()
    )
    return [AdminTaskOut.model_validate(t) for t in tasks]


def create_task(db: Session, user: User, variant_id: int, payload: TaskCreateIn) -> AdminTaskOut:
    variant = _variant_or_404(db, variant_id)

    if variant_has_finished_attempts(db, variant.id):
        raise conflict("вариант использован в завершённых попытках: добавлять задания нельзя")

    _check_partial_sum_rules(payload.number, payload.scoring_type)

    duplicate = (
        db.query(Task)
        .filter(Task.variant_id == variant.id, Task.number == payload.number)
        .first()
    )
    if duplicate is not None:
        raise conflict(f"задание с номером {payload.number} уже есть в этом варианте")

    task = Task(variant_id=variant.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    log_action(db, user.id, "create_task", "task", task.id, {"number": task.number})
    return AdminTaskOut.model_validate(_load_task(db, task.id))


def get_task(db: Session, task_id: int) -> AdminTaskOut:
    _task_or_404(db, task_id)
    return AdminTaskOut.model_validate(_load_task(db, task_id))


def patch_task(db: Session, user: User, task_id: int, payload: TaskPatchIn) -> AdminTaskOut:
    task = _task_or_404(db, task_id)

    if variant_has_finished_attempts(db, task.variant_id):
        raise conflict(
            "задание использовано в завершённых попытках: редактирование запрещено "
            "доступно только архивирование"
        )

    data = payload.model_dump(exclude_unset=True)

    new_number = data.get("number", task.number)
    new_scoring = data.get("scoring_type", task.scoring_type)
    _check_partial_sum_rules(new_number, new_scoring)

    if "number" in data:
        duplicate = (
            db.query(Task)
            .filter(
                Task.variant_id == task.variant_id,
                Task.number == new_number,
                Task.id != task.id,
            )
            .first()
        )
        if duplicate is not None:
            raise conflict(f"задание с номером {new_number} уже есть в этом варианте")

    for key, value in data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    log_action(db, user.id, "update_task", "task", task.id, data)
    return AdminTaskOut.model_validate(_load_task(db, task.id))


def archive_task(db: Session, user: User, task_id: int) -> AdminTaskOut:
    task = _task_or_404(db, task_id)
    task.archived_at = utcnow()
    db.commit()
    db.refresh(task)
    log_action(db, user.id, "archive_task", "task", task.id, {"number": task.number})
    return AdminTaskOut.model_validate(_load_task(db, task.id))


def create_field(db: Session, user: User, task_id: int, payload: FieldCreateIn) -> AdminFieldOut:
    task = _task_or_404(db, task_id)

    if variant_has_finished_attempts(db, task.variant_id):
        raise conflict("задание использовано в завершённых попытках: добавлять поля нельзя")

    duplicate = (
        db.query(AnswerField)
        .filter(AnswerField.task_id == task.id, AnswerField.code == payload.code)
        .first()
    )
    if duplicate is not None:
        raise conflict(f"поле с кодом {payload.code} уже есть у этого задания")

    field = AnswerField(task_id=task.id, **payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    log_action(db, user.id, "create_field", "answer_field", field.id, {"code": field.code})
    return AdminFieldOut.model_validate(field)


def patch_field(db: Session, user: User, field_id: int, payload: FieldPatchIn) -> AdminFieldOut:
    field = _field_or_404(db, field_id)
    task = _task_or_404(db, field.task_id)

    if variant_has_finished_attempts(db, task.variant_id):
        raise conflict(
            "задание использовано в завершённых попытках: правка правильных ответов запрещена"
        )

    data = payload.model_dump(exclude_unset=True)

    if "code" in data:
        duplicate = (
            db.query(AnswerField)
            .filter(
                AnswerField.task_id == task.id,
                AnswerField.code == data["code"],
                AnswerField.id != field.id,
            )
            .first()
        )
        if duplicate is not None:
            raise conflict(f"поле с кодом {data['code']} уже есть у этого задания")

    for key, value in data.items():
        setattr(field, key, value)

    db.commit()
    db.refresh(field)
    log_action(db, user.id, "update_field", "answer_field", field.id, data)
    return AdminFieldOut.model_validate(field)


def delete_field(db: Session, user: User, field_id: int) -> int:
    field = _field_or_404(db, field_id)
    task = _task_or_404(db, field.task_id)

    if variant_has_finished_attempts(db, task.variant_id):
        raise conflict("задание использовано в завершённых попытках: удалять поля нельзя")

    db.delete(field)
    db.commit()
    log_action(db, user.id, "delete_field", "answer_field", field_id, None)
    return field_id


def upload_file(db: Session, user: User, task_id: int, upload: UploadFile) -> TaskFileOut:
    task = _task_or_404(db, task_id)

    original_name = upload.filename or "file"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise bad_request(
            f"Расширение '.{ext}' запрещено. Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    data = upload.file.read()

    max_bytes = int(get_setting(db, "max_file_size_bytes"))
    if len(data) > max_bytes:
        raise bad_request(f"файл превышает лимит размера ({max_bytes} байт)")

    if len(data) == 0:
        raise bad_request("пустой файл")

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest: Path = get_settings().task_files_dir / stored_name
    dest.write_bytes(data)

    row = TaskFile(
        task_id=task.id,
        file_path=str(dest),
        original_name=original_name,
        mime_type=upload.content_type,
        size_bytes=len(data),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db, user.id, "upload_file", "task_file", row.id,
        {"task_id": task.id, "original_name": original_name, "size_bytes": row.size_bytes},
    )
    return TaskFileOut.model_validate(row)


def delete_file(db: Session, user: User, file_id: int) -> int:
    row = db.get(TaskFile, file_id)
    if row is None:
        raise not_found("файл не найден")

    task = _task_or_404(db, row.task_id)
    if variant_has_finished_attempts(db, task.variant_id):
        raise conflict("задание использовано в завершённых попытках: удалять файлы нельзя")

    path = Path(row.file_path)
    if path.exists():
        path.unlink(missing_ok=True)

    db.delete(row)
    db.commit()
    log_action(db, user.id, "delete_file", "task_file", file_id, {"original_name": row.original_name})
    return file_id


def get_settings_view(db: Session) -> SettingsOut:
    return get_settings_out(db)


def update_settings(db: Session, user: User, payload: SettingsPatchIn) -> SettingsOut:
    result = apply_settings_patch(db, payload)
    log_action(db, user.id, "update_settings", "settings", None, payload.model_dump(exclude_unset=True))
    return result


def _table_or_404(db: Session, table_id: int) -> ConversionTable:
    table = db.get(ConversionTable, table_id)
    if table is None:
        raise not_found("Таблица перевода не найдена")
    return table


def _validate_entries(entries: list, max_primary: int) -> None:
    seen = set()
    for e in entries:
        if e.primary_score < 0 or e.primary_score > max_primary:
            raise bad_request(
                f"первичный балл {e.primary_score} вне диапазона 0..{max_primary}"
            )
        if e.primary_score in seen:
            raise conflict(f"дубликат строки для первичного балла {e.primary_score}")
        seen.add(e.primary_score)


def list_conversion_tables(db: Session) -> list[ConversionTableOut]:
    tables = db.query(ConversionTable).order_by(ConversionTable.id.desc()).all()
    return [ConversionTableOut.model_validate(t) for t in tables]


def create_conversion_table(
    db: Session, user: User, payload: ConversionTableCreateIn,
) -> ConversionTableOut:
    _validate_entries(payload.entries, payload.max_primary)

    table = ConversionTable(
        name=payload.name,
        year=payload.year,
        max_primary=payload.max_primary,
        is_active=False,
    )
    db.add(table)
    db.flush()

    for e in payload.entries:
        db.add(
            ConversionEntry(
                conversion_table_id=table.id,
                primary_score=e.primary_score,
                test_score=e.test_score,
            )
        )

    db.commit()
    db.refresh(table)
    log_action(db, user.id, "create_conversion_table", "conversion_table", table.id, {"name": table.name})
    return ConversionTableOut.model_validate(table)


def get_conversion_table(db: Session, table_id: int) -> ConversionTableOut:
    return ConversionTableOut.model_validate(_table_or_404(db, table_id))


def patch_conversion_table(
    db: Session, user: User, table_id: int, payload: ConversionTablePatchIn,
) -> ConversionTableOut:
    table = _table_or_404(db, table_id)
    data = payload.model_dump(exclude_unset=True)

    if payload.entries is not None:
        new_max = data.get("max_primary", table.max_primary)
        _validate_entries(payload.entries, new_max)

    if "max_primary" in data and payload.entries is None:
        bad = (
            db.query(ConversionEntry)
            .filter(
                ConversionEntry.conversion_table_id == table.id,
                ConversionEntry.primary_score > data["max_primary"],
            )
            .first()
        )
        if bad is not None:
            raise bad_request(
                f"в таблице есть строка с первичным баллом {bad.primary_score}, "
                f"больше нового максимума {data['max_primary']}"
            )

    for key in ("name", "year", "max_primary"):
        if key in data:
            setattr(table, key, data[key])

    if payload.entries is not None:
        db.query(ConversionEntry).filter(
            ConversionEntry.conversion_table_id == table.id
        ).delete(synchronize_session=False)
        for e in payload.entries:
            db.add(
                ConversionEntry(
                    conversion_table_id=table.id,
                    primary_score=e.primary_score,
                    test_score=e.test_score,
                )
            )

    db.commit()
    db.refresh(table)
    log_action(db, user.id, "update_conversion_table", "conversion_table", table.id, data)
    return ConversionTableOut.model_validate(table)


def activate_conversion_table(db: Session, user: User, table_id: int) -> ConversionTableOut:
    table = _table_or_404(db, table_id)

    db.query(ConversionTable).filter(ConversionTable.id != table.id).update(
        {ConversionTable.is_active: False}, synchronize_session=False
    )
    table.is_active = True

    db.commit()
    db.refresh(table)
    log_action(db, user.id, "activate_conversion_table", "conversion_table", table.id, {"name": table.name})
    return ConversionTableOut.model_validate(table)
