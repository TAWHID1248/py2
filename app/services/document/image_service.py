"""Image manipulation with Pillow + Wand. Phase 3 feature."""
from pathlib import Path


def resize(input_path: Path, width: int, height: int, output_path: Path) -> Path:
    from PIL import Image
    img = Image.open(str(input_path))
    img = img.resize((width, height), Image.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    return output_path


def add_text_overlay(input_path: Path, text: str, output_path: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(str(input_path)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 20), text, fill=(255, 255, 255, 200), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    return output_path


def html_to_image(html: str, output_path: Path) -> Path:
    try:
        import imgkit
        imgkit.from_string(html, str(output_path))
        return output_path
    except ImportError:
        raise RuntimeError("imgkit not installed")
