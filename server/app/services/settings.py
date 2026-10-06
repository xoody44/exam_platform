import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import Setting
from ..schemas import SettingsOut, SettingsPatchIn

DEFAULTS: dict[str, Any] = {
    "exam_duration_minutes": 235,
    "instruction_text": (
        "Пробный экзамен по информатике в формате ЕГЭ.\n\n"
        "- Длительность экзамена - 3 часа 55 минут (235 минут).\n"
        "- Ответы вводятся в поля соответствующего задания; ответ можно менять до завершения экзамена.\n"
        "- Ответы сохраняются автоматически.\n"
        "- Задания 26 и 27 состоят из двух частей, каждая часть оценивается отдельно.\n"
        "- После завершения экзамена вы увидите свой результат;\n\n"
        "Желаем удачи!"
    ),
    "max_file_size_bytes": 50 * 1024 * 1024,
}


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(Setting, key)
    if row is None:
        return DEFAULTS.get(key, default)
    try:
        return json.loads(row.value)
    except (TypeError, ValueError):
        return row.value


def set_setting(db: Session, key: str, value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False)
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=raw))
    else:
        row.value = raw
    db.commit()


def get_settings_out(db: Session) -> SettingsOut:
    return SettingsOut(
        exam_duration_minutes=int(get_setting(db, "exam_duration_minutes")),
        instruction_text=str(get_setting(db, "instruction_text")),
        max_file_size_bytes=int(get_setting(db, "max_file_size_bytes")),
    )


def apply_settings_patch(db: Session, patch: SettingsPatchIn) -> SettingsOut:
    data = patch.model_dump(exclude_unset=True)
    for key, value in data.items():
        set_setting(db, key, value)
    return get_settings_out(db)


def seed_settings(db: Session) -> None:
    for key, value in DEFAULTS.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))
        db.commit()
