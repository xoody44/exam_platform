"""Настройки системы: чтение, сидирование, применение патчей."""

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Setting
from ..schemas import SettingsOut, SettingsPatchIn

DEFAULT_INSTRUCTION_TEXT = (
    "Пробный экзамен по информатике в формате ЕГЭ.\n\n"
    "- Длительность экзамена — 3 часа 55 минут (235 минут).\n"
    "- Ответы вводятся в поля соответствующего задания; ответ можно менять до завершения экзамена.\n"
    "- Ответы сохраняются автоматически.\n"
    "- Задания 26 и 27 состоят из двух частей, каждая часть оценивается отдельно.\n"
    "- После завершения экзамена вы увидите свой результат; правильные ответы не показываются.\n\n"
    "Желаем удачи!"
)

ALL_KEYS = (
    "exam_duration_minutes",
    "instruction_text",
    "max_file_size_bytes",
    "python_executable",
    "csc_path",
    "code_time_limit_seconds",
)


def _default_value(key: str) -> str:
    s = get_settings()
    if key == "exam_duration_minutes":
        return str(s.default_exam_duration_minutes)
    if key == "instruction_text":
        return DEFAULT_INSTRUCTION_TEXT
    if key == "max_file_size_bytes":
        return str(s.max_uploaded_size_mb * 1024 * 1024)
    if key == "python_executable":
        return ""
    if key == "csc_path":
        return ""
    if key == "code_time_limit_seconds":
        return "5"
    raise KeyError(key)


def get_setting(db: Session, key: str) -> str:
    """Значение настройки; при отсутствии создаёт строку с дефолтом."""
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=_default_value(key))
        db.add(row)
        db.commit()
        db.refresh(row)
    return row.value


def seed_settings(db: Session) -> None:
    for key in ALL_KEYS:
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=_default_value(key)))
    db.commit()


def get_settings_out(db: Session) -> SettingsOut:
    return SettingsOut(
        exam_duration_minutes=int(get_setting(db, "exam_duration_minutes")),
        instruction_text=get_setting(db, "instruction_text"),
        max_file_size_bytes=int(get_setting(db, "max_file_size_bytes")),
        python_executable=get_setting(db, "python_executable"),
        csc_path=get_setting(db, "csc_path"),
        code_time_limit_seconds=int(get_setting(db, "code_time_limit_seconds")),
    )


def apply_settings_patch(db: Session, payload: SettingsPatchIn) -> SettingsOut:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is None:
            continue
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
    db.commit()
    return get_settings_out(db)