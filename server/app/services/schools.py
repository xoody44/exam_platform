from sqlalchemy.orm import Session

from ..models import School
from ..schemas import SchoolOut


def list_schools(db: Session) -> list[SchoolOut]:
    schools = db.query(School).order_by(School.name).all()
    return [SchoolOut.model_validate(s) for s in schools]
