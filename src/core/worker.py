import traceback

from PySide6.QtCore import QThread, Signal

from src.utils.logger import logger


class LogicWorker(QThread):
    """Runs a background task in a separate thread and emits the result or error."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, task, *args):
        """Initialize the worker with a callable task and its arguments."""
        super().__init__()
        self.task = task
        self.args = args

    def run(self):
        """Execute the task and emit the result or an error message."""
        try:
            res = self.task(*self.args)
            self.finished.emit(res)
        except Exception as e:
            logger.error("Background task failed: %s", traceback.format_exc())
            self.error.emit(str(e))
