from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SchoolOut
from ..services.schools import list_schools

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/schools", response_model=list[SchoolOut])
def get_schools(db: Session = Depends(get_db)):
    return list_schools(db)