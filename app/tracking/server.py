"""FastAPI tracking server running as a daemon thread on localhost:8765."""
import threading
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
import uvicorn
from app.core.config import settings
from app.core.logger import get_logger
from app.tracking.pixel_handler import gif_bytes, record_open
from app.tracking.click_handler import record_click

log = get_logger(__name__)
app = FastAPI(docs_url=None, redoc_url=None)


@app.get("/track/open/{token}")
async def open_pixel(token: str, request: Request):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    try:
        record_open(token, ip, ua)
    except Exception as exc:
        log.error("Open tracking error: %s", exc)
    return Response(content=gif_bytes(), media_type="image/gif")


@app.get("/track/click/{token}")
async def click_redirect(token: str, url: str, request: Request):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    try:
        record_click(token, url, ip, ua)
    except Exception as exc:
        log.error("Click tracking error: %s", exc)
    return RedirectResponse(url=url, status_code=302)


@app.get("/unsub/{token}")
async def unsubscribe(token: str, request: Request):
    from app.core.database import get_session
    from app.repositories.campaign_repository import CampaignRepository
    from app.repositories.contact_repository import ContactRepository

    with get_session() as s:
        send = CampaignRepository(s).get_send_by_token(token)
        if send:
            contact = s.get(send.__class__, send.contact_id)
            if contact:
                ContactRepository(s).suppress(contact.email, reason="unsubscribed")
    return Response(content="<h2>You have been unsubscribed.</h2>", media_type="text/html")


def start_tracking_server():
    config = uvicorn.Config(
        app,
        host=settings.tracking_host,
        port=settings.tracking_port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    log.info(
        "Tracking server started on %s:%d", settings.tracking_host, settings.tracking_port
    )
