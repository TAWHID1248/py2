"""HTML → PDF: WeasyPrint primary, reportlab fallback, pdfkit tertiary."""
from pathlib import Path
from app.core.logger import get_logger

log = get_logger(__name__)


def html_to_pdf(html: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # WeasyPrint — best CSS support
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        font_config = FontConfiguration()
        HTML(string=html).write_pdf(
            str(output_path),
            font_config=font_config,
        )
        log.debug("PDF via WeasyPrint: %s", output_path.name)
        return output_path
    except Exception as e:
        log.warning("WeasyPrint failed (%s), trying pdfkit…", e)

    # pdfkit (wkhtmltopdf wrapper)
    try:
        import pdfkit
        pdfkit.from_string(html, str(output_path))
        log.debug("PDF via pdfkit: %s", output_path.name)
        return output_path
    except Exception as e:
        log.warning("pdfkit failed (%s), using reportlab…", e)

    # reportlab — pure Python, always available
    _html_to_pdf_reportlab(html, output_path)
    log.debug("PDF via reportlab: %s", output_path.name)
    return output_path


def _html_to_pdf_reportlab(html: str, output_path: Path):
    """Strip tags and render as basic reportlab PDF."""
    import re
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors

    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").strip()

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle("body", parent=styles["Normal"],
                                fontSize=11, leading=16, spaceAfter=8)
    story = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(line, body_style))
        else:
            story.append(Spacer(1, 6))
    doc.build(story)


def merge_pdfs(paths: list[Path], output_path: Path) -> Path:
    from pypdf import PdfWriter
    writer = PdfWriter()
    for p in paths:
        writer.append(str(p))
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def split_pdf(input_path: Path, output_dir: Path) -> list[Path]:
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(input_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out = output_dir / f"page_{i+1:04d}.pdf"
        with open(out, "wb") as f:
            writer.write(f)
        paths.append(out)
    return paths


def add_watermark(input_path: Path, watermark_text: str, output_path: Path) -> Path:
    import io
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from pypdf import PdfReader, PdfWriter

    packet = io.BytesIO()
    c = rl_canvas.Canvas(packet, pagesize=A4)
    c.setFont("Helvetica", 48)
    c.setFillColorRGB(0.8, 0.8, 0.8, alpha=0.25)
    c.saveState()
    c.translate(A4[0] / 2, A4[1] / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, watermark_text)
    c.restoreState()
    c.save()
    packet.seek(0)

    wm = PdfReader(packet)
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm.pages[0])
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def generate_campaign_report_pdf(rows: list[dict], title: str, output_path: Path) -> Path:
    """Render a campaign statistics table as a PDF report."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from datetime import datetime

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Spacer(1, 0.5*cm),
    ]

    if rows:
        headers = list(rows[0].keys())
        data = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]
        col_w = (landscape(A4)[0] - 3*cm) / len(headers)
        tbl = Table(data, colWidths=[col_w] * len(headers), repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#313244")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#89b4fa")),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#1e1e2e"), colors.HexColor("#181825")]),
            ("TEXTCOLOR",  (0, 1), (-1, -1), colors.HexColor("#cdd6f4")),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#45475a")),
            ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)

    doc.build(story)
    return output_path
