"""QThread that starts the FastAPI tracking server."""
from PySide6.QtCore import QThread
from app.tracking.server import start_tracking_server


class TrackingWorker(QThread):
    def run(self):
        start_tracking_server()
        self.exec()
