"""
Render document pages into images for OCR or a vision model.

Owned by: Developer 4 (Multimodal Engineer)

Works from bytes, never a path: the resolver owns all file access, so nothing
downstream of the security boundary touches the filesystem.
"""

import io
import logging
from dataclasses import dataclass
from typing import Iterator, Optional

import pymupdf
from PIL import Image, UnidentifiedImageError

from workbench.multimodal.errors import (
    DocumentEncryptedError,
    DocumentUnreadableError,
)

logger = logging.getLogger(__name__)

DEFAULT_DPI = 300
PDF_POINTS_PER_INCH = 72.0


@dataclass
class RenderedPage:
    page_index: int
    image: Image.Image
    png_bytes: bytes
    width_px: int
    height_px: int
    dpi: Optional[int]
    has_text_layer: bool


def _to_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_pdf_pages(
    content: bytes,
    dpi: int = DEFAULT_DPI,
    max_pages: Optional[int] = None,
) -> Iterator[RenderedPage]:
    """Yield each PDF page as an image. Lazy: one page in memory at a time."""
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise DocumentUnreadableError(f"Could not open PDF: {exc}") from exc

    try:
        if document.needs_pass:
            raise DocumentEncryptedError("Document is password-protected")

        zoom = dpi / PDF_POINTS_PER_INCH
        matrix = pymupdf.Matrix(zoom, zoom)
        limit = len(document) if max_pages is None else min(max_pages, len(document))

        for index in range(limit):
            page = document[index]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes(
                "RGB", (pixmap.width, pixmap.height), pixmap.samples
            )
            yield RenderedPage(
                page_index=index,
                image=image,
                png_bytes=_to_png(image),
                width_px=pixmap.width,
                height_px=pixmap.height,
                dpi=dpi,
                has_text_layer=bool(page.get_text("text").strip()),
            )
    finally:
        document.close()


def load_single_image(content: bytes) -> RenderedPage:
    """Treat a standalone image as a one-page document, so one code path
    serves both PDFs and photographs."""
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise DocumentUnreadableError(f"Could not open image: {exc}") from exc

    image = image.convert("RGB")
    return RenderedPage(
        page_index=0,
        image=image,
        png_bytes=_to_png(image),
        width_px=image.width,
        height_px=image.height,
        dpi=None,
        has_text_layer=False,
    )
