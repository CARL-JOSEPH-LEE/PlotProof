"""Workers communicate only through queued Qt signals."""

import threading

from PySide6.QtCore import QThread, Signal

from ..engine import Cancelled


class Worker(QThread):
    progress = Signal(object)
    result = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.cancel = threading.Event()

    def run(self):
        try:
            result = self.function(self.progress.emit, self.cancel)
            if self.cancel.is_set():
                raise Cancelled()
            self.result.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc) or type(exc).__name__)
