"""QThread wrapper that starts the campaign service."""
from PySide6.QtCore import QThread
from app.services.campaign.campaign_service import CampaignService
from app.core.logger import get_logger

log = get_logger(__name__)
_svc = CampaignService()


class SendWorker(QThread):
    def __init__(self, campaign_id: int, parent=None):
        super().__init__(parent)
        self.campaign_id = campaign_id

    def run(self):
        _svc.start(self.campaign_id)
        self.exec()  # keep thread alive until campaign finishes

    def pause(self):
        _svc.pause(self.campaign_id)

    def stop(self):
        _svc.stop(self.campaign_id)
        self.quit()
