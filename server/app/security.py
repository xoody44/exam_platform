from datetime import datetime, timedelta, timezone

import logging
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from .config import get_settings

logger = logging.getLogger("exam.security")
ALGORITH = "HS256"

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerificationError, VerifyMismatchError):
        return False


def create_access_token(subject: str, role: str, **extra: object) -> str:
    import logging
    logger = logging.getLogger("exam.security")

    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=s.acess_token_expire_minutes),
    }
    payload.update(extra)

    logger.info("create_access_token: payload перед encode = %s", payload)

    return jwt.encode(payload, s.secret_key, algorithm=ALGORITH)


def decode_access_token(token: str) -> dict | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.secret_key, algorithms=[ALGORITH])
    except jwt.PyJWTError as e:
        logger.warning("JWT decode failed: %s: %s", type(e).__name__, e)
        return None
