from PyQt6.QtWidgets import QMessageBox


def ask_yes_no(parent, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)

    yes = box.addButton("Да", QMessageBox.ButtonRole.YesRole)
    no = box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
    no.setObjectName("secondary")

    box.setDefaultButton(no)
    box.setEscapeButton(no)
    box.exec()

    return box.clickedButton() is yes