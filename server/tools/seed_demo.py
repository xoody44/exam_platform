"""Демо-данные для ручной проверки потока ученика.

Запуск из папки server/:
    poetry run python -m tools.seed_demo
"""

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    INPUT_NUMBER,
    INPUT_STRING,
    SCORING_ALL_OR_NOTHING,
    SCORING_PARTIAL_SUM,
    AnswerField,
    ConversionEntry,
    ConversionTable,
    Task,
    Variant,
)
from app.services.auth import ensure_default_admin
from app.services.seed import seed_schools
from app.services.settings import seed_settings

DEMO_VARIANT_TITLE = "Демо-вариант"

# (номер, заголовок, текст, макс. балл, тип проверки, поля)
TASKS_SPEC = [
    (
        1,
        "Задание 1",
        "Введите ответ ABC без пробелов. Регистр важен.",
        1,
        SCORING_ALL_OR_NOTHING,
        [("answer", "Ответ", INPUT_STRING, 1, "ABC")],
    ),
    (
        2,
        "Задание 2",
        "Введите число 1.5 (можно ввести 1.50 — оно эквивалентно).",
        1,
        SCORING_ALL_OR_NOTHING,
        [("answer", "Ответ", INPUT_NUMBER, 1, "1.5")],
    ),
    (
        26,
        "Задание 26",
        "Две независимые части, по 1 баллу каждая.",
        2,
        SCORING_PARTIAL_SUM,
        [
            ("part1", "Часть 1", INPUT_NUMBER, 1, "12"),
            ("part2", "Часть 2", INPUT_NUMBER, 1, "34"),
        ],
    ),
    (
        27,
        "Задание 27",
        "Две независимые части, по 1 баллу каждая.",
        2,
        SCORING_PARTIAL_SUM,
        [
            ("part1", "Часть 1", INPUT_NUMBER, 1, "7"),
            ("part2", "Часть 2", INPUT_NUMBER, 1, "8"),
        ],
    ),
]

# Максимальный первичный балл демо-варианта: 1 + 1 + 2 + 2 = 6
DEMO_CONVERSION = {0: 0, 1: 17, 2: 33, 3: 50, 4: 67, 5: 83, 6: 100}


def seed_demo(db: Session) -> None:
    existing = db.query(Variant).filter(Variant.title == DEMO_VARIANT_TITLE).first()
    if existing is not None:
        print("Демо-вариант уже существует, пропускаю.")
        return

    variant = Variant(title=DEMO_VARIANT_TITLE, is_active=True)
    db.add(variant)
    db.flush()

    for number, title, statement, max_score, scoring, fields in TASKS_SPEC:
        task = Task(
            variant_id=variant.id,
            number=number,
            title=title,
            statement_text=statement,
            max_score=max_score,
            scoring_type=scoring,
        )
        db.add(task)
        db.flush()

        for order, (code, label, input_type, points, expected) in enumerate(fields, start=1):
            db.add(
                AnswerField(
                    task_id=task.id,
                    code=code,
                    label=label,
                    input_type=input_type,
                    sort_order=order,
                    points=points,
                    expected_answer=expected,
                )
            )

    table = ConversionTable(
        name="Демо-таблица (макс. 6)",
        year=2026,
        max_primary=6,
        is_active=True,
    )
    db.add(table)
    db.flush()

    for primary, secondary in DEMO_CONVERSION.items():
        db.add(
            ConversionEntry(
                conversion_table_id=table.id,
                primary_score=primary,
                secondary_score=secondary,
            )
        )

    db.commit()
    print("Демо-вариант и демо-таблица перевода созданы.")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
        seed_schools(db)
        seed_settings(db)
        seed_demo(db)
    finally:
        db.close()
    print("Готово. Можно запускать сервер и идти в /docs.")


if __name__ == "__main__":
    main()