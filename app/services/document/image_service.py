"""Image manipulation — Pillow (always) + Wand/ImageMagick (optional)."""
from pathlib import Path
from app.core.logger import get_logger

log = get_logger(__name__)

# Check Wand / ImageMagick availability once
try:
    from wand.image import Image as WandImage
    _HAS_WAND = True
except Exception:
    _HAS_WAND = False
    log.info("Wand/ImageMagick not available — using Pillow-only image ops")


# ── Pillow operations ──────────────────────────────────────────────────────────

def resize(input_path: Path, width: int, height: int, output_path: Path) -> Path:
    from PIL import Image
    with Image.open(str(input_path)) as img:
        img = img.resize((width, height), Image.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
    return output_path


def crop(input_path: Path, box: tuple[int, int, int, int], output_path: Path) -> Path:
    """box = (left, upper, right, lower)"""
    from PIL import Image
    with Image.open(str(input_path)) as img:
        cropped = img.crop(box)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(str(output_path))
    return output_path


def add_text_overlay(
    input_path: Path,
    text: str,
    output_path: Path,
    position: tuple[int, int] = (20, 20),
    font_size: int = 36,
    color: tuple = (255, 255, 255, 220),
) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    with Image.open(str(input_path)).convert("RGBA") as img:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        draw.text(position, text, fill=color, font=font)
        combined = Image.alpha_composite(img, overlay)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.convert("RGB").save(str(output_path))
    return output_path


def add_logo(
    base_path: Path,
    logo_path: Path,
    output_path: Path,
    position: str = "bottom-right",
    margin: int = 20,
    max_logo_width: int = 120,
) -> Path:
    from PIL import Image
    with Image.open(str(base_path)).convert("RGBA") as base:
        with Image.open(str(logo_path)).convert("RGBA") as logo:
            # scale logo proportionally
            ratio = max_logo_width / logo.width
            logo = logo.resize(
                (int(logo.width * ratio), int(logo.height * ratio)), Image.LANCZOS
            )
            bw, bh = base.size
            lw, lh = logo.size
            positions = {
                "top-left":     (margin, margin),
                "top-right":    (bw - lw - margin, margin),
                "bottom-left":  (margin, bh - lh - margin),
                "bottom-right": (bw - lw - margin, bh - lh - margin),
                "center":       ((bw - lw) // 2, (bh - lh) // 2),
            }
            xy = positions.get(position, positions["bottom-right"])
            base.paste(logo, xy, logo)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            base.convert("RGB").save(str(output_path))
    return output_path


def convert_format(input_path: Path, output_path: Path) -> Path:
    from PIL import Image
    with Image.open(str(input_path)) as img:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
    return output_path


# ── Wand / ImageMagick operations ─────────────────────────────────────────────

def apply_effect(input_path: Path, effect: str, output_path: Path) -> Path:
    """effect: blur | sharpen | grayscale | sepia | emboss"""
    if not _HAS_WAND:
        log.warning("Wand not available — skipping effect '%s'", effect)
        return input_path

    from wand.image import Image as WI
    with WI(filename=str(input_path)) as img:
        if effect == "blur":
            img.blur(radius=0, sigma=3)
        elif effect == "sharpen":
            img.sharpen(radius=0, sigma=2)
        elif effect == "grayscale":
            img.transform_colorspace("gray")
        elif effect == "sepia":
            img.sepia_tone(threshold=0.8)
        elif effect == "emboss":
            img.emboss(radius=0, sigma=1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(filename=str(output_path))
    return output_path


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """Rasterise each PDF page to a PNG using Wand."""
    if not _HAS_WAND:
        raise RuntimeError("Wand/ImageMagick required for PDF-to-image conversion")

    from wand.image import Image as WI
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with WI(filename=str(pdf_path), resolution=dpi) as pdf:
        for i, page in enumerate(pdf.sequence):
            with WI(page) as pg:
                pg.format = "png"
                out = output_dir / f"page_{i+1:04d}.png"
                pg.save(filename=str(out))
                paths.append(out)
    return paths


def html_to_image(html: str, output_path: Path) -> Path:
    """Convert HTML to image via imgkit (wkhtmltopdf) or Playwright."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import imgkit
        imgkit.from_string(html, str(output_path))
        return output_path
    except Exception:
        pass
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.screenshot(path=str(output_path), full_page=True)
            browser.close()
        return output_path
    except Exception as e:
        raise RuntimeError(f"html_to_image failed: {e}")
