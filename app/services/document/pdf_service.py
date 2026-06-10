"""HTML → PDF using WeasyPrint (primary) or pdfkit (fallback). Phase 3 feature."""
from pathlib import Path
from app.core.logger import get_logger

log = get_logger(__name__)


def html_to_pdf(html: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(output_path))
        log.info("PDF (weasyprint): %s", output_path)
        return output_path
    except ImportError:
        pass
    try:
        import pdfkit
        pdfkit.from_string(html, str(output_path))
        log.info("PDF (pdfkit): %s", output_path)
        return output_path
    except ImportError:
        raise RuntimeError("Neither weasyprint nor pdfkit is available")


def merge_pdfs(paths: list[Path], output_path: Path) -> Path:
    from pypdf import PdfWriter
    writer = PdfWriter()
    for p in paths:
        writer.append(str(p))
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def add_watermark(input_path: Path, watermark_text: str, output_path: Path) -> Path:
    from reportlab.pdfgen import canvas as rl_canvas
    from pypdf import PdfWriter, PdfReader
    import io

    packet = io.BytesIO()
    c = rl_canvas.Canvas(packet)
    c.setFont("Helvetica", 40)
    c.setFillColorRGB(0.8, 0.8, 0.8, alpha=0.3)
    c.saveState()
    c.translate(300, 400)
    c.rotate(45)
    c.drawCentredString(0, 0, watermark_text)
    c.restoreState()
    c.save()
    packet.seek(0)

    wm_reader = PdfReader(packet)
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm_reader.pages[0])
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path
