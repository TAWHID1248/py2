"""Campaign state machine — routes SMTP vs Gmail, Faker name randomization."""
import uuid
import time
import threading
from app.core.database import get_session
from app.core.logger import get_logger
from app.core.event_bus import bus
from app.core.config import settings
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.account_repository import AccountRepository
from app.services.email.smtp_service import SMTPService
from app.services.email.mime_builder import build_message
from app.services.content.template_service import TemplateService
from app.services.content.fake_data_service import random_name
from app.services.campaign.throttle_service import ThrottleService

log = get_logger(__name__)

_active: dict[int, threading.Event] = {}


class CampaignService:
    def start(self, campaign_id: int):
        if campaign_id in _active:
            log.warning("Campaign %d already running", campaign_id)
            return
        stop_ev = threading.Event()
        _active[campaign_id] = stop_ev
        t = threading.Thread(target=self._run, args=(campaign_id, stop_ev), daemon=True)
        t.start()

    def pause(self, campaign_id: int):
        ev = _active.get(campaign_id)
        if ev:
            ev.set()
        with get_session() as s:
            CampaignRepository(s).update_status(campaign_id, "paused")

    def stop(self, campaign_id: int):
        ev = _active.pop(campaign_id, None)
        if ev:
            ev.set()
        with get_session() as s:
            CampaignRepository(s).update_status(campaign_id, "stopped")

    def resume(self, campaign_id: int):
        """Resume a paused campaign from the first pending send."""
        self.start(campaign_id)

    def _run(self, campaign_id: int, stop_ev: threading.Event):
        try:
            with get_session() as s:
                repo = CampaignRepository(s)
                camp = repo.get(campaign_id)
                if not camp:
                    return
                repo.update_status(campaign_id, "running")
                bus.log_line.emit(f"[Campaign {campaign_id}] '{camp.name}' starting…")

                acc_repo = AccountRepository(s)
                acc = acc_repo.get(camp.account_id)

                contact_repo = ContactRepository(s)
                contacts = contact_repo.contacts_in_list(camp.list_id)

                # filter out already-sent contacts (resume support)
                sent_contact_ids = {
                    send.contact_id
                    for send in repo.pending_sends.__func__(repo, campaign_id)
                    # pending_sends only returns pending — use a different query for resume
                } if False else set()
                # For resume: skip contacts with existing sent status
                existing = {
                    cs.contact_id: cs.status
                    for cs in s.query(__import__(
                        'app.models.campaign', fromlist=['CampaignSend']
                    ).CampaignSend).filter_by(campaign_id=campaign_id).all()
                }
                contacts = [c for c in contacts if existing.get(c.id, "pending") == "pending"
                            or c.id not in existing]

                tmpl = s.get(
                    __import__('app.models.template', fromlist=['Template']).Template,
                    camp.template_id
                )
                if not tmpl:
                    bus.log_line.emit(f"[Campaign {campaign_id}] ERROR: template not found")
                    repo.update_status(campaign_id, "failed")
                    return

                tmpl_svc = TemplateService()
                throttle = ThrottleService(
                    delay_seconds=camp.throttle_delay,
                    hourly_limit=acc.hourly_limit if acc else 100,
                )

                pixel_base = f"http://{settings.tracking_host}:{settings.tracking_port}/track/open/"
                unsub_base = f"http://{settings.tracking_host}:{settings.tracking_port}/unsub/"

                smtp_svc = None
                gmail_svc = None
                if acc:
                    if acc.account_type == "gmail" and acc.oauth_token_enc:
                        from app.core.crypto import decrypt
                        from app.services.email.gmail_service import GmailService
                        gmail_svc = GmailService(decrypt(acc.oauth_token_enc))
                    else:
                        password = acc_repo.get_smtp_password(acc) or ""
                        smtp_svc = SMTPService(acc, password)

                for contact in contacts:
                    if stop_ev.is_set():
                        break

                    token = uuid.uuid4().hex
                    send_rec = repo.create_send(campaign_id, contact.id, token)
                    s.commit()

                    try:
                        subject, html, text = tmpl_svc.render(
                            tmpl,
                            contact,
                            use_spintax=camp.use_spintax,
                            use_synonyms=camp.use_synonyms,
                        )

                        # Faker from_name randomization
                        from_name = camp.from_name or (acc.name if acc else "")
                        if camp.use_spintax and "{" in (from_name or ""):
                            from app.services.content.spinner_service import spin
                            from_name = spin(from_name, seed=contact.id)
                        elif not from_name:
                            from_name = random_name()

                        msg = build_message(
                            from_addr=acc.email if acc else "noreply@example.com",
                            from_name=from_name,
                            to_addr=contact.email,
                            subject=subject,
                            html_body=html,
                            text_body=text,
                            reply_to=camp.reply_to,
                            tracking_pixel_url=pixel_base + token,
                            unsubscribe_url=unsub_base + token if camp.inject_unsubscribe else None,
                        )

                        throttle.wait()

                        if gmail_svc:
                            msg_id = gmail_svc.send(msg)
                        elif smtp_svc:
                            msg_id = smtp_svc.send(msg)
                        else:
                            msg_id = f"simulated-{uuid.uuid4().hex}"
                            log.warning("No send account — simulating send to %s", contact.email)

                        repo.mark_send(send_rec.id, "sent", message_id=msg_id)
                        repo.increment_sent(campaign_id)
                        s.commit()

                        bus.send_progress.emit(campaign_id, camp.sent_count, contact.email)
                        bus.log_line.emit(f"  ✓ {contact.email}")

                    except Exception as exc:
                        log.error("Send failed → %s: %s", contact.email, exc)
                        repo.mark_send(send_rec.id, "failed", error=str(exc))
                        s.commit()
                        bus.log_line.emit(f"  ✗ {contact.email}: {exc}")

                if smtp_svc:
                    smtp_svc.close()
                if gmail_svc:
                    # persist refreshed token
                    refreshed = gmail_svc.refreshed_credentials_json()
                    from app.core.crypto import encrypt
                    acc.oauth_token_enc = encrypt(refreshed)
                    s.commit()

                final = "paused" if stop_ev.is_set() else "completed"
                repo.update_status(campaign_id, final)
                s.commit()
                bus.send_complete.emit(campaign_id)
                bus.log_line.emit(f"[Campaign {campaign_id}] {final.capitalize()}.")

        except Exception as exc:
            log.exception("Campaign %d fatal: %s", campaign_id, exc)
            with get_session() as s:
                CampaignRepository(s).update_status(campaign_id, "failed")
            bus.log_line.emit(f"[Campaign {campaign_id}] FAILED: {exc}")
        finally:
            _active.pop(campaign_id, None)
