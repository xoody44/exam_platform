from dataclasses import dataclass
from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def make_event(event_type: str, payload: dict | None = None) -> dict:
    return {
        "event_type": event_type,
        "payload": payload,
        "client_timestamp": now_utc().isoformat(),
    }