"""APScheduler-backed campaign scheduler — auto-fires campaign_service.start()."""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from app.core.logger import get_logger

log = get_logger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")
_scheduler.start()


def _fire_campaign(campaign_id: int):
    from app.services.campaign.campaign_service import CampaignService
    log.info("Scheduler firing campaign %d", campaign_id)
    CampaignService().start(campaign_id)


def schedule_campaign(campaign_id: int, run_at: datetime):
    job_id = f"campaign_{campaign_id}"
    _scheduler.add_job(
        _fire_campaign,
        trigger=DateTrigger(run_date=run_at),
        id=job_id,
        replace_existing=True,
        args=[campaign_id],
    )
    log.info("Campaign %d scheduled for %s UTC", campaign_id, run_at)


def cancel_scheduled(campaign_id: int):
    job_id = f"campaign_{campaign_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        log.info("Campaign %d schedule cancelled", campaign_id)


def restore_scheduled_campaigns():
    """Call at app startup to reschedule any campaigns still in 'scheduled' state."""
    from app.core.database import get_session
    from app.models.campaign import Campaign
    from datetime import timezone

    with get_session() as s:
        pending = s.query(Campaign).filter_by(status="scheduled").all()
        now = datetime.utcnow()
        for camp in pending:
            if camp.scheduled_at:
                run_at = camp.scheduled_at
                if run_at <= now:
                    # overdue — fire immediately
                    log.info("Campaign %d overdue, firing now", camp.id)
                    _fire_campaign(camp.id)
                else:
                    schedule_campaign(camp.id, run_at)


def shutdown():
    _scheduler.shutdown(wait=False)
