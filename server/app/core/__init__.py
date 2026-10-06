import sys
from pathlib import Path

IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
MEIPASS_DIR = Path(sys._MEIPASS) if IS_FROZEN else None

def get_app_root() -> Path:
    if IS_FROZEN:
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent