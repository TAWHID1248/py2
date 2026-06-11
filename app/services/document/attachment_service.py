"""Per-contact dynamic PDF/Word attachment generation."""
import re
from pathlib import Path
from app.models.contact import Contact
from app.services.content.personalization import build_context, render
from app.services.document.pdf_service import html_to_pdf
from app.services.document.word_service import fill_template, docx_to_pdf
from app.core.config import settings
from app.core.logger import get_logger

log = get_logger(__name__)

_ATTACH_DIR = settings.attachments_dir / "generated"


def _safe_filename(pattern: str, contact: Contact) -> str:
    ctx = build_context(contact)
    name = pattern
    for k, v in ctx.items():
        name = name.replace(f"{{{k}}}", re.sub(r'[\\/:*?"<>|]', "_", v or ""))
    return name or f"attachment_{contact.id}"


def generate_pdf_for_contact(
    html_template: str,
    contact: Contact,
    name_pattern: str = "document_{email}.pdf",
) -> Path:
    """Render html_template with contact merge fields → PDF file."""
    personalised_html = render(html_template, contact)
    filename = _safe_filename(name_pattern, contact)
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    out = _ATTACH_DIR / str(contact.id) / filename
    return html_to_pdf(personalised_html, out)


def generate_word_for_contact(
    template_path: Path,
    contact: Contact,
    name_pattern: str = "document_{email}.docx",
    as_pdf: bool = False,
) -> Path:
    """Fill Word template with contact data. Optionally convert to PDF."""
    filename = _safe_filename(name_pattern, contact)
    if as_pdf:
        docx_out = _ATTACH_DIR / str(contact.id) / filename.replace(".pdf", ".docx")
        pdf_out  = _ATTACH_DIR / str(contact.id) / filename
        fill_template(template_path, contact, docx_out)
        return docx_to_pdf(docx_out, pdf_out)
    if not (filename.endswith(".docx") or filename.endswith(".doc")):
        filename += ".docx"
    out = _ATTACH_DIR / str(contact.id) / filename
    return fill_template(template_path, contact, out)


def cleanup_contact_attachments(contact_id: int):
    """Remove temp generated files for a contact after send."""
    import shutil
    d = _ATTACH_DIR / str(contact_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
