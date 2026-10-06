from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QLayout,
    QPushButton,
    QVBoxLayout,
)

DIALOG_WIDTH = 560


class ServerSetupDialog(QDialog):
    def __init__(self, current_url: str, current_machine: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка подключения")
        self.setObjectName("setupDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        title = QLabel("Настройка подключения")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel(
            "Сервер экзамена недоступен.\n"
            "Введите IP-адрес сервера (отображается в консоли при его запуске)\n"
            "и идентификатор этого компьютера."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        self.server_url = QLineEdit(current_url)
        self.server_url.setPlaceholderText("http://192.168.1.10:8000")
        self.server_url.setMinimumWidth(360)
        self.machine_id = QLineEdit(current_machine)
        self.machine_id.setPlaceholderText("pc-01")
        form.addRow("Адрес сервера:", self.server_url)
        form.addRow("ID компьютера:", self.machine_id)
        layout.addLayout(form)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        exit_button = QPushButton("Выход")
        exit_button.setObjectName("secondary")
        exit_button.clicked.connect(self.reject)
        self.check_button = QPushButton("Проверить и продолжить")
        self.check_button.clicked.connect(self._on_check)
        buttons.addWidget(exit_button)
        buttons.addStretch(1)
        buttons.addWidget(self.check_button)
        layout.addLayout(buttons)

        self.setFixedWidth(DIALOG_WIDTH)

        self.accepted_url: str = ""
        self.accepted_machine: str = ""

    def set_status(self, text: str, error: bool = False) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "color: #ff6b6b; font-weight: 600;" if error else "color: #9aa0a6;"
        )

    def _on_check(self) -> None:
        url = self.server_url.text().strip().rstrip("/")
        machine = self.machine_id.text().strip()

        if not url:
            self.set_status("Укажите адрес сервера", error=True)
            return
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        if not machine:
            self.set_status("Укажите ID компьютера", error=True)
            return

        self.set_status("Проверка соединения...")
        self.check_button.setEnabled(False)

        try:
            from ..api import ExamApi
            api = ExamApi(url)
            api.health(timeout=3.0)
        except Exception as exc:
            self.set_status(f"Сервер недоступен: {exc}", error=True)
            self.check_button.setEnabled(True)
            return

        self.accepted_url = url
        self.accepted_machine = machine
        self.accept()