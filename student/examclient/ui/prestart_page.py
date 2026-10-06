from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

CARD_WIDTH = 640
CARD_MARGIN = 36
LABEL_WIDTH = CARD_WIDTH - CARD_MARGIN * 2


class PrestartPage(QWidget):
    start_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")

        outer = QVBoxLayout(self)
        outer.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedWidth(CARD_WIDTH)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(CARD_MARGIN, 32, CARD_MARGIN, 32)
        card_layout.setSpacing(14)

        title = QLabel("Экзамен готов к началу")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        card_layout.addWidget(title)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-size: 16px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.MinimumExpanding,
        )
        card_layout.addWidget(self.info_label)

        self.start_button = QPushButton("Начать экзамен")
        self.start_button.clicked.connect(self.start_requested)
        card_layout.addWidget(self.start_button)

        exit_button = QPushButton("Выход")
        exit_button.setObjectName("secondary")
        exit_button.clicked.connect(self.exit_requested)
        card_layout.addWidget(exit_button)

        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    def set_info(self, student: dict, duration_minutes: int) -> None:
        hours, minutes = divmod(duration_minutes, 60)
        self.info_label.setText(
            f"Ученик: {student['full_name']}\n"
            f"Школа: {student['school_name']}\n"
            f"Длительность экзамена: {hours} ч {minutes} мин\n\n"
            "После нажатия «Начать экзамен» будет создана попытка, "
            "выдан вариант и запущен таймер. Остановить или отменить попытку нельзя."
        )
        needed_height = self.info_label.heightForWidth(LABEL_WIDTH)
        self.info_label.setMinimumHeight(needed_height)
        self.info_label.updateGeometry()
        self.card.adjustSize()

    def set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)