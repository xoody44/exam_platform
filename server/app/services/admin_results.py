import math
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..exceptions import bad_request, not_found
from ..models import (
    STATUS_ABORTED,
    STATUS_FINISHED,
    STATUS_TIME_EXPIRED,
    AnswerField,
    Attempt,
    AttemptAnswer,
    ConversionTable,
    School,
    Student,
    Task,
    User,
    Variant,
    utcnow,
)
from ..schemas import (
    AdminAnswerOut,
    AdminTaskResultOut,
    AttemptDetailOut,
    AttemptFilters,
    AttemptListItemOut,
    AttemptsListOut,
    ClearResultsOut,
    DashboardOut,
    PaginatedOut,
    ScoresOut,
    StatsOut,
    StatsOverviewOut,
    StatsTaskOut,
    StudentOut,
    StudentWithAttemptsOut,
    StudentsListOut,
)
from .audit import log_action

FINISHED_STATUSES = (STATUS_FINISHED, STATUS_TIME_EXPIRED)


def _paginate(total: int, page: int, per_page: int) -> PaginatedOut:
    return PaginatedOut(
        page=page,
        per_page=per_page,
        total=total,
        pages=math.ceil(total / per_page) if total else 0,
    )



def get_dashboard(db: Session) -> DashboardOut:
    students_count = db.query(Student).count()

    active_q = db.query(Attempt).filter(Attempt.deleted_at.is_(None))
    in_progress = active_q.filter(Attempt.status == "in_progress").count()
    finished = active_q.filter(Attempt.status.in_(FINISHED_STATUSES)).count()
    aborted = active_q.filter(Attempt.status == STATUS_ABORTED).count()
    variants_active = (
        db.query(Variant)
        .filter(Variant.is_active.is_(True), Variant.archived_at.is_(None))
        .count()
    )

    return DashboardOut(
        students_count=students_count,
        attempts_in_progress=in_progress,
        attempts_finished=finished,
        attempts_aborted=aborted,
        variants_active=variants_active,
    )



def list_attempts(
    db: Session,
    filters: AttemptFilters,
    page: int,
    per_page: int,
    sort_by: str,
    sort_order: str,
) -> AttemptsListOut:
    query = (
        db.query(Attempt)
        .join(Student, Attempt.student_id == Student.id)
        .options(selectinload(Attempt.student).selectinload(Student.school))
        .options(selectinload(Attempt.variant))
        .filter(Attempt.deleted_at.is_(None))
    )

    if filters.student_id is not None:
        query = query.filter(Attempt.student_id == filters.student_id)

    if filters.school_id is not None:
        query = query.filter(Student.school_id == filters.school_id)

    if filters.school_id is not None:
        query = query.filter(Student.school_id == filters.school_id)

    if filters.variant_id is not None:
        query = query.filter(Attempt.variant_id == filters.variant_id)

    if filters.status is not None:
        query = query.filter(Attempt.status == filters.status)

    if filters.min_primary is not None:
        query = query.filter(Attempt.primary_score >= filters.min_primary)
    if filters.max_primary is not None:
        query = query.filter(Attempt.primary_score <= filters.max_primary)

    if filters.min_test is not None:
        query = query.filter(Attempt.test_score >= filters.min_test)
    if filters.max_test is not None:
        query = query.filter(Attempt.test_score <= filters.max_test)

    if filters.search:
        search = f"%{filters.search.lower()}%"
        query = query.filter(Student.normalized_name.like(search))

    total = query.count()

    sort_column = {
        "started_at": Attempt.started_at,
        "finished_at": Attempt.finished_at,
        "student_name": Student.full_name,
        "primary_score": Attempt.primary_score,
        "test_score": Attempt.test_score,
        "status": Attempt.status,
        "duration_seconds": Attempt.duration_seconds,
    }.get(sort_by, Attempt.started_at)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    attempts = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for a in attempts:
        items.append(
            AttemptListItemOut(
                id=a.id,
                student_full_name=a.student.full_name,
                school_name=a.student.school.name,
                variant_title=a.variant.title if a.variant else "",
                status=a.status,
                started_at=a.started_at,
                finished_at=a.finished_at,
                duration_seconds=a.duration_seconds,
                primary_score=a.primary_score,
                test_score=a.test_score,
                machine_id=a.machine_id,
            )
        )

    return AttemptsListOut(
        items=items,
        pagination=_paginate(total, page, per_page),
    )



