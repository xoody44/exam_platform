import json
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BROWSER_BLACKLIST = [
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "browser.exe",
    "yandex.exe", "yandexbrowser.exe", "brave.exe", "vivaldi.exe",
    "iexplore.exe", "tor.exe", "waterfox.exe", "palemoon.exe", "epic.exe",
    "arc.exe", "maxthon.exe", "360se.exe", "360chrome.exe", "qqbrowser.exe",
    "ucbrowser.exe", "whale.exe", "sleipnir.exe",
]


def _config_dir() -> Path:
    """Папка с конфигом: рядом с exe в упакованном режиме, student/ в dev."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = _config_dir() / "config.json"


@dataclass
class AppConfig:
    server_url: str
    machine_id: str
    autosave_seconds: int = 20
    sync_seconds: int = 30
    locker_enabled: bool = True
    locker_poll_ms: int = 800
    locker_blacklist: list = field(
        default_factory=lambda: list(DEFAULT_BROWSER_BLACKLIST)
    )


def _default_machine_id() -> str:
    try:
        return (socket.gethostname() or "pc-unknown").lower()
    except OSError:
        return "pc-unknown"


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig(server_url="", machine_id=_default_machine_id())
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return AppConfig(server_url="", machine_id=_default_machine_id())

    locker = data.get("locker", {}) or {}
    return AppConfig(
        server_url=(data.get("server_url") or "").rstrip("/"),
        machine_id=data.get("machine_id") or _default_machine_id(),
        autosave_seconds=int(data.get("autosave_seconds", 20)),
        sync_seconds=int(data.get("sync_seconds", 30)),
        locker_enabled=bool(locker.get("enabled", True)),
        locker_poll_ms=int(locker.get("poll_ms", 800)),
        locker_blacklist=list(locker.get("blacklist", DEFAULT_BROWSER_BLACKLIST)),
    )


def save_config(config: AppConfig) -> None:
    data = {
        "server_url": config.server_url,
        "machine_id": config.machine_id,
        "autosave_seconds": config.autosave_seconds,
        "sync_seconds": config.sync_seconds,
        "locker": {
            "enabled": config.locker_enabled,
            "poll_ms": config.locker_poll_ms,
            "blacklist": config.locker_blacklist,
        },
    }
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )