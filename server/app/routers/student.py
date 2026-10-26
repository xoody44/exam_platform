import json
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..exceptions import bad_request, not_found
from ..services.code_runner import run_code_tests

logger = logging.getLogger("exam.router.student")

from ..database import get_db
from ..dependencies import require_student
from ..models import (
    STATUS_IN_PROGRESS,
    TASK_TYPE_CODE,
    AttemptCodeSubmission,
    CodeTest,
    Student,
    Task,
)
from ..schemas import (
    AttemptResultOut,
    AttemptStateOut,
    CodeRunOut,
    CodeSubmitIn,
    CodeTestResultOut,
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
    """вход ученика по ФИО и школе"""
    return student_login(db, payload)


@router.post("/attempts/start", response_model=AttemptStateOut)
def start_attempt(
    payload: StartAttemptIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    """начать попытку: выбирает вариант и создаёт Attempt"""
    logger.info(
        "POST /api/student/attempts/start вызван student=%s machine=%s",
        student.id,
        payload.machine_id,
    )
    return attempt_service.start_attempt(db, student, payload.machine_id)


@router.get("/attempts/{attempt_id}", response_model=AttemptStateOut)
def get_attempt_state(
    attempt_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    """текущее состояние попытки для восстановления экрана после перезапуска"""
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.build_state(db, attempt)


@router.put("/attempts/{attempt_id}/answers")
def save_answers(
    attempt_id: int,
    payload: SaveAnswersIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    """автосохранение ответов ученика"""
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
    """приём событий телеметрии с клиента ученика"""
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
    """завершение попытки с подсчётом баллов"""
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.finish_attempt(db, attempt, payload.reason, payload.answers)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResultOut)
def get_attempt_result(
    attempt_id: int,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    """результаты завершённой попытки для экрана итогов"""
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    return attempt_service.build_result(db, attempt)


@router.put("/attempts/{attempt_id}/tasks/{task_id}/code", response_model=CodeRunOut)
def submit_code(
    attempt_id: int,
    task_id: int,
    payload: CodeSubmitIn,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    attempt = attempt_service.get_attempt_for_student(db, attempt_id, student)
    if attempt.status != STATUS_IN_PROGRESS:
        raise bad_request("попытка завершена, отправлять код нельзя")

    task = db.get(Task, task_id)
    if (
        task is None
        or task.variant_id != attempt.variant_id
        or task.task_type != TASK_TYPE_CODE
    ):
        raise not_found("задание не найдено")

    submission = (
        db.query(AttemptCodeSubmission)
        .filter(
            AttemptCodeSubmission.attempt_id == attempt.id,
            AttemptCodeSubmission.task_id == task.id,
        )
        .first()
    )
    if submission is None:
        submission = AttemptCodeSubmission(attempt_id=attempt.id, task_id=task.id)
        db.add(submission)
    submission.language = payload.language
    submission.source_code = payload.source_code
    db.commit()

    if not payload.run:
        stored = json.loads(submission.results_json) if submission.results_json else []
        return CodeRunOut(
            tests=[CodeTestResultOut(**r) for r in stored],
            all_passed=submission.all_passed,
            compile_log=None,
        )

    tests = (
        db.query(CodeTest)
        .filter(CodeTest.task_id == task.id)
        .order_by(CodeTest.sort_order)
        .all()
    )
    results, _compile_log = run_code_tests(
        db=db,
        language=payload.language,
        source=payload.source_code,
        tests=tests,
    )
    submission.results_json = json.dumps(
        [r.to_dict() for r in results], ensure_ascii=False
    )
    submission.all_passed = bool(results) and all(r.passed for r in results)
    db.commit()

    return CodeRunOut(
        tests=[
            CodeTestResultOut(
                test_id=r.test_id, name=r.name, status=r.status, passed=r.passed
            )
            for r in results
        ],
        all_passed=submission.all_passed,
        compile_log=None,
    )