def get_attempt_detail(db: Session, attempt_id: int) -> AttemptDetailOut:
    attempt = (
        db.query(Attempt)
        .options(
            selectinload(Attempt.student).selectinload(Student.school),
            selectinload(Attempt.variant),
        )
        .filter(Attempt.id == attempt_id, Attempt.deleted_at.is_(None))
        .first()
    )
    if attempt is None:
        raise not_found("попытка не найдена")

    tasks = (
        db.query(Task)
        .options(selectinload(Task.fields))
        .filter(Task.variant_id == attempt.variant_id)
        .order_by(Task.number)
        .all()
    )

    answers = {
        aa.answers_field_id: aa
        for aa in db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    }

    graded = attempt.status in FINISHED_STATUSES
    max_primary = 0

    task_results: list[AdminTaskResultOut] = []
    for task in tasks:
        max_primary += task.max_score
        task_answers: list[AdminAnswerOut] = []
        task_score = 0

        for f in task.fields:
            aa = answers.get(f.id)
            task_answers.append(
                AdminAnswerOut(
                    field_id=f.id,
                    field_label=f.label,
                    input_type=f.input_type,
                    student_answer=aa.raw_value if aa else "",
                    expected_answer=f.expected_answer,
                    is_correct=aa.is_correct if aa else False,
                    score=aa.score if aa else None,
                )
            )

        if graded:
            for f in task.fields:
                aa = answers.get(f.id)
                task_score += aa.score or 0 if aa else 0

        task_results.append(
            AdminTaskResultOut(
                task_id=task.id,
                number=task.number,
                title=task.title,
                score=task_score if graded else 0,
                max_score=task.max_score,
                answers=task_answers,
            )
        )

    max_test: int | None = None
    conversion_name: str | None = None
    if attempt.conversion_table_id is not None:
        table = db.get(ConversionTable, attempt.conversion_table_id)
        if table is not None:
            conversion_name = table.name
            max_test = max((e.test_score for e in table.entries), default=None)

    scores = ScoresOut(
        primary_score=attempt.primary_score if graded else None,
        max_primary_score=max_primary,
        test_score=attempt.test_score if graded else None,
        max_test_score=max_test if graded else None,
        conversion_table_id=attempt.conversion_table_id if graded else None,
    )

    return AttemptDetailOut(
        attempt=attempt,
        student=StudentOut(
            id=attempt.student.id,
            full_name=attempt.student.full_name,
            school_name=attempt.student.school.name,
        ),
        variant_title=attempt.variant.title if attempt.variant else "",
        conversion_table_name=conversion_name,
        scores=scores,
        tasks=task_results,
    )



