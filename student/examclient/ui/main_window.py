import json
import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from ..api import ApiError, ExamApi
from ..config import AppConfig, CONFIG_PATH
from ..session import SessionState, make_event, now_utc
from ..worker import NetworkWorker
from ..locker import BrowserLockerThread
from .exam_page import ExamPage
from .login_page import LoginPage
from .prestart_page import PrestartPage
from .result_page import ResultPage
from .dialogs import ask_yes_no


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.api = ExamApi(config.server_url)
        self.session = SessionState()
        self.setWindowTitle("Экзамен - ученик")
        self.resize(1200, 800)

        self.worker = NetworkWorker()
        self.worker.task_done.connect(self._on_task_done)
        self.worker.start()

        self.locker = BrowserLockerThread(
            blacklist=config.locker_blacklist,
            poll_ms=config.locker_poll_ms,
            log_path=CONFIG_PATH.parent / "locker.log",
            parent=self,
        )
        self.locker.browser_killed.connect(self._on_browser_killed)
        self._last_kill_event_ts = 0.0

        self.stack = QStackedWidget()
        self.login_page = LoginPage(self.api)
        self.prestart_page = PrestartPage()
        self.exam_page = ExamPage(self.session)
        self.result_page = ResultPage()
        self.login_page.exit_requested.connect(self.close)
        for page in (self.login_page, self.prestart_page, self.exam_page, self.result_page):
            self.stack.addWidget(page)
        self.setCentralWidget(self.stack)

        self.login_page.logged_in.connect(self._on_logged_in)
        self.prestart_page.start_requested.connect(self._start_exam)
        self.prestart_page.exit_requested.connect(self.close)
        self.exam_page.answer_changed.connect(self._on_answer_changed)
        self.exam_page.task_opened.connect(self._on_task_opened)
        self.exam_page.finish_requested.connect(self._request_finish)
        self.exam_page.download_requested.connect(self._download_file)
        self.result_page.exit_requested.connect(self.close)

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._tick)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(config.autosave_seconds * 1000)
        self.autosave_timer.timeout.connect(self._autosave)

        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(config.sync_seconds * 1000)
        self.sync_timer.timeout.connect(self._sync)

        self._last_snapshot: list[dict] = []
        self._answer_event_ts: dict[int, float] = {}

    def emit_event(self, event_type: str, payload: dict | None = None) -> None:
        if not self.session.active:
            return
        self.session.offline_events.append(make_event(event_type, payload))
        if len(self.session.offline_events) > 500:
            self.session.offline_events.pop(0)

    def _on_browser_killed(self, name: str, pid: int) -> None:
        now = now_utc().timestamp()
        if now - self._last_kill_event_ts > 10:
            self._last_kill_event_ts = now
            self.emit_event("browser_killed", {"process": name, "pid": pid})

    def _stop_locker(self, reason: str) -> None:
        if self.locker.isRunning():
            self.locker.stop_lock(reason=reason)
            self.emit_event("block_finished", {"reason": reason})

    def _on_logged_in(self, student: dict) -> None:
        self.session.student = student
        self.emit_event("student_login", {"student_id": student["id"]})
        self.worker.submit("exam_info", self.api.get_exam_info)

    def _start_exam(self) -> None:
        self.prestart_page.set_busy(True)
        self.worker.submit(
            "start", lambda: self.api.start_attempt(self.config.machine_id)
        )

    def _enter_exam(self, data: dict) -> None:
        self.session.load_attempt(data)
        if self.config.locker_enabled:
            self.locker.start_lock()
            self.emit_event("block_started", {"machine_id": self.config.machine_id})
        self.exam_page.populate()
        self.exam_page.set_status("Экзамен идёт")
        self.tick_timer.start()
        self.autosave_timer.start()
        self.sync_timer.start()
        self.stack.setCurrentWidget(self.exam_page)
        self.showFullScreen()

    def _on_answer_changed(self, field_id: int, text: str) -> None:
        self.session.answers[field_id] = text
        self.exam_page.update_nav()
        now = now_utc().timestamp()
        if now - self._answer_event_ts.get(field_id, 0.0) > 15:
            self._answer_event_ts[field_id] = now
            self.emit_event("answer_changed", {"field_id": field_id})

    def _on_task_opened(self, task) -> None:
        number = task["number"] if task else 0
        self.emit_event("task_opened", {"task_number": number})

    def _tick(self) -> None:
        if not self.session.active or self.session.expires_at is None:
            return
        remaining = (self.session.expires_at - now_utc()).total_seconds()
        self.exam_page.set_remaining(int(remaining))
        if remaining <= 0:
            self._force_finish("time_expired")

    def _sync(self) -> None:
        if not self.session.active:
            return
        aid = self.session.attempt_id
        self.worker.submit("sync", lambda: self.api.get_attempt(aid))

    def _autosave(self) -> None:
        if not self.session.active:
            return
        snapshot = self.session.collect_answers()
        self._last_snapshot = snapshot
        self.worker.submit("autosave", lambda: self._send_answers(snapshot))

    def _send_answers(self, snapshot: list[dict]) -> dict:
        aid = self.session.attempt_id
        try:
            if self.session.offline_events:
                events = list(self.session.offline_events)
                self.api.send_events(aid, events)
                self.session.offline_events.clear()
        except ApiError:
            pass
        return self.api.save_answers(aid, snapshot)

    def _write_local_backup(self, snapshot: list[dict]) -> None:
        path = Path(tempfile.gettempdir()) / (
            f"exam_answers_{self.config.machine_id}_{self.session.attempt_id}.json"
        )
        path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    def _remove_local_backup(self) -> None:
        path = Path(tempfile.gettempdir()) / (
            f"exam_answers_{self.config.machine_id}_{self.session.attempt_id}.json"
        )
        path.unlink(missing_ok=True)

    def _request_finish(self) -> None:
        if ask_yes_no(
            self,
            "Завершение",
            "Завершить экзамен досрочно? После этого изменить ответы будет нельзя.",
        ):
            self._force_finish("finished")

    def _force_finish(self, reason: str) -> None:
        if not self.session.active:
            return
        self.tick_timer.stop()
        self.autosave_timer.stop()
        self.sync_timer.stop()
        self.exam_page.set_busy(True)
        self.exam_page.set_status("Завершение экзамена…")
        snapshot = self.session.collect_answers()
        self.worker.submit("finish", lambda: self._do_finish(reason, snapshot))

    def _do_finish(self, reason: str, snapshot: list[dict]) -> dict:
        aid = self.session.attempt_id
        events = list(self.session.offline_events)
        events.append(make_event("exam_finish_requested", {"reason": reason}))
        try:
            self.api.send_events(aid, events)
            self.session.offline_events.clear()
        except ApiError:
            pass
        return self.api.finish(aid, reason, snapshot)

    def _download_file(self, file_id: int, name: str) -> None:
        self.worker.submit(
            "download", lambda: (name, self.api.download_file(file_id))
        )

    def _on_task_done(self, name: str, result, error) -> None:
        if name == "exam_info":
            if error:
                QMessageBox.warning(self, "Сервер", str(error))
                return
            self.prestart_page.set_info(
                self.session.student, result["exam_duration_minutes"]
            )
            self.stack.setCurrentWidget(self.prestart_page)

        elif name == "start":
            self.prestart_page.set_busy(False)
            if error:
                QMessageBox.warning(self, "Начало экзамена", str(error))
                return
            self._enter_exam(result)

        elif name == "autosave":
            if error:
                self._write_local_backup(self._last_snapshot)
                self.exam_page.set_status("Нет связи с сервером - ответы сохранены локально")
            else:
                self._remove_local_backup()
                self.exam_page.set_status(
                    f"Ответы сохранены на сервере в {now_utc().astimezone().strftime('%H:%M:%S')}"
                )

        elif name == "sync":
            if error:
                return
            attempt = result["attempt"]
            if attempt["status"] != "in_progress":
                self._stop_locker("server_reported_finished")
                self.session.finished = True
                self.worker.submit(
                    "result", lambda: self.api.get_result(self.session.attempt_id)
                )
            else:
                from ..session import parse_iso

                self.session.expires_at = parse_iso(attempt.get("expires_at"))

        elif name == "finish":
            if error:
                self.exam_page.set_busy(False)
                self.exam_page.set_status("Не удалось завершить экзамен. Повторите попытку завершения.")
                QMessageBox.critical(self, "Завершение", str(error))
                return
            self._stop_locker("exam_finished")
            self.session.finished = True
            self._remove_local_backup()
            self.result_page.show_result(result)
            self.stack.setCurrentWidget(self.result_page)

        elif name == "result":
            if error:
                return
            self._stop_locker("exam_finished")
            self.session.finished = True
            self.result_page.show_result(result)
            self.stack.setCurrentWidget(self.result_page)

        elif name == "download":
            if error:
                QMessageBox.warning(self, "Файл", str(error))
                return
            name_file, content = result
            folder = Path(tempfile.gettempdir()) / "exam_files"
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / name_file
            dest.write_bytes(content)
            self.exam_page.set_status(f"Файл сохранён: {dest}")
            if hasattr(os, "startfile"):
                try:
                    os.startfile(dest)  # type: ignore[attr-defined]
                except OSError:
                    pass

        elif name == "event":
            if error:
                pass 

    def closeEvent(self, event) -> None:
        if self.session.active:
            if not ask_yes_no(
                self,
                "Выход",
                "Закрыть приложение? Попытка будет помечена как прерванная.",
            ):
                event.ignore()
                return
            try:
                self.api.finish(
                    self.session.attempt_id,
                    "aborted",
                    self.session.collect_answers(),
                    retries=0,
                )
            except ApiError:
                pass
            self.session.finished = True
        self._stop_locker("app_close")
        self.worker.stop()
        self.worker.wait(2000)
        event.accept()