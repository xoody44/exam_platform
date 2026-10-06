from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AdminLoginOut, AdminLogIn
from ..services.auth import admin_login

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AdminLoginOut)
def login(payload: AdminLogIn, db: Session = Depends(get_db)):
    """вход администратора, возвращает токен и данные пользователя"""
    return admin_login(db, payload.username, payload.password)
