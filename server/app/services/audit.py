import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import ActionLog


def log_action(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        ActionLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=(
                json.dumps(payload, ensure_ascii=False, default=str)
                if payload is not None
                else None
            ),
        )
    )
    db.commit()
