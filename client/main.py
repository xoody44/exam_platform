import sys
import json
import time
from datetime import datetime

import requests
import psutil

from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QStackedWidget,
    QListWidget,
    QScrollArea,
    QMessageBox,
)

# ---------------------------------------------------------------------------
# Конфиг
# ---------------------------------------------------------------------------

try:
    with open("config.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {
        "server_url": "http://127.0.0.1:8000",
        "machine_id": "pc-01",
        "browser_blacklist": [
            "chrome.exe",
            "msedge.exe",
            "firefox.exe",
            "opera.exe",
            "brave.exe",
            "vivaldi.exe",
            "yandex.exe",
            "iexplore.exe",
        ],
    }

SERVER_URL = CONFIG.get("server_url", "http://127.0.0.1:8000").rstrip("/")
MACHINE_ID = CONFIG.get("machine_id", "pc-01")
BROWSER_BLACKLIST = {name.lower() for name in CONFIG.get("browser_blacklist", [])}


# ---------------------------------------------------------------------------
# Антибраузер
# ---------------------------------------------------------------------------


class AntiBrowserThread(QThread):
    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                for proc in psutil.process_iter(["name"]):
                    try:
                        name = proc.info.get("name")
                        if name and name.lower() in BROWSER_BLACKLIST:
                            proc.kill()
                    except Exception:
                        pass
            except Exception:
                pass

            time.sleep(0.7)


# ---------------------------------------------------------------------------
# Основное приложение
# ---------------------------------------------------------------------------


