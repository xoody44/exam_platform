import sys

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from examclient.api import ExamApi
from examclient.config import AppConfig, load_config, save_config
from examclient.ui.main_window import MainWindow
from examclient.ui.server_setup_dialog import ServerSetupDialog
from examclient.ui.styles import EXAM_QSS


def build_palette() -> QPalette:
    bg = QColor("#252526")
    panel = QColor("#2d2d30")
    text = QColor("#e6e6e6")
    accent = QColor("#3e6db0")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, panel)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, panel)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, panel)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8a8a8a"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#777777"))
    return palette


def ensure_server_config(app: QApplication) -> AppConfig:
    config = load_config()

    if config.server_url:
        try:
            ExamApi(config.server_url).health(timeout=3.0)
            return config
        except Exception:
            pass

    while True:
        dialog = ServerSetupDialog(
            current_url=config.server_url,
            current_machine=config.machine_id,
            parent=None,
        )
        dialog.setStyleSheet(EXAM_QSS)
        dialog.setPalette(app.palette())
        if dialog.exec() != dialog.DialogCode.Accepted:
            sys.exit(0)

        config.server_url = dialog.accepted_url
        config.machine_id = dialog.accepted_machine

        try:
            save_config(config)
        except OSError:
            pass

        return config


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ExamStudent")
    app.setPalette(build_palette())
    app.setStyleSheet(EXAM_QSS)

    config = ensure_server_config(app)

    window = MainWindow(config)
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()