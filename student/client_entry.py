import sys
import traceback
from pathlib import Path


def _crash_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name("crash.log")
    return Path(__file__).resolve().parent / "crash.log"


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    try:
        with _crash_log_path().open("a", encoding="utf-8") as fh:
            fh.write("=== UNHANDLED EXCEPTION ===\n")
            fh.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
            fh.write("\n")
    except OSError:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


def main() -> None:
    from examclient.main import main as qt_main
    qt_main()


if __name__ == "__main__":
    main()