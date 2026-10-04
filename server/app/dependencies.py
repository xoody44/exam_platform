import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .exceptions import forbidden, unauthorized
from .models import ROLE_ADMIN, ROLE_STUDENT, Student, User
from .security import decode_access_token

logger = logging.getLogger("exam.auth")
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or not credentials.credentials:
        logger.warning("отсутствует заголовок Authorization")
        raise unauthorized("отсутствует заголовок Authorization")

    token = credentials.credentials.strip()
    logger.info("получен токен длиной %d символов, начинается с %s...", len(token), token[:20])

    payload = decode_access_token(token)
    if payload is None:
        from .config import get_settings
        s = get_settings()
        logger.error(
            "токен не прошёл проверку. Секрет сервера: %s...%s",
            s.secret_key[:8],
            s.secret_key[-4:],
        )
        raise unauthorized("токен недействителен или истёк")

    logger.info("токен расшифрован: sub=%s, role=%s", payload.get("sub"), payload.get("role"))
    return payload


def require_admin(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    if payload.get("role") != ROLE_ADMIN:
        raise forbidden("требуются права администратора")

    uid = payload.get("uid")
    user = db.get(User, int(uid)) if uid is not None else None
    if user is None or not user.is_active:
        raise unauthorized("пользователь не найден или отключён")

    return user


def require_student(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> Student:
    if payload.get("role") != ROLE_STUDENT:
        raise forbidden("Эндпоинт доступен только ученику")

    uid = payload.get("uid")
    logger.info("require_student: payload=%s", payload)
    logger.info("require_student: uid=%s, type=%s", uid, type(uid).__name__ if uid is not None else "None")

    student = db.get(Student, int(uid)) if uid is not None else None
    logger.info("require_student: db.get result = %s", student)

    if student is None:
        # Диагностика: проверим, есть ли вообще такой студент в базе
        all_students = db.query(Student).all()
        logger.error(
            "Ученик не найден! uid=%s. Всего учеников в базе: %d. IDs: %s",
            uid,
            len(all_students),
            [s.id for s in all_students],
        )
        raise unauthorized("Ученик не найден")

    return student