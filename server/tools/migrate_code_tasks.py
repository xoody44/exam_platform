"""миграция: программные задания. запуск из server/:
poetry run python -m tools.migrate_code_tasks
"""

from sqlalchemy import inspect, text

from app.database import Base, engine


def main() -> None:
    insp = inspect(engine)
    columns = [c["name"] for c in insp.get_columns("tasks")]
    if "task_type" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN task_type VARCHAR(20) "
                    "NOT NULL DEFAULT 'answer'"
                )
            )
        print("Добавлена колонка tasks.task_type")
    else:
        print("Колонка tasks.task_type уже есть")

    Base.metadata.create_all(bind=engine)
    print("Таблицы code_tests и attempt_code_submissions готовы")


if __name__ == "__main__":
    main()
