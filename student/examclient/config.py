import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class AppConfig:
    server_url: str
    machine_id: str
    autosave_seconds: int = 20
    sync_seconds: int = 30


def load_config() -> AppConfig:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return AppConfig(
        server_url=data["server_url"].rstrip("/"),
        machine_id=data.get("machine_id", "pc-unknown"),
        autosave_seconds=int(data.get("autosave_seconds", 20)),
        sync_seconds=int(data.get("sync_seconds", 30)),
    )
