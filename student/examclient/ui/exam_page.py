from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..session import SessionState


class ExamPage(QWidget):
    answer_changed = pyqtSignal(int, str)
    task_opened = pyqtSignal(object)
    finish_requested = pyqtSignal()
    download_requested = pyqtSignal(int, str)

    def __init__(self, session: SessionState):
        super().__init__()
        self.session = session
        self.setObjectName("page")
        self.nav_buttons: list[QPushButton] = []
        self._current = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QFrame()
        top.setObjectName("topBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 10, 16, 10)
        self.timer_label = QLabel("--:--:--")
        self.timer_label.setObjectName("timer")
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusBar")
        self.finish_button = QPushButton("Завершить экзамен")
        self.finish_button.setObjectName("danger")
        self.finish_button.clicked.connect(self.finish_requested)
        top_layout.addWidget(self.timer_label)
        top_layout.addWidget(self.status_label, 1)
        top_layout.addWidget(self.finish_button)
        root.addWidget(top)

        body = QWidget()
        body.setObjectName("contentPane")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(12)

        left = QWidget()
        left.setObjectName("navPane")
        left.setFixedWidth(250)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        self.counter_label = QLabel("Дано ответов: 0 / 0")
        self.counter_label.setObjectName("answeredCounter")
        left_layout.addWidget(self.counter_label)

        self.nav_scroll = QScrollArea()
        self.nav_scroll.setObjectName("navScroll")
        self.nav_scroll.setWidgetResizable(True)
        self.nav_container = QWidget()
        self.nav_container.setObjectName("navContainer")
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(0)
        self.nav_scroll.setWidget(self.nav_container)
        left_layout.addWidget(self.nav_scroll, 1)

        body_layout.addWidget(left)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setObjectName("contentPane")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)
        self.scroll.setWidget(self.content)
        body_layout.addWidget(self.scroll, 3)

        root.addWidget(body, 1)

    def populate(self) -> None:
        while self.nav_layout.count():
            item = self.nav_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.nav_buttons = []
        self._current = -1

        labels = ["Страница 0"] + [f"Задание {t['number']}" for t in self.session.tasks]
        for index, text in enumerate(labels):
            button = QPushButton(text)
            button.setObjectName("navItem")
            button.setProperty("answered", False)
            button.setProperty("current", False)
            button.clicked.connect(lambda _checked, i=index: self._select(i))
            self.nav_layout.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_layout.addStretch(1)

        self._select(0)
        self.update_nav()

    def _select(self, index: int) -> None:
        if index < 0 or index >= len(self.nav_buttons):
            return
        if 0 <= self._current < len(self.nav_buttons) and self._current != index:
            old = self.nav_buttons[self._current]
            old.setProperty("current", False)
            old.style().unpolish(old)
            old.style().polish(old)

        self._current = index
        new = self.nav_buttons[index]
        new.setProperty("current", True)
        new.style().unpolish(new)
        new.style().polish(new)

        self._clear_content()
        if index == 0:
            self._render_instruction()
            self.task_opened.emit(None)
        else:
            task = self.session.tasks[index - 1]
            self._render_task(task)
            self.task_opened.emit(task)

    def update_nav(self) -> None:
        if not self.nav_buttons:
            return
        answered_count = 0
        for index, task in enumerate(self.session.tasks, start=1):
            answered = self.session.is_task_answered(task)
            if answered:
                answered_count += 1
            button = self.nav_buttons[index]
            if button.property("answered") != answered:
                button.setProperty("answered", answered)
                button.style().unpolish(button)
                button.style().polish(button)
        self.counter_label.setText(
            f"Дано ответов: {answered_count} / {len(self.session.tasks)}"
        )

    def _clear_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_instruction(self) -> None:
        label = QLabel(self.session.instruction or "Инструкция не задана.")
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 16px;")
        self.content_layout.addWidget(label)
        self.content_layout.addStretch()

    @staticmethod
    def _task_heading(task: dict) -> str:
        base = f"Задание {task['number']}"
        title = (task.get("title") or "").strip()
        if not title:
            return base
        if title.lower().startswith(base.lower()):
            return title
        return f"{base}. {title}"

    def _render_task(self, task: dict) -> None:
        title = QLabel(self._task_heading(task))
        title.setObjectName("taskTitle")
        title.setWordWrap(True)
        self.content_layout.addWidget(title)

        for key, caption in (
            ("statement_text", "Текст задания"),
            ("instruction_text", "Инструкция"),
            ("source_data_text", "Исходные данные"),
        ):
            text = task.get(key)
            if text:
                head = QLabel(caption)
                head.setObjectName("section")
                body = QLabel(text)
                body.setWordWrap(True)
                body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.content_layout.addWidget(head)
                self.content_layout.addWidget(body)

        files = task.get("files", [])
        if files:
            head = QLabel("Прикреплённые файлы")
            head.setObjectName("section")
            self.content_layout.addWidget(head)
            for f in files:
                button = QPushButton(f"Скачать: {f['original_name']}")
                button.setObjectName("secondary")
                button.clicked.connect(
                    lambda _checked, fid=f["id"], name=f["original_name"]:
                    self.download_requested.emit(fid, name)
                )
                self.content_layout.addWidget(button)

        head = QLabel("Ответы")
        head.setObjectName("section")
        self.content_layout.addWidget(head)

        for field in task.get("fields", []):
            label = QLabel(field["label"])
            label.setObjectName("section")
            label.setWordWrap(True)
            edit = QLineEdit(self.session.answers.get(field["id"], ""))
            edit.textChanged.connect(
                lambda text, fid=field["id"]: self.answer_changed.emit(fid, text)
            )
            self.content_layout.addWidget(label)
            self.content_layout.addWidget(edit)

        self.content_layout.addStretch()

    def set_remaining(self, seconds: int) -> None:
        seconds = max(seconds, 0)
        hours, rest = divmod(seconds, 3600)
        minutes, secs = divmod(rest, 60)
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")
        self.timer_label.setObjectName("timerWarn" if seconds <= 900 else "timer")
        self.timer_label.style().unpolish(self.timer_label)
        self.timer_label.style().polish(self.timer_label)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.finish_button.setEnabled(not busy)
        for button in self.nav_buttons:
            button.setEnabled(not busy)