class ExamClient(QWidget):
    def __init__(self):
        super().__init__()

        self.token = None
        self.student_info = None

        self.attempt = None
        self.tasks = []
        self.instruction = ""

        self.answers = {}
        self.expires_at = None

        self.exam_active = False

        self.blocker = None

        self.setWindowTitle("Экзамен")
        self.resize(1100, 700)

        self.stack = QStackedWidget()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.build_login_page()
        self.build_prestart_page()
        self.build_exam_page()
        self.build_result_page()

        self.stack.setCurrentWidget(self.login_page)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_timer)

        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(20000)
        self.autosave_timer.timeout.connect(self.save_answers)

    # -----------------------------------------------------------------------
    # Страницы
    # -----------------------------------------------------------------------

    def build_login_page(self):
        self.login_page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Вход ученика")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()

        self.last_name_edit = QLineEdit()
        self.first_name_edit = QLineEdit()
        self.middle_name_edit = QLineEdit()
        self.class_number_edit = QLineEdit()
        self.class_letter_edit = QLineEdit()

        form.addRow("Фамилия:", self.last_name_edit)
        form.addRow("Имя:", self.first_name_edit)
        form.addRow("Отчество:", self.middle_name_edit)
        form.addRow("Класс:", self.class_number_edit)
        form.addRow("Буква класса:", self.class_letter_edit)

        login_button = QPushButton("Войти")
        login_button.clicked.connect(self.do_login)

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(login_button)
        layout.addStretch()

        self.login_page.setLayout(layout)
        self.stack.addWidget(self.login_page)

    def build_prestart_page(self):
        self.prestart_page = QWidget()
        layout = QVBoxLayout()

        self.prestart_label = QLabel()
        self.prestart_label.setStyleSheet("font-size: 20px;")
        self.prestart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        start_button = QPushButton("Начать экзамен")
        start_button.clicked.connect(self.start_exam)

        exit_button = QPushButton("Выход")
        exit_button.clicked.connect(QApplication.quit)

        layout.addWidget(self.prestart_label)
        layout.addWidget(start_button)
        layout.addWidget(exit_button)
        layout.addStretch()

        self.prestart_page.setLayout(layout)
        self.stack.addWidget(self.prestart_page)

    def build_exam_page(self):
        self.exam_page = QWidget()
        root_layout = QHBoxLayout()

        left_panel = QVBoxLayout()

        self.task_list = QListWidget()
        self.task_list.currentRowChanged.connect(self.show_task)

        finish_button = QPushButton("Завершить экзамен")
        finish_button.clicked.connect(lambda: self.finish_exam("finished"))

        left_panel.addWidget(self.task_list)
        left_panel.addWidget(finish_button)

        right_panel = QVBoxLayout()

        self.timer_label = QLabel("Осталось: --:--")
        self.timer_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.task_detail = QWidget()
        self.task_detail_layout = QVBoxLayout()
        self.task_detail.setLayout(self.task_detail_layout)
        self.scroll.setWidget(self.task_detail)

        right_panel.addWidget(self.timer_label)
        right_panel.addWidget(self.scroll)

        root_layout.addLayout(left_panel, 1)
        root_layout.addLayout(right_panel, 3)

        self.exam_page.setLayout(root_layout)
        self.stack.addWidget(self.exam_page)

    def build_result_page(self):
        self.result_page = QWidget()
        layout = QVBoxLayout()

        self.result_label = QLabel()
        self.result_label.setStyleSheet("font-size: 22px;")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(QApplication.quit)

        layout.addWidget(self.result_label)
        layout.addWidget(close_button)
        layout.addStretch()

        self.result_page.setLayout(layout)
        self.stack.addWidget(self.result_page)

    # -----------------------------------------------------------------------
    # Сеть
    # -----------------------------------------------------------------------

    def headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def api_url(self, path):
        return SERVER_URL + path

    # -----------------------------------------------------------------------
    # Логика
    # -----------------------------------------------------------------------

    def do_login(self):
        payload = {
            "last_name": self.last_name_edit.text(),
            "first_name": self.first_name_edit.text(),
            "middle_name": self.middle_name_edit.text(),
            "class_number": self.class_number_edit.text(),
            "class_letter": self.class_letter_edit.text(),
        }

        if not payload["last_name"].strip():
            QMessageBox.warning(self, "Ошибка", "Введите фамилию")
            return

        if not payload["first_name"].strip():
            QMessageBox.warning(self, "Ошибка", "Введите имя")
            return

        try:
            class_number = int(payload["class_number"])
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Класс должен быть числом")
            return

        body = {
            "last_name": payload["last_name"],
            "first_name": payload["first_name"],
            "middle_name": payload["middle_name"] or None,
            "class_number": class_number,
            "class_letter": payload["class_letter"],
        }

        try:
            response = requests.post(
                self.api_url("/api/student/login"),
                json=body,
                timeout=10,
            )
            data = response.json()

            if response.status_code != 200:
                raise Exception(data.get("detail", "Ошибка входа"))

            self.token = data["token"]
            self.student_info = data["student"]

            self.prestart_label.setText(
                f"Ученик: {self.student_info['full_name']}\n"
                f"Класс: {self.student_info['class_name']}\n\n"
                f"Нажмите «Начать экзамен»."
            )

            self.stack.setCurrentWidget(self.prestart_page)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def start_exam(self):
        try:
            response = requests.post(
                self.api_url("/api/student/attempts/start"),
                json={"machine_id": MACHINE_ID},
                headers=self.headers(),
                timeout=15,
            )
            data = response.json()

            if response.status_code != 200:
                raise Exception(data.get("detail", "Не удалось начать экзамен"))

            self.attempt = data["attempt"]
            self.tasks = data["tasks"]
            self.instruction = data.get("instruction", "")

            self.answers = {}
            self.exam_active = True

            self.fill_task_list()
            self.show_task(0)

            expires_at = self.attempt.get("expires_at")
            self.expires_at = datetime.fromisoformat(expires_at) if expires_at else None

            self.start_blocker()

            self.timer.start()
            self.autosave_timer.start()

            self.stack.setCurrentWidget(self.exam_page)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def fill_task_list(self):
        self.task_list.clear()
        self.task_list.addItem("Страница 0")

        for task in self.tasks:
            self.task_list.addItem(f"Задание {task['number']}")

        self.task_list.setCurrentRow(0)

    def clear_task_detail(self):
        while self.task_detail_layout.count():
            item = self.task_detail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_task(self, row):
        self.clear_task_detail()

        if row == 0:
            label = QLabel(self.instruction or "Инструкция")
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 16px;")
            self.task_detail_layout.addWidget(label)
            self.task_detail_layout.addStretch()
            return

        task = self.tasks[row - 1]

        title = QLabel(f"Задание {task['number']}: {task['title']}")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setWordWrap(True)

        statement = QLabel(task.get("statement_text") or "")
        statement.setWordWrap(True)
        statement.setStyleSheet("font-size: 16px;")

        self.task_detail_layout.addWidget(title)
        self.task_detail_layout.addWidget(statement)

        if task.get("instruction_text"):
            instruction = QLabel(task["instruction_text"])
            instruction.setWordWrap(True)
            self.task_detail_layout.addWidget(instruction)

        if task.get("source_data_text"):
            source = QLabel(task["source_data_text"])
            source.setWordWrap(True)
            self.task_detail_layout.addWidget(source)

        for field in task.get("fields", []):
            field_label = QLabel(field.get("label", "Ответ"))
            field_label.setStyleSheet("font-weight: bold;")

            edit = QLineEdit()
            edit.setText(str(self.answers.get(field["id"], "")))
            edit.textChanged.connect(
                lambda text, field_id=field["id"]: self.answers.update({field_id: text})
            )

            self.task_detail_layout.addWidget(field_label)
            self.task_detail_layout.addWidget(edit)

        self.task_detail_layout.addStretch()

    def collect_answers(self):
        result = []

        for task in self.tasks:
            for field in task.get("fields", []):
                result.append(
                    {
                        "task_id": task["id"],
                        "field_id": field["id"],
                        "value": self.answers.get(field["id"], ""),
                    }
                )

        return result

    def save_answers(self):
        if not self.exam_active or not self.attempt:
            return

        payload = {"answers": self.collect_answers()}

        try:
            requests.put(
                self.api_url(f"/api/student/attempts/{self.attempt['id']}/answers"),
                json=payload,
                headers=self.headers(),
                timeout=10,
            )
        except Exception:
            pass

    def update_timer(self):
        if not self.expires_at:
            return

        now = datetime.utcnow()
        delta = (self.expires_at - now).total_seconds()

        if delta <= 0:
            self.timer_label.setText("Время вышло")
            self.finish_exam("time_expired")
            return

        minutes = int(delta // 60)
        seconds = int(delta % 60)

        self.timer_label.setText(f"Осталось: {minutes:02d}:{seconds:02d}")

    def start_blocker(self):
        if not self.blocker:
            self.blocker = AntiBrowserThread()
            self.blocker.start()

    def stop_blocker(self):
        if self.blocker:
            self.blocker.stop()
            self.blocker.wait(1000)
            self.blocker = None

    def finish_exam(self, reason):
        if not self.exam_active:
            return

        self.exam_active = False

        self.timer.stop()
        self.autosave_timer.stop()

        self.save_answers()

        payload = {
            "reason": reason,
            "answers": self.collect_answers(),
        }

        try:
            response = requests.post(
                self.api_url(f"/api/student/attempts/{self.attempt['id']}/finish"),
                json=payload,
                headers=self.headers(),
                timeout=20,
            )
            data = response.json()

            if response.status_code != 200:
                raise Exception(data.get("detail", "Ошибка завершения экзамена"))

            attempt = data["attempt"]

            self.result_label.setText(
                "Экзамен завершен.\n\n"
                f"Первичный балл: {attempt.get('primary_score')}\n"
                f"Вторичный балл: {attempt.get('secondary_score')}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

        finally:
            self.stop_blocker()
            self.stack.setCurrentWidget(self.result_page)

    def closeEvent(self, event):
        if self.exam_active:
            event.ignore()
            QMessageBox.warning(
                self,
                "Внимание",
                "Нельзя закрыть приложение во время экзамена.",
            )
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExamClient()
    window.show()
    sys.exit(app.exec())
