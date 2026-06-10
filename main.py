import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from app.core.database import init_db
from app.ui.main_window import MainWindow
from app.ui.workers.tracking_worker import TrackingWorker
from app.services.content.spinner_service import download_nltk_data


def load_stylesheet(app: QApplication) -> None:
    qss = Path(__file__).parent / "app" / "ui" / "resources" / "styles" / "dark_theme.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BM2Ultra")
    app.setApplicationVersion("1.0.0")

    # Database — create all tables
    init_db()

    # Restore any campaigns scheduled for later
    from app.services.campaign.scheduler_service import restore_scheduled_campaigns
    restore_scheduled_campaigns()

    # Background: tracking server on localhost:8765
    tracking_worker = TrackingWorker()
    tracking_worker.start()

    # Background: pre-download NLTK WordNet corpus (quiet, no UI block)
    download_nltk_data()

    load_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
