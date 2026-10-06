from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..api import ApiError, ExamApi


class LoginPage(QWidget):
    logged_in = pyqtSignal(dict)
    exit_requested = pyqtSignal()

    def __init__(self, api: ExamApi):
        super().__init__()
        self.setObjectName("page")
        self.api = api
        self.schools: list[dict] = []

        outer = QVBoxLayout(self)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(12)

        title = QLabel("Пробный экзамен по информатике")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        card_layout.addWidget(title)

        subtitle = QLabel("Вход для ученика")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        card_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        self.last_name = QLineEdit()
        self.first_name = QLineEdit()
        self.middle_name = QLineEdit()
        self.school_combo = QComboBox()
        form.addRow("Фамилия:", self.last_name)
        form.addRow("Имя:", self.first_name)
        form.addRow("Отчество:", self.middle_name)
        form.addRow("Школа:", self.school_combo)
        card_layout.addLayout(form)

        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.do_login)
        card_layout.addWidget(self.login_button)

        self.refresh_button = QPushButton("Обновить список школ")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.clicked.connect(self.load_schools)
        card_layout.addWidget(self.refresh_button)

        exit_button = QPushButton("Выход")
        exit_button.setObjectName("secondary")
        exit_button.clicked.connect(self.exit_requested)
        card_layout.addWidget(exit_button)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        self.load_schools()

    def load_schools(self) -> None:
        try:
            self.schools = self.api.get_schools()
        except ApiError as exc:
            self.schools = []
            QMessageBox.warning(self, "Школы", f"Не удалось загрузить список школ: {exc}")
            return
        self.school_combo.clear()
        for school in self.schools:
            self.school_combo.addItem(school["name"], school["id"])

    def do_login(self) -> None:
        payload = {
            "last_name": self.last_name.text().strip(),
            "first_name": self.first_name.text().strip(),
            "middle_name": self.middle_name.text().strip() or None,
            "school_id": self.school_combo.currentData(),
        }
        if not payload["last_name"] or not payload["first_name"]:
            QMessageBox.warning(self, "Вход", "Укажите фамилию и имя")
            return
        if payload["school_id"] is None:
            QMessageBox.warning(self, "Вход", "Выберите школу")
            return
        try:
            student = self.api.student_login(payload)
        except ApiError as exc:
            QMessageBox.warning(self, "Вход", str(exc))
            return
        self.logged_in.emit(student)