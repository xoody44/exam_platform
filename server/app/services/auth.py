from sqlalchemy.orm import Session

from ..config import get_settings
from ..exceptions import not_found, unauthorized
from ..models import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    School,
    Student,
    User,
    utcnow,
)
from ..schemas import (
    AdminInfoOut,
    AdminLoginOut,
    StudentLoginIn,
    StudentLoginOut,
    StudentOut,
)

from ..security import create_access_token, hash_password, verify_password
from .audit import log_action


def ensure_default_admin(db: Session) -> None:
    if db.query(User).count() > 0:
        return

    s = get_settings()
    db.add(
        User(
            username=s.default_admin_username,
            password_hash=hash_password(s.default_admin_password),
        )
    )
    db.commit()


def admin_login(db: Session, username: str, password: str) -> AdminLoginOut:
    user = db.query(User).filter(User.username == username).first()

    if user is None or not verify_password(password, user.password_hash):
        raise unauthorized("неверный логин или пароль")

    if not user.is_active:
        raise unauthorized("пользователь отключен")

    user.last_login_at = utcnow()
    db.commit()
    db.refresh(user)

    token = create_access_token(
        subject=f"user:{user.id}",
        role=ROLE_ADMIN,
        uid=user.id,
    )

    log_action(db, user.id, "login", entity_type="user", entity_id=user.id)

    return AdminLoginOut(
        access_token=token,
        user=AdminInfoOut.model_validate(user),
    )


def get_or_create_student(
    db: Session,
    school: School,
    payload: StudentLoginIn,
) -> Student:
    parts = [payload.last_name, payload.first_name]
    if payload.middle_name:
        parts.append(payload.middle_name)

    full_name = " ".join(parts)
    normalized_name = full_name.lower()

    student = (
        db.query(Student)
        .filter(
            Student.school_id == school.id,
            Student.normalized_name == normalized_name,
        )
        .first()
    )

    if student is not None:
        student.last_seen_at = utcnow()
        db.commit()
        db.refresh(student)
        return student

    student = Student(
        school_id=school.id,
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        full_name=full_name,
        normalized_name=normalized_name,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def student_login(db: Session, payload: StudentLoginIn) -> StudentLoginOut:
    school = db.get(School, payload.school_id)
    if school is None:
        raise not_found("Школа не найдена")

    student = get_or_create_student(db, school, payload)

    import logging
    logger = logging.getLogger("exam.auth")
    logger.info("student_login: создан/найден ученик id=%s, full_name=%s", student.id, student.full_name)

    token = create_access_token(
        subject=f"student:{student.id}",
        role=ROLE_STUDENT,
        uid=student.id,
    )

    logger.info("student_login: токен создан для student.id=%s", student.id)

    return StudentLoginOut(
        access_token=token,
        student=StudentOut(
            id=student.id,
            full_name=student.full_name,
            school_name=school.name,
        ),
    )
