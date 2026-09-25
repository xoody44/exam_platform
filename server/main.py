import os
import secrets
import random
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    sessionmaker,
    DeclarativeBase,
    Session,
)

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam.db")

TEACHER_USERNAME = os.getenv("TEACHER_USERNAME", "admin")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "admin")

DEFAULT_EXAM_DURATION_MINUTES = 235


# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Модели
# ---------------------------------------------------------------------------


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    letter = Column(String(10), nullable=False)
    display_name = Column(String(50), nullable=False)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)

    full_name = Column(String(300), nullable=False)
    normalized_name = Column(String(300), nullable=False, index=True)

    created_at = Column(DateTime, default=utcnow)
    last_seen_at = Column(DateTime, default=utcnow)


class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    archived_at = Column(DateTime, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)

    number = Column(Integer, nullable=False)
    title = Column(String(300), nullable=False)

    statement_text = Column(Text, nullable=True)
    instruction_text = Column(Text, nullable=True)
    source_data_text = Column(Text, nullable=True)
    teacher_comment = Column(Text, nullable=True)

    max_score = Column(Integer, nullable=False, default=1)
    scoring_type = Column(String(30), nullable=False, default="all_or_nothing")

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    archived_at = Column(DateTime, nullable=True)


class AnswerField(Base):
    __tablename__ = "answer_fields"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    code = Column(String(50), nullable=False)
    label = Column(String(200), nullable=False)

    input_type = Column(String(20), nullable=False, default="string")
    sort_order = Column(Integer, nullable=False, default=0)

    points = Column(Integer, nullable=False, default=1)
    expected_answer = Column(Text, nullable=False, default="")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)

    machine_id = Column(String(100), nullable=True)

    status = Column(String(20), nullable=False, default="in_progress")

    started_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    duration_seconds = Column(Integer, nullable=True)

    primary_score = Column(Integer, nullable=True)
    secondary_score = Column(Integer, nullable=True)

    finish_reason = Column(String(30), nullable=True)


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "answer_field_id",
            name="uq_attempt_answer_field",
        ),
    )

    id = Column(Integer, primary_key=True)

    attempt_id = Column(Integer, ForeignKey("attempts.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    answer_field_id = Column(Integer, ForeignKey("answer_fields.id"), nullable=False)

    raw_value = Column(Text, nullable=False, default="")
    normalized_value = Column(Text, nullable=True)

    is_correct = Column(Boolean, nullable=True)
    score = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True)

    token = Column(String(100), unique=True, index=True, nullable=False)
    role = Column(String(20), nullable=False)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)


