from dataclasses import dataclass, field
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


@dataclass
class SessionState:
    student: dict | None = None
    attempt: dict | None = None
    tasks: dict = field(default_factory=dict)
    instruction: str = ""
    answers: dict = field(default_factory=dict)
    expires_at: datetime | None = None
    offline_events: list = field(default_factory=list)
    finished: bool = False

    @property
    def attempt_id(self) -> int | None:
        return self.attempt["id"] if self.attempt else None


    @property
    def active(self) -> bool:
        return self.attempt is not None and not self.finished


    def load_attempt(self, data: dict) -> None:
        self.attempt = data["attempt"]
        self.tasks = data["tasks"]
        self.instruction = data.get("instruction_text", "")
        self.expires_at = parse_iso(self.attempt.get("expires_at"))


    def collect_answers(self) -> list[dict]:
        result = []
        for task in self.tasks:
            for item in task.get("fields", []):
                result.append(
                    {
                        "task_id": task["id"],
                        "field_id": item["id"],
                        "value": self.answers.get(item["id"], "")
                    }
                )
        return result

    def is_task_answered(self, task: dict) -> bool:
        return any(
            self.answers.get(item["id"], "").strip() for item in task.get("fields", [])
        )