def list_students(
    db: Session,
    search: str | None,
    school_id: int | None,
    page: int,
    per_page: int,
) -> StudentsListOut:
    query = (
        db.query(Student)
        .options(selectinload(Student.school))
        .outerjoin(Attempt)
        .group_by(Student.id)
    )

    if search:
        query = query.filter(Student.normalized_name.like(f"%{search.lower()}%"))

    if school_id is not None:
        query = query.filter(Student.school_id == school_id)

    total = query.count()

    students = (
        query.order_by(Student.full_name.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items: list[StudentWithAttemptsOut] = []
    for s in students:
        attempts = (
            db.query(Attempt)
            .filter(
                Attempt.student_id == s.id,
                Attempt.deleted_at.is_(None),
            )
            .order_by(Attempt.started_at.desc())
            .all()
        )
        best = max(
            (a.primary_score for a in attempts if a.primary_score is not None),
            default=None,
        )
        last = attempts[0].started_at if attempts else None

        items.append(
            StudentWithAttemptsOut(
                id=s.id,
                full_name=s.full_name,
                school_name=s.school.name,
                attempts_count=len(attempts),
                last_attempt_at=last,
                best_primary_score=best,
            )
        )

    return StudentsListOut(
        items=items,
        pagination=_paginate(total, page, per_page),
    )



def get_stats(db: Session) -> StatsOut:
    finished = (
        db.query(Attempt)
        .filter(
            Attempt.deleted_at.is_(None),
            Attempt.status.in_(FINISHED_STATUSES),
            Attempt.primary_score.isnot(None),
        )
        .all()
    )

    if not finished:
        return StatsOut(
            overview=StatsOverviewOut(
                attempts_count=0,
                avg_primary=None,
                avg_test=None,
                min_primary=None,
                min_test=None,
                max_primary=None,
                max_test=None,
            ),
            tasks=[],
        )

    primaries = [a.primary_score for a in finished]
    tests = [a.test_score for a in finished if a.test_score is not None]

    overview = StatsOverviewOut(
        attempts_count=len(finished),
        avg_primary=sum(primaries) / len(primaries),
        avg_test=(sum(tests) / len(tests)) if tests else None,
        min_primary=min(primaries),
        min_test=min(tests) if tests else None,
        max_primary=max(primaries),
        max_test=max(tests) if tests else None,
    )

    task_stats: dict[int, dict] = {}
    variant_ids = {a.variant_id for a in finished}
    tasks = (
        db.query(Task)
        .filter(Task.variant_id.in_(variant_ids))
        .order_by(Task.number)
        .all()
    )
    for t in tasks:
        task_stats[t.id] = {
            "number": t.number,
            "title": t.title,
            "max_score": t.max_score,
            "score_sum": 0,
            "count": 0,
        }

    for a in finished:
        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == a.id).all()
        for aa in answers:
            if aa.task_id in task_stats:
                task_stats[aa.task_id]["score_sum"] += aa.score or 0
                task_stats[aa.task_id]["count"] += 1

    task_out: list[StatsTaskOut] = []
    for t in tasks:
        s = task_stats[t.id]
        count = s["count"]
        if count == 0:
            completion = 0.0
            avg = 0.0
        else:
            completion = (s["score_sum"] / (s["max_score"] * count)) * 100
            avg = s["score_sum"] / count
        task_out.append(
            StatsTaskOut(
                task_number=s["number"],
                title=s["title"],
                max_score=s["max_score"],
                completion_percent=round(completion, 2),
                avg_score=round(avg, 2),
            )
        )

    task_out.sort(key=lambda x: x.completion_percent)

    return StatsOut(overview=overview, tasks=task_out)


def clear_results(
    db: Session,
    user: User,
    mode: str,
    attempt_id: int | None = None,
    student_id: int | None = None,
    status: str | None = None,
    variant_id: int | None = None,
) -> ClearResultsOut:
    now = utcnow()
    query = db.query(Attempt).filter(Attempt.deleted_at.is_(None))

    if mode == "attempt":
        if attempt_id is None:
            raise bad_request("attempt_id обязателен для mode=attempt")
        query = query.filter(Attempt.id == attempt_id)
    elif mode == "student":
        if student_id is None:
            raise bad_request("student_id обязателен для mode=student")
        query = query.filter(Attempt.student_id == student_id)
    elif mode == "filter":
        if status is not None:
            query = query.filter(Attempt.status == status)
        if variant_id is not None:
            query = query.filter(Attempt.variant_id == variant_id)
    elif mode == "all":
        pass
    else:
        raise bad_request(f"неизвестный mode: {mode}")

    ids = [row.id for row in query.with_entities(Attempt.id).all()]
    if not ids:
        return ClearResultsOut(deleted_count=0, deleted_ids=[])

    db.query(Attempt).filter(Attempt.id.in_(ids)).update(
        {Attempt.deleted_at: now}, synchronize_session=False
    )
    db.commit()

    log_action(
        db,
        user.id,
        "clear_results",
        "attempts",
        None,
        {
            "mode": mode,
            "deleted_count": len(ids),
            "deleted_ids": ids[:50],
            "attempt_id": attempt_id,
            "student_id": student_id,
            "status": status,
            "variant_id": variant_id,
        },
    )

    return ClearResultsOut(deleted_count=len(ids), deleted_ids=ids)