"""Generate test documents so no binaries are committed to the repo.

Commit the recipe, not the cake: a generator can be edited and reviewed,
a checked-in PDF cannot.
"""

import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

# Probe the environment rather than assuming it. A single hardcoded font path
# is an unstated assumption about the machine and breaks on other platforms.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/calibri.ttf",
)

LINES = [
    "MRPL - EQUIPMENT INSPECTION REPORT",
    "Report No: INS-2026-0473",
    "Unit: Crude Distillation Unit 2",
    "Equipment Tag: P-101B",
    "Inspection Date: 14-02-2026",
    "Inspector: R. Nayak",
    "",
    "OBSERVATIONS",
    "Surface corrosion noted on the lower flange.",
    "Estimated wall loss approximately 1.8 mm.",
    "Gasket shows signs of compression set.",
    "",
    "RECOMMENDATION",
    "Schedule flange replacement at next shutdown.",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise RuntimeError(
        "No TrueType font found. Tried:\n  "
        + "\n  ".join(FONT_CANDIDATES)
        + "\nAdd a path for your platform to FONT_CANDIDATES."
    )


def build_page_image(width: int = 1240, height: int = 1754) -> Image.Image:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(34)
    body_font = load_font(26)

    y = 120
    for index, line in enumerate(LINES):
        draw.text((110, y), line, fill="black",
                  font=title_font if index == 0 else body_font)
        y += 48 if index == 0 else 40

    return image.rotate(0.4, resample=Image.BICUBIC, fillcolor="white")


def write_scanned_pdf(path: Path) -> Path:
    """An image-only PDF: no text layer, like a real scan."""
    buffer = io.BytesIO()
    build_page_image().save(buffer, format="PNG")

    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=buffer.getvalue())
    document.save(path)
    document.close()
    return path


def write_digital_pdf(path: Path) -> Path:
    """A PDF WITH a real text layer, to prove text-layer detection works."""
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 100), "Native text layer present", fontsize=14)
    document.save(path)
    document.close()
    return path


def write_photograph(path: Path) -> Path:
    """A standalone image, exercising the non-PDF code path."""
    image = Image.new("RGB", (900, 500), "white")
    ImageDraw.Draw(image).text(
        (60, 200), "VALVE TAG V-204", fill="black", font=load_font(48)
    )
    image.save(path, format="PNG")
    return path
