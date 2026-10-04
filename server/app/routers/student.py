import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

logger = logging.getLogger("exam.router.student")

from ..database import get_db
from ..dependencies import require_student
from ..models import Student
from ..schemas import (
    AttemptResultOut,
    AttemptStateOut,
    FinishAttemptIn,
    SaveAnswersIn,
    SendEventsIn,
    StartAttemptIn,
    StudentLoginIn,
    StudentLoginOut,
)
from ..services import attempt as attempt_service
from ..services.auth import student_login

router = APIRouter(prefix="/api/student", tags=["student"])


@router.post("/login", response_model=StudentLoginOut)
def login(payload: StudentLoginIn, db: Session = Depends(get_db)):
    return student_login(db, payload)


@router.post("/attempts/start", response_model=AttemptStateOut)
def start_attempt(
    payload: StartAttemptIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    logger.info("POST /api/student/attempts/start вызван student=%s machine=%s",
                student.id, payload.machine_id)
    return attempt_service.start_attempt(db, student, payload.machine_id)


@router.get("/attempts/{attempt_id}", response_model=AttemptStateOut)
def get_attempt_state(
    attempt_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.build_state(db, attempt)


@router.put("/attempts/{attempt_id}/answers")
def save_answers(
    attempt_id: int,
    payload: SaveAnswersIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    saved = attempt_service.save_answers(db, attempt, payload.answers)
    return {"saved": saved}


@router.post("/attempts/{attempt_id}/events")
def send_events(
    attempt_id: int,
    payload: SendEventsIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    received = attempt_service.send_events(db, attempt, student, payload.events)
    return {"received": received}


@router.post("/attempts/{attempt_id}/finish", response_model=AttemptResultOut)
def finish_attempt(
    attempt_id: int,
    payload: FinishAttemptIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.finish_attempt(db, attempt, payload.reason, payload.answers)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResultOut)
def get_attempt_result(
    attempt_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.build_result(db, attempt)