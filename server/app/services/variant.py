import random

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..exceptions import bad_request
from ..models import Attempt, Variant


def choose_variant(db: Session, student_id: int) -> Variant:
    active = (
        db.query(Variant)
        .filter(
            Variant.is_active.is_(True),
            Variant.archived_at.is_(None),
        )
        .all()
    )
    if not active:
        raise bad_request("Нет доступных активных вариантов")

    taken = {
        row.variant_id
        for row in db.query(Attempt.variant_id)
        .filter(
            Attempt.student_id == student_id,
            Attempt.variant_id.isnot(None),
        )
        .all()
    }
    unseen = [v for v in active if v.id not in taken]

    candidates = unseen if unseen else active

    candidate_ids = [v.id for v in candidates]
    load_rows = (
        db.query(Attempt.variant_id, func.count(Attempt.id))
        .filter(Attempt.variant_id.in_(candidate_ids))
        .group_by(Attempt.variant_id)
        .all()
    )
    load_map = dict(load_rows)

    min_load = min(load_map.get(v.id, 0) for v in candidates)

    best = [v for v in candidates if load_map.get(v.id, 0) == min_load]
    return random.choice(best)
