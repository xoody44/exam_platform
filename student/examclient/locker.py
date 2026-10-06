from datetime import datetime, timezone
from pathlib import Path

import psutil
from PyQt6.QtCore import QThread, pyqtSignal


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrowserLockerThread(QThread):
    browser_killed = pyqtSignal(str, int)

    def __init__(
        self,
        blacklist: list[str],
        poll_ms: int = 800,
        log_path: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._blacklist = {name.lower() for name in blacklist}
        self._poll_ms = max(int(poll_ms), 200)
        self._log_path = log_path
        self._running = False

    def _log(self, message: str) -> None:
        if self._log_path is None:
            return
        try:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{now_iso()} {message}\n")
        except OSError:
            pass

    def start_lock(self) -> None:
        if self.isRunning():
            return
        self._log(f"lock START blacklist={sorted(self._blacklist)} poll_ms={self._poll_ms}")
        self.start()

    def stop_lock(self, reason: str) -> None:
        if not self.isRunning():
            return
        self._running = False
        self.wait(2000)
        self._log(f"lock STOP reason={reason}")

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                for proc in psutil.process_iter(["name", "pid"]):
                    if not self._running:
                        break
                    name = (proc.info.get("name") or "").lower()
                    if name not in self._blacklist:
                        continue
                    pid = proc.info.get("pid") or 0
                    try:
                        proc.kill()
                        self._log(f"killed {name} pid={pid}")
                        self.browser_killed.emit(name, pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as exc:
                        self._log(f"kill failed {name} pid={pid}: {exc}")
            except Exception as exc:
                self._log(f"iter failed: {exc}")
            self.msleep(self._poll_ms)