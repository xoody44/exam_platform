from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_admin
from ..models import User
from ..services import admin_delete as ad

router = APIRouter(prefix="/api/admin", tags=["admin-delete"])


@router.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ad.delete_student(db, admin, student_id)


@router.delete("/students")
def delete_all_students(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ad.delete_all_students(db, admin)


@router.delete("/attempts/{attempt_id}")
def delete_attempt(
    attempt_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ad.delete_attempt(db, admin, attempt_id)


@router.delete("/variants/{variant_id}")
def delete_variant(
    variant_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ad.delete_variant(db, admin, variant_id)


@router.delete("/conversion-tables/{table_id}")
def delete_conversion_table(
    table_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ad.delete_conversion_table(db, admin, table_id)