class ConversionTable(Base):
    __tablename__ = "conversion_tables"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    year = Column(Integer, nullable=True)
    max_primary = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class ConversionEntry(Base):
    __tablename__ = "conversion_entries"

    id = Column(Integer, primary_key=True)
    conversion_table_id = Column(
        Integer,
        ForeignKey("conversion_tables.id"),
        nullable=False,
    )
    primary_score = Column(Integer, nullable=False)
    secondary_score = Column(Integer, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# Pydantic схемы
# ---------------------------------------------------------------------------


class StudentLoginIn(BaseModel):
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    class_number: int
    class_letter: str


class StartAttemptIn(BaseModel):
    machine_id: Optional[str] = None


class AnswerItem(BaseModel):
    task_id: int
    field_id: int
    value: str


class SaveAnswersIn(BaseModel):
    answers: List[AnswerItem]


class FinishAttemptIn(BaseModel):
    reason: Optional[str] = "finished"
    answers: Optional[List[AnswerItem]] = None


class TeacherLoginIn(BaseModel):
    username: str
    password: str


class VariantIn(BaseModel):
    title: str


class TaskIn(BaseModel):
    number: int
    title: str
    statement_text: Optional[str] = None
    instruction_text: Optional[str] = None
    source_data_text: Optional[str] = None
    teacher_comment: Optional[str] = None
    max_score: int = 1
    scoring_type: str = "all_or_nothing"


class AnswerFieldIn(BaseModel):
    code: str
    label: str
    input_type: str = "string"
    sort_order: int = 0
    points: int = 1
    expected_answer: str = ""


# ---------------------------------------------------------------------------
# Приложение
# ---------------------------------------------------------------------------

app = FastAPI(title="Exam Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Зависимости
# ---------------------------------------------------------------------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_token(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Token:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Требуется токен")

    token_value = authorization.split(" ", 1)[1].strip()
    token = db.query(Token).filter(Token.token == token_value).first()

    if not token:
        raise HTTPException(status_code=401, detail="Неверный токен")

    if token.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Токен истек")

    return token


def require_student(
    token: Token = Depends(get_token),
    db: Session = Depends(get_db),
) -> Student:
    if token.role != "student":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    student = db.get(Student, token.student_id)
    if not student:
        raise HTTPException(status_code=401, detail="Ученик не найден")

    return student


def require_teacher(
    token: Token = Depends(get_token),
) -> Token:
    if token.role != "teacher":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    return token


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").split()).strip()


def normalize_answer(value: Optional[str]) -> str:
    return "".join((value or "").split())


def parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    try:
        text = "".join((value or "").split())
        if not text:
            return None
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def get_setting_value(db: Session, key: str, default: str) -> str:
    setting = db.get(Setting, key)
    if not setting:
        return default
    return setting.value


def get_exam_duration_minutes(db: Session) -> int:
    raw = get_setting_value(
        db,
        "exam_duration_minutes",
        str(DEFAULT_EXAM_DURATION_MINUTES),
    )
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_EXAM_DURATION_MINUTES


def create_token(
    db: Session,
    role: str,
    student_id: Optional[int] = None,
) -> Token:
    token = Token(
        token=secrets.token_urlsafe(32),
        role=role,
        student_id=student_id,
        expires_at=utcnow() + timedelta(hours=12),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_class_or_create(
    db: Session,
    number: int,
    letter: str,
) -> Class:
    letter = normalize_text(letter).upper()

    cls = db.query(Class).filter(Class.number == number, Class.letter == letter).first()

    if cls:
        return cls

    cls = Class(
        number=number,
        letter=letter,
        display_name=f"{number} {letter}",
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


def get_student_or_create(
    db: Session,
    cls: Class,
    last_name: str,
    first_name: str,
    middle_name: Optional[str],
) -> Student:
    last_name = normalize_text(last_name)
    first_name = normalize_text(first_name)
    middle_name = normalize_text(middle_name) if middle_name else None

    parts = [last_name, first_name]
    if middle_name:
        parts.append(middle_name)

    full_name = " ".join(parts)
    normalized_name = full_name.lower()

    student = (
        db.query(Student)
        .filter(
            Student.class_id == cls.id,
            Student.normalized_name == normalized_name,
        )
        .first()
    )

    if student:
        student.last_seen_at = utcnow()
        db.commit()
        db.refresh(student)
        return student

    student = Student(
        class_id=cls.id,
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        full_name=full_name,
        normalized_name=normalized_name,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def choose_variant(db: Session, student_id: int) -> Variant:
    active_variants = db.query(Variant).filter(Variant.is_active == True).all()

    if not active_variants:
        raise HTTPException(
            status_code=400,
            detail="Нет активных вариантов",
        )

    attempts = db.query(Attempt).filter(Attempt.student_id == student_id).all()

    already_taken_variant_ids = {
        attempt.variant_id for attempt in attempts if attempt.variant_id
    }

    unseen_variants = [
        variant
        for variant in active_variants
        if variant.id not in already_taken_variant_ids
    ]

    candidates = unseen_variants if unseen_variants else active_variants

    loaded = []
    for variant in candidates:
        count = db.query(Attempt).filter(Attempt.variant_id == variant.id).count()
        loaded.append((count, variant))

    min_load = min(item[0] for item in loaded)
    best = [variant for count, variant in loaded if count == min_load]

    return random.choice(best)


def public_field(field: AnswerField) -> dict:
    return {
        "id": field.id,
        "code": field.code,
        "label": field.label,
        "input_type": field.input_type,
        "sort_order": field.sort_order,
        "points": field.points,
    }


def public_task(db: Session, task: Task) -> dict:
    fields = (
        db.query(AnswerField)
        .filter(AnswerField.task_id == task.id)
        .order_by(AnswerField.sort_order)
        .all()
    )

    return {
        "id": task.id,
        "number": task.number,
        "title": task.title,
        "statement_text": task.statement_text,
        "instruction_text": task.instruction_text,
        "source_data_text": task.source_data_text,
        "max_score": task.max_score,
        "scoring_type": task.scoring_type,
        "fields": [public_field(field) for field in fields],
    }


def public_attempt(db: Session, attempt: Attempt, student: Student) -> dict:
    variant = db.get(Variant, attempt.variant_id)

    tasks = (
        db.query(Task)
        .filter(Task.variant_id == attempt.variant_id)
        .order_by(Task.number)
        .all()
    )

    return {
        "attempt": {
            "id": attempt.id,
            "status": attempt.status,
            "started_at": (
                attempt.started_at.isoformat() if attempt.started_at else None
            ),
            "expires_at": (
                attempt.expires_at.isoformat() if attempt.expires_at else None
            ),
            "finished_at": (
                attempt.finished_at.isoformat() if attempt.finished_at else None
            ),
            "primary_score": attempt.primary_score,
            "secondary_score": attempt.secondary_score,
            "finish_reason": attempt.finish_reason,
        },
        "variant": {
            "id": variant.id if variant else None,
            "title": variant.title if variant else "",
        },
        "student": {
            "id": student.id,
            "full_name": student.full_name,
        },
        "instruction": get_setting_value(
            db,
            "instruction_text",
            "Экзаменационная инструкция. Текст можно изменить в настройках.",
        ),
        "tasks": [public_task(db, task) for task in tasks],
    }


def save_answers_to_attempt(
    db: Session,
    attempt: Attempt,
    answers: List[AnswerItem],
) -> None:
    variant_tasks = {
        task.id: task
        for task in db.query(Task).filter(Task.variant_id == attempt.variant_id).all()
    }

    for answer in answers:
        task = variant_tasks.get(answer.task_id)
        if not task:
            continue

        field = db.get(AnswerField, answer.field_id)
        if not field or field.task_id != task.id:
            continue

        existing = (
            db.query(AttemptAnswer)
            .filter(
                AttemptAnswer.attempt_id == attempt.id,
                AttemptAnswer.answer_field_id == field.id,
            )
            .first()
        )

        if existing:
            existing.raw_value = answer.value
            existing.updated_at = utcnow()
        else:
            db.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    task_id=task.id,
                    answer_field_id=field.id,
                    raw_value=answer.value,
                )
            )

    db.commit()


def get_secondary_score(db: Session, primary_score: int) -> Optional[int]:
    table = (
        db.query(ConversionTable)
        .filter(ConversionTable.is_active == True)
        .order_by(ConversionTable.id.desc())
        .first()
    )

    if not table:
        # Временная заглушка для MVP.
        # Потом лучше заменить на реальную таблицу перевода.
        return primary_score

    entry = (
        db.query(ConversionEntry)
        .filter(
            ConversionEntry.conversion_table_id == table.id,
            ConversionEntry.primary_score == primary_score,
        )
        .first()
    )

    if not entry:
        return primary_score

    return entry.secondary_score


def grade_attempt(db: Session, attempt: Attempt) -> None:
    tasks = db.query(Task).filter(Task.variant_id == attempt.variant_id).all()

    attempt_answers = (
        db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
    )

    answers_by_field = {answer.answer_field_id: answer for answer in attempt_answers}

    total_primary = 0

    for task in tasks:
        fields = (
            db.query(AnswerField)
            .filter(AnswerField.task_id == task.id)
            .order_by(AnswerField.sort_order)
            .all()
        )

        field_results = []

        for field in fields:
            attempt_answer = answers_by_field.get(field.id)

            raw_value = attempt_answer.raw_value if attempt_answer else ""
            normalized = normalize_answer(raw_value)

            if field.input_type == "number":
                expected = parse_decimal(field.expected_answer)
                given = parse_decimal(raw_value)
                is_correct = (
                    expected is not None and given is not None and expected == given
                )
            else:
                expected = normalize_answer(field.expected_answer)
                is_correct = normalized == expected

            if attempt_answer is None:
                attempt_answer = AttemptAnswer(
                    attempt_id=attempt.id,
                    task_id=task.id,
                    answer_field_id=field.id,
                    raw_value="",
                )
                db.add(attempt_answer)

            attempt_answer.normalized_value = normalized
            attempt_answer.is_correct = is_correct

            field_score = 0
            if task.scoring_type == "partial_sum" and is_correct:
                field_score = field.points

            attempt_answer.score = field_score
            field_results.append((field, is_correct, field_score))

        if not fields:
            task_score = 0
        elif task.scoring_type == "all_or_nothing":
            all_correct = all(item[1] for item in field_results)
            task_score = task.max_score if all_correct else 0

            # Для all_or_nothing можно проставить баллы полям только если все верно.
            for field, is_correct, _ in field_results:
                answer = answers_by_field.get(field.id)
                if answer:
                    answer.score = field.points if all_correct else 0
        elif task.scoring_type == "partial_sum":
            task_score = sum(item[2] for item in field_results)
            if task_score > task.max_score:
                task_score = task.max_score
        else:
            task_score = 0

        total_primary += task_score

    attempt.primary_score = total_primary
    attempt.secondary_score = get_secondary_score(db, total_primary)


def finish_attempt(
    db: Session,
    attempt: Attempt,
    status: str,
    finish_reason: str,
) -> None:
    if attempt.status != "in_progress":
        return

    attempt.status = status
    attempt.finished_at = utcnow()
    attempt.finish_reason = finish_reason

    if attempt.started_at and attempt.finished_at:
        attempt.duration_seconds = int(
            (attempt.finished_at - attempt.started_at).total_seconds()
        )

    grade_attempt(db, attempt)
    db.commit()


# ---------------------------------------------------------------------------
# Стартовые данные
# ---------------------------------------------------------------------------


def create_default_data(db: Session) -> None:
    if not db.query(ConversionTable).count():
        table = ConversionTable(
            name="Базовая таблица",
            year=2026,
            max_primary=29,
            is_active=True,
        )
        db.add(table)
        db.flush()

        for primary in range(0, 30):
            db.add(
                ConversionEntry(
                    conversion_table_id=table.id,
                    primary_score=primary,
                    secondary_score=primary,
                )
            )

    if not db.query(Variant).count():
        variant = Variant(
            title="Демо-вариант",
            is_active=True,
        )
        db.add(variant)
        db.flush()

        task1 = Task(
            variant_id=variant.id,
            number=1,
            title="Задание 1",
            statement_text="Введите ответ ABC без пробелов.",
            max_score=1,
            scoring_type="all_or_nothing",
        )
        db.add(task1)
        db.flush()

        db.add(
            AnswerField(
                task_id=task1.id,
                code="answer",
                label="Ответ",
                input_type="string",
                sort_order=1,
                points=1,
                expected_answer="ABC",
            )
        )

        task2 = Task(
            variant_id=variant.id,
            number=2,
            title="Задание 2",
            statement_text="Введите число 1.5",
            max_score=1,
            scoring_type="all_or_nothing",
        )
        db.add(task2)
        db.flush()

        db.add(
            AnswerField(
                task_id=task2.id,
                code="answer",
                label="Ответ",
                input_type="number",
                sort_order=1,
                points=1,
                expected_answer="1.5",
            )
        )

        task3 = Task(
            variant_id=variant.id,
            number=3,
            title="Задание 3",
            statement_text="Задание с частичным баллом. Два поля по 1 баллу.",
            max_score=2,
            scoring_type="partial_sum",
        )
        db.add(task3)
        db.flush()

        db.add(
            AnswerField(
                task_id=task3.id,
                code="part1",
                label="Часть 1",
                input_type="string",
                sort_order=1,
                points=1,
                expected_answer="A",
            )
        )

        db.add(
            AnswerField(
                task_id=task3.id,
                code="part2",
                label="Часть 2",
                input_type="string",
                sort_order=2,
                points=1,
                expected_answer="B",
            )
        )

    db.commit()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_data(db)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Ученик: авторизация и попытка
# ---------------------------------------------------------------------------


@app.post("/api/student/login")
def student_login(payload: StudentLoginIn, db: Session = Depends(get_db)):
    if not normalize_text(payload.last_name):
        raise HTTPException(status_code=400, detail="Фамилия обязательна")

    if not normalize_text(payload.first_name):
        raise HTTPException(status_code=400, detail="Имя обязательно")

    cls = get_class_or_create(
        db=db,
        number=payload.class_number,
        letter=payload.class_letter,
    )

    student = get_student_or_create(
        db=db,
        cls=cls,
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
    )

    token = create_token(db, role="student", student_id=student.id)

    return {
        "token": token.token,
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "class_name": cls.display_name,
        },
    }


@app.post("/api/student/attempts/start")
def start_attempt(
    payload: StartAttemptIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = (
        db.query(Attempt)
        .filter(
            Attempt.student_id == student.id,
            Attempt.status == "in_progress",
        )
        .first()
    )

    # Если уже есть активная попытка, возвращаем ее.
    if attempt:
        # Если время вышло, сразу завершаем.
        if attempt.expires_at and attempt.expires_at <= utcnow():
            finish_attempt(db, attempt, "time_expired", "time_expired")
            db.refresh(attempt)
        else:
            return public_attempt(db, attempt, student)

    variant = choose_variant(db, student.id)
    duration_minutes = get_exam_duration_minutes(db)

    attempt = Attempt(
        student_id=student.id,
        variant_id=variant.id,
        machine_id=payload.machine_id,
        status="in_progress",
        started_at=utcnow(),
        expires_at=utcnow() + timedelta(minutes=duration_minutes),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return public_attempt(db, attempt, student)


@app.get("/api/student/attempts/{attempt_id}")
def get_attempt(
    attempt_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = db.get(Attempt, attempt_id)

    if not attempt or attempt.student_id != student.id:
        raise HTTPException(status_code=404, detail="Попытка не найдена")

    return public_attempt(db, attempt, student)


@app.put("/api/student/attempts/{attempt_id}/answers")
def save_answers(
    attempt_id: int,
    payload: SaveAnswersIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = db.get(Attempt, attempt_id)

    if not attempt or attempt.student_id != student.id:
        raise HTTPException(status_code=404, detail="Попытка не найдена")

    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Попытка уже завершена")

    save_answers_to_attempt(db, attempt, payload.answers)

    return {"ok": True}


@app.post("/api/student/attempts/{attempt_id}/finish")
def finish(
    attempt_id: int,
    payload: FinishAttemptIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = db.get(Attempt, attempt_id)

    if not attempt or attempt.student_id != student.id:
        raise HTTPException(status_code=404, detail="Попытка не найдена")

    if attempt.status != "in_progress":
        return public_attempt(db, attempt, student)

    if payload.answers:
        save_answers_to_attempt(db, attempt, payload.answers)

    reason = payload.reason or "finished"

    if reason == "time_expired":
        finish_attempt(db, attempt, "time_expired", "time_expired")
    else:
        finish_attempt(db, attempt, "finished", "finished")

    db.refresh(attempt)

    return public_attempt(db, attempt, student)


# ---------------------------------------------------------------------------
# Преподаватель: авторизация
# ---------------------------------------------------------------------------


@app.post("/api/teacher/login")
def teacher_login(payload: TeacherLoginIn, db: Session = Depends(get_db)):
    if payload.username != TEACHER_USERNAME or payload.password != TEACHER_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = create_token(db, role="teacher")

    return {
        "token": token.token,
        "username": payload.username,
    }


# ---------------------------------------------------------------------------
# Преподаватель: управление вариантами и заданиями
# ---------------------------------------------------------------------------


@app.get("/api/teacher/variants")
def list_variants(
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    variants = db.query(Variant).order_by(Variant.id.desc()).all()

    return [
        {
            "id": variant.id,
            "title": variant.title,
            "is_active": variant.is_active,
            "created_at": (
                variant.created_at.isoformat() if variant.created_at else None
            ),
        }
        for variant in variants
    ]


@app.post("/api/teacher/variants")
def create_variant(
    payload: VariantIn,
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    variant = Variant(title=payload.title, is_active=True)
    db.add(variant)
    db.commit()
    db.refresh(variant)

    return {
        "id": variant.id,
        "title": variant.title,
        "is_active": variant.is_active,
    }


@app.post("/api/teacher/variants/{variant_id}/tasks")
def create_task(
    variant_id: int,
    payload: TaskIn,
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    variant = db.get(Variant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Вариант не найден")

    task = Task(
        variant_id=variant.id,
        number=payload.number,
        title=payload.title,
        statement_text=payload.statement_text,
        instruction_text=payload.instruction_text,
        source_data_text=payload.source_data_text,
        teacher_comment=payload.teacher_comment,
        max_score=payload.max_score,
        scoring_type=payload.scoring_type,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return public_task(db, task)


@app.post("/api/teacher/tasks/{task_id}/fields")
def create_answer_field(
    task_id: int,
    payload: AnswerFieldIn,
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    field = AnswerField(
        task_id=task.id,
        code=payload.code,
        label=payload.label,
        input_type=payload.input_type,
        sort_order=payload.sort_order,
        points=payload.points,
        expected_answer=payload.expected_answer,
    )

    db.add(field)
    db.commit()
    db.refresh(field)

    return public_field(field)


# ---------------------------------------------------------------------------
# Преподаватель: результаты
# ---------------------------------------------------------------------------


@app.get("/api/teacher/attempts")
def teacher_attempts(
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    attempts = db.query(Attempt).order_by(Attempt.started_at.desc()).all()

    result = []

    for attempt in attempts:
        student = db.get(Student, attempt.student_id)
        variant = db.get(Variant, attempt.variant_id)
        cls = db.get(Class, student.class_id) if student else None

        result.append(
            {
                "id": attempt.id,
                "student_name": student.full_name if student else "Unknown",
                "class_name": cls.display_name if cls else "",
                "variant_title": variant.title if variant else "",
                "status": attempt.status,
                "started_at": (
                    attempt.started_at.isoformat() if attempt.started_at else None
                ),
                "finished_at": (
                    attempt.finished_at.isoformat() if attempt.finished_at else None
                ),
                "duration_seconds": attempt.duration_seconds,
                "primary_score": attempt.primary_score,
                "secondary_score": attempt.secondary_score,
                "finish_reason": attempt.finish_reason,
                "machine_id": attempt.machine_id,
            }
        )

    return result


@app.get("/api/teacher/attempts/{attempt_id}")
def teacher_attempt_detail(
    attempt_id: int,
    teacher: Token = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    attempt = db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Попытка не найдена")

    student = db.get(Student, attempt.student_id)
    variant = db.get(Variant, attempt.variant_id)
    cls = db.get(Class, student.class_id) if student else None

    tasks = (
        db.query(Task)
        .filter(Task.variant_id == attempt.variant_id)
        .order_by(Task.number)
        .all()
    )

    answers = (
        db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
    )

    answers_by_field = {answer.answer_field_id: answer for answer in answers}

    task_data = []

    for task in tasks:
        fields = (
            db.query(AnswerField)
            .filter(AnswerField.task_id == task.id)
            .order_by(AnswerField.sort_order)
            .all()
        )

        field_data = []

        for field in fields:
            answer = answers_by_field.get(field.id)

            field_data.append(
                {
                    "id": field.id,
                    "code": field.code,
                    "label": field.label,
                    "expected_answer": field.expected_answer,
                    "student_answer": answer.raw_value if answer else "",
                    "is_correct": answer.is_correct if answer else False,
                    "score": answer.score if answer else 0,
                }
            )

        task_score = 0
        if task.scoring_type == "all_or_nothing":
            all_correct = bool(fields) and all(
                answers_by_field.get(field.id)
                and answers_by_field.get(field.id).is_correct
                for field in fields
            )
            task_score = task.max_score if all_correct else 0
        else:
            task_score = sum(
                answers_by_field.get(field.id).score or 0
                for field in fields
                if answers_by_field.get(field.id)
            )

        task_data.append(
            {
                "id": task.id,
                "number": task.number,
                "title": task.title,
                "max_score": task.max_score,
                "score": task_score,
                "fields": field_data,
            }
        )

    return {
        "attempt": {
            "id": attempt.id,
            "status": attempt.status,
            "started_at": (
                attempt.started_at.isoformat() if attempt.started_at else None
            ),
            "finished_at": (
                attempt.finished_at.isoformat() if attempt.finished_at else None
            ),
            "duration_seconds": attempt.duration_seconds,
            "primary_score": attempt.primary_score,
            "secondary_score": attempt.secondary_score,
            "finish_reason": attempt.finish_reason,
            "machine_id": attempt.machine_id,
        },
        "student": {
            "id": student.id if student else None,
            "full_name": student.full_name if student else "Unknown",
            "class_name": cls.display_name if cls else "",
        },
        "variant": {
            "id": variant.id if variant else None,
            "title": variant.title if variant else "",
        },
        "tasks": task_data,
    }


# ---------------------------------------------------------------------------
# Веб-страница преподавателя
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Результаты экзамена</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f4f6f8;
    }
    header {
      background: #1f2937;
      color: white;
      padding: 16px 24px;
      font-size: 22px;
      font-weight: bold;
    }
    .container {
      padding: 24px;
    }
    .card {
      background: white;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    input, button {
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #d1d5db;
      font-size: 15px;
    }
    button {
      background: #2563eb;
      color: white;
      border: none;
      cursor: pointer;
    }
    button:hover {
      background: #1d4ed8;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      border-bottom: 1px solid #e5e7eb;
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #f9fafb;
    }
    .muted {
      color: #6b7280;
    }
    .error {
      color: #dc2626;
      margin-top: 10px;
    }
    .status {
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 13px;
      display: inline-block;
    }
    .status.in_progress { background: #dbeafe; color: #1d4ed8; }
    .status.finished { background: #dcfce7; color: #166534; }
    .status.time_expired { background: #fef9c3; color: #854d0e; }
    .status.aborted { background: #fee2e2; color: #991b1b; }
  </style>
</head>
<body>
  <header>Панель преподавателя</header>

  <div class="container">
    <div class="card" id="loginCard">
      <h2>Вход</h2>
      <div>
        <input id="username" placeholder="Логин" value="admin">
      </div>
      <br>
      <div>
        <input id="password" type="password" placeholder="Пароль" value="admin">
      </div>
      <br>
      <button onclick="login()">Войти</button>
      <div id="loginError" class="error"></div>
    </div>

    <div class="card" id="contentCard" style="display:none;">
      <h2>Попытки</h2>
      <button onclick="loadAttempts()">Обновить</button>
      <br><br>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Ученик</th>
            <th>Класс</th>
            <th>Вариант</th>
            <th>Статус</th>
            <th>Начало</th>
            <th>Завершение</th>
            <th>Первичный</th>
            <th>Вторичный</th>
          </tr>
        </thead>
        <tbody id="attemptsBody"></tbody>
      </table>
    </div>
  </div>

<script>
let token = localStorage.getItem('teacher_token') || '';

async function api(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  const response = await fetch(path, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || 'Ошибка запроса');
  }

  return data;
}

async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const errorBox = document.getElementById('loginError');

  errorBox.textContent = '';

  try {
    const data = await api('/api/teacher/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    token = data.token;
    localStorage.setItem('teacher_token', token);
    showDashboard();
    await loadAttempts();
  } catch (e) {
    errorBox.textContent = e.message;
  }
}

function showDashboard() {
  document.getElementById('loginCard').style.display = 'none';
  document.getElementById('contentCard').style.display = 'block';
}

async function loadAttempts() {
  try {
    const attempts = await api('/api/teacher/attempts');
    renderAttempts(attempts);
  } catch (e) {
    if (String(e.message).toLowerCase().includes('токен')) {
      token = '';
      localStorage.removeItem('teacher_token');
      document.getElementById('loginCard').style.display = 'block';
      document.getElementById('contentCard').style.display = 'none';
    }
  }
}

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

function renderAttempts(attempts) {
  const tbody = document.getElementById('attemptsBody');
  tbody.innerHTML = '';

  for (const attempt of attempts) {
    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td>${attempt.id}</td>
      <td>${attempt.student_name}</td>
      <td>${attempt.class_name || ''}</td>
      <td>${attempt.variant_title || ''}</td>
      <td><span class="status ${attempt.status}">${attempt.status}</span></td>
      <td>${formatDate(attempt.started_at)}</td>
      <td>${formatDate(attempt.finished_at)}</td>
      <td>${attempt.primary_score ?? '-'}</td>
      <td>${attempt.secondary_score ?? '-'}</td>
    `;

    tbody.appendChild(tr);
  }
}

window.onload = async function() {
  if (token) {
    showDashboard();
    await loadAttempts();
  }
};

setInterval(() => {
  if (token) {
    loadAttempts();
  }
}, 5000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML
