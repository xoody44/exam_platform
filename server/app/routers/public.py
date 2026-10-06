from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SchoolOut
from ..services.schools import list_schools
from ..services.settings import get_setting

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/schools", response_model=list[SchoolOut])
def get_schools(db: Session = Depends(get_db)):
    """список школ для формы входа ученика"""
    return list_schools(db)

@router.get("/exam-info")
def get_exam_info(db: Session = Depends(get_db)):
    """публичная информация о длительности экзамена"""
    return {"exam_duration_minutes": int(get_setting(db, "exam_duration_minutes"))}