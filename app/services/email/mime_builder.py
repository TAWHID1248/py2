"""Construct MIME email messages."""
import uuid
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from pathlib import Path


def build_message(
    from_addr: str,
    from_name: str,
    to_addr: str,
    subject: str,
    html_body: str | None = None,
    text_body: str | None = None,
    reply_to: str | None = None,
    attachments: list[Path] | None = None,
    inline_images: dict[str, Path] | None = None,  # cid → path
    tracking_pixel_url: str | None = None,
    unsubscribe_url: str | None = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = f"<{uuid.uuid4()}@bm2ultra>"
    if reply_to:
        msg["Reply-To"] = reply_to
    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"

    alt = MIMEMultipart("alternative")

    if text_body:
        alt.attach(MIMEText(text_body, "plain", "utf-8"))

    if html_body:
        if tracking_pixel_url:
            pixel = f'<img src="{tracking_pixel_url}" width="1" height="1" alt="" />'
            html_body = html_body + pixel
        if unsubscribe_url:
            link = f'<p style="font-size:11px;color:#888;"><a href="{unsubscribe_url}">Unsubscribe</a></p>'
            html_body = html_body + link
        if inline_images:
            related = MIMEMultipart("related")
            related.attach(MIMEText(html_body, "html", "utf-8"))
            for cid, path in (inline_images or {}).items():
                with open(path, "rb") as f:
                    img = MIMEImage(f.read())
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header("Content-Disposition", "inline", filename=path.name)
                related.attach(img)
            alt.attach(related)
        else:
            alt.attach(MIMEText(html_body, "html", "utf-8"))

    msg.attach(alt)

    for att_path in attachments or []:
        with open(att_path, "rb") as f:
            data = f.read()
        part = MIMEApplication(data, Name=att_path.name)
        part.add_header("Content-Disposition", "attachment", filename=att_path.name)
        msg.attach(part)

    return msg
