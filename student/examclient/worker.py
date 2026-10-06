from queue import Empty, Queue
from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal


class NetworkWorker(QThread):
    task_done = pyqtSignal(str, object, object)

    def __init__(self):
        super().__init__()
        self._queue: Queue = Queue()
        self._running = True

    def submit(self, name: str, fn: Callable[[], Any]) -> None:
        self._queue.put((name, fn))

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)

    def run(self) -> None:
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if item is None:
                break
            name, fn = item
            try:
                result = fn()
                self.task_done.emit(name, result, None)
            except Exception as exc:
                self.task_done.emit(name, None, exc)