from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ResultPage(QWidget):
    exit_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 32, 48, 32)
        layout.setSpacing(16)

        title = QLabel("Экзамен завершён")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        self.scores_label = QLabel()
        self.scores_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scores_label.setWordWrap(True)
        self.scores_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #ffffff;")
        layout.addWidget(self.scores_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["№ задания", "Ваши ответы", "Балл"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        note = QLabel("Ответы успешно сохранены")
        note.setObjectName("muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        exit_button = QPushButton("Выйти")
        exit_button.setFixedWidth(220)
        exit_button.clicked.connect(self.exit_requested)
        buttons.addWidget(exit_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def show_result(self, result: dict) -> None:
        scores = result["scores"]
        primary = scores["primary_score"]
        test = scores["test_score"]
        max_test = scores.get("max_test_score")

        lines = [
            f"Первичный балл: {primary if primary is not None else '-'} из {scores['max_primary_score']}",
        ]
        if test is not None:
            suffix = f" из {max_test}" if max_test is not None else ""
            lines.append(f"Тестовый балл: {test}{suffix}")
        else:
            lines.append("Тестовый балл: не рассчитан (ошибка настройки таблицы перевода)")
        self.scores_label.setText("\n".join(lines))

        tasks = result["tasks"]
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(str(task["number"])))
            answers_text = "; ".join(a["value"] or "-" for a in task["answers"])
            self.table.setItem(row, 1, QTableWidgetItem(answers_text))
            score = "-" if task["score"] is None else f"{task['score']} из {task['max_score']}"
            self.table.setItem(row, 2, QTableWidgetItem(score))