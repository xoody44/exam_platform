from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_admin
from ..models import User
from ..schemas import (
    AttemptDetailOut,
    AttemptFilters,
    AttemptsListOut,
    ClearResultsIn,
    ClearResultsOut,
    DashboardOut,
    StatsOut,
    StudentWithAttemptsOut,
    StudentsListOut,
)
from ..services import admin_results as ar

router = APIRouter(prefix="/api/admin", tags=["admin-results"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ar.get_dashboard(db)


@router.get("/attempts", response_model=AttemptsListOut)
def list_attempts(
    school_id: int | None = None,
    variant_id: int | None = None,
    status: str | None = None,
    min_primary: int | None = None,
    max_primary: int | None = None,
    min_test: int | None = None,
    max_test: int | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="started_at"),
    sort_order: str = Query(default="desc"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    filters = AttemptFilters(
        school_id=school_id,
        variant_id=variant_id,
        status=status,
        min_primary=min_primary,
        max_primary=max_primary,
        min_test=min_test,
        max_test=max_test,
        search=search,
    )
    return ar.list_attempts(db, filters, page, per_page, sort_by, sort_order)


@router.get("/attempts/{attempt_id}", response_model=AttemptDetailOut)
def get_attempt_detail(
    attempt_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ar.get_attempt_detail(db, attempt_id)


@router.get("/students", response_model=StudentsListOut)
def list_students(
    search: str | None = None,
    school_id: int | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ar.list_students(db, search, school_id, page, per_page)


@router.get("/students/{student_id}/attempts")
def get_student_attempts(
    student_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    filters = AttemptFilters()
    filters.student_id = student_id
    return ar.list_attempts(db, filters, page, per_page, "started_at", "desc")


@router.get("/stats", response_model=StatsOut)
def get_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ar.get_stats(db)


@router.post("/results/clear", response_model=ClearResultsOut)
def clear_results(
    payload: ClearResultsIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ar.clear_results(
        db,
        admin,
        payload.mode,
        attempt_id=payload.attempt_id,
        student_id=payload.student_id,
        status=payload.status,
        variant_id=payload.variant_id,
    )