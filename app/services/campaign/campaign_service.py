"""Campaign state machine — SMTP/Gmail routing, Faker names, per-contact PDF/Word attachments,
multi-account rotation."""
import uuid
import threading
from pathlib import Path
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


def _get_sender(acc, acc_repo):
    """Return (smtp_service | None, gmail_service | None, password)."""
    if not acc:
        return None, None, ""
    if acc.account_type == "gmail" and acc.oauth_token_enc:
        from app.core.crypto import decrypt
        from app.services.email.gmail_service import GmailService
        return None, GmailService(decrypt(acc.oauth_token_enc)), ""
    pw = acc_repo.get_smtp_password(acc) or ""
    return SMTPService(acc, pw), None, pw


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
        _active.pop(campaign_id, None) and _active.get(campaign_id, threading.Event()).set()
        ev = _active.pop(campaign_id, None)
        if ev:
            ev.set()
        with get_session() as s:
            CampaignRepository(s).update_status(campaign_id, "stopped")

    def resume(self, campaign_id: int):
        self.start(campaign_id)

    # ── main run loop ──────────────────────────────────────────────────────────

    def _run(self, campaign_id: int, stop_ev: threading.Event):
        try:
            with get_session() as s:
                repo      = CampaignRepository(s)
                acc_repo  = AccountRepository(s)
                cont_repo = ContactRepository(s)

                camp = repo.get(campaign_id)
                if not camp:
                    return
                repo.update_status(campaign_id, "running")
                bus.log_line.emit(f"[Campaign {campaign_id}] '{camp.name}' starting…")

                # ── resolve template ───────────────────────────────────────────
                from app.models.template import Template
                tmpl = s.get(Template, camp.template_id)
                if not tmpl:
                    bus.log_line.emit(f"[Campaign {campaign_id}] ERROR: template not found")
                    repo.update_status(campaign_id, "failed")
                    return

                # ── account pool / rotation ────────────────────────────────────
                rotation_svc = None
                if camp.use_account_rotation:
                    from app.services.campaign.account_rotation_service import AccountRotationService
                    pool = acc_repo.active()
                    if pool:
                        rotation_svc = AccountRotationService(pool)

                primary_acc = acc_repo.get(camp.account_id)

                # ── contacts (skip already sent) ───────────────────────────────
                from app.models.campaign import CampaignSend
                already_sent = {
                    cs.contact_id
                    for cs in s.query(CampaignSend)
                    .filter_by(campaign_id=campaign_id)
                    .filter(CampaignSend.status == "sent")
                    .all()
                }
                contacts = [
                    c for c in cont_repo.contacts_in_list(camp.list_id)
                    if c.id not in already_sent
                ]

                tmpl_svc = TemplateService()
                throttle  = ThrottleService(
                    delay_seconds=camp.throttle_delay,
                    hourly_limit=primary_acc.hourly_limit if primary_acc else 100,
                )

                pixel_base = f"http://{settings.tracking_host}:{settings.tracking_port}/track/open/"
                unsub_base = f"http://{settings.tracking_host}:{settings.tracking_port}/unsub/"

                # ── Phase 3: attachment config ─────────────────────────────────
                word_tmpl_path = Path(camp.word_template_path) if camp.word_template_path else None

                # ── send loop ──────────────────────────────────────────────────
                for contact in contacts:
                    if stop_ev.is_set():
                        break

                    # choose account
                    if rotation_svc:
                        try:
                            acc = rotation_svc.next_account()
                        except RuntimeError as e:
                            bus.log_line.emit(f"[Campaign {campaign_id}] {e}")
                            break
                    else:
                        acc = primary_acc

                    token    = uuid.uuid4().hex
                    send_rec = repo.create_send(campaign_id, contact.id, token)
                    s.commit()

                    try:
                        subject, html, text = tmpl_svc.render(
                            tmpl, contact,
                            use_spintax=camp.use_spintax,
                            use_synonyms=camp.use_synonyms,
                        )

                        # from-name: spintax or Faker
                        from_name = camp.from_name or (acc.name if acc else "")
                        if camp.use_spintax and "{" in (from_name or ""):
                            from app.services.content.spinner_service import spin
                            from_name = spin(from_name, seed=contact.id)
                        elif not from_name:
                            from_name = random_name()

                        # ── Phase 3: build per-contact attachments ─────────────
                        attachments: list[Path] = []
                        name_pat = camp.attachment_name_pattern or "attachment_{email}"

                        if camp.attach_pdf and camp.pdf_template_html:
                            from app.services.document.attachment_service import (
                                generate_pdf_for_contact, cleanup_contact_attachments,
                            )
                            pdf_path = generate_pdf_for_contact(
                                camp.pdf_template_html, contact,
                                name_pattern=name_pat.replace(".docx", ".pdf"),
                            )
                            attachments.append(pdf_path)

                        if camp.attach_word and word_tmpl_path and word_tmpl_path.exists():
                            from app.services.document.attachment_service import (
                                generate_word_for_contact,
                            )
                            ext = ".pdf" if name_pat.endswith(".pdf") else ".docx"
                            word_path = generate_word_for_contact(
                                word_tmpl_path, contact,
                                name_pattern=name_pat,
                                as_pdf=ext == ".pdf",
                            )
                            attachments.append(word_path)

                        msg = build_message(
                            from_addr=acc.email if acc else "noreply@example.com",
                            from_name=from_name,
                            to_addr=contact.email,
                            subject=subject,
                            html_body=html,
                            text_body=text,
                            reply_to=camp.reply_to,
                            attachments=attachments if attachments else None,
                            tracking_pixel_url=pixel_base + token,
                            unsubscribe_url=unsub_base + token if camp.inject_unsubscribe else None,
                        )

                        throttle.wait()

                        # send via SMTP or Gmail
                        smtp_svc, gmail_svc, _ = _get_sender(acc, acc_repo)
                        if gmail_svc:
                            msg_id = gmail_svc.send(msg)
                            # persist refreshed token
                            from app.core.crypto import encrypt
                            acc.oauth_token_enc = encrypt(gmail_svc.refreshed_credentials_json())
                            s.commit()
                        elif smtp_svc:
                            msg_id = smtp_svc.send(msg)
                            smtp_svc.close()
                        else:
                            msg_id = f"simulated-{uuid.uuid4().hex}"

                        if rotation_svc:
                            rotation_svc.record_send(acc.id)

                        repo.mark_send(send_rec.id, "sent", message_id=msg_id)
                        repo.increment_sent(campaign_id)
                        s.commit()

                        # clean up temp attachment files
                        if attachments:
                            from app.services.document.attachment_service import (
                                cleanup_contact_attachments,
                            )
                            cleanup_contact_attachments(contact.id)

                        bus.send_progress.emit(campaign_id, camp.sent_count, contact.email)
                        bus.log_line.emit(f"  ✓ {contact.email}")

                    except Exception as exc:
                        log.error("Send failed → %s: %s", contact.email, exc)
                        repo.mark_send(send_rec.id, "failed", error=str(exc))
                        s.commit()
                        bus.log_line.emit(f"  ✗ {contact.email}: {exc}")

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
