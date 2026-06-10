"""python-docx Word template filling. Phase 3 feature."""
from pathlib import Path
from app.models.contact import Contact
from app.services.content.personalization import build_context
from app.core.logger import get_logger

log = get_logger(__name__)


def fill_template(template_path: Path, contact: Contact, output_path: Path) -> Path:
    from docx import Document

    doc = Document(str(template_path))
    ctx = build_context(contact)

    def _replace(text: str) -> str:
        for key, val in ctx.items():
            text = text.replace(f"{{{key}}}", val)
        return text

    for para in doc.paragraphs:
        for run in para.runs:
            run.text = _replace(run.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.text = _replace(run.text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    log.info("Word doc saved: %s", output_path)
    return output_path


def docx_to_pdf(docx_path: Path, output_path: Path) -> Path:
    try:
        import docx2pdf
        docx2pdf.convert(str(docx_path), str(output_path))
        return output_path
    except ImportError:
        raise RuntimeError("docx2pdf not installed")
