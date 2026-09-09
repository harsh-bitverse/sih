"""
Port: the raw OCR capability.

Owned by: Developer 4 (Multimodal Engineer)

Named OcrBackend, not OcrEngine, to avoid confusion with the public
workbench.multimodal.ocr.OCREngine interface. This port is the low-level
word-recognition step; OCREngine is the subsystem-facing service.

pipeline/ depends on THIS. Never on pytesseract, paddleocr, or any concrete
engine. Swapping backends means adding an adapter and one config change.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol, runtime_checkable

from PIL import Image


@dataclass(frozen=True)
class PixelBox:
    """Backend-native coordinates: pixels, origin top-left, of the given image."""
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class OcrWord:
    """One recognised word, with the backend's own measured confidence."""
    text: str
    box: PixelBox
    confidence: Optional[float]
    line_id: str


@runtime_checkable
class OcrBackend(Protocol):
    @property
    def name(self) -> str:
        """Stable identity recorded in evidence, e.g. 'tesseract-5.5.3'."""
        ...

    def recognize(self, image: Image.Image) -> List[OcrWord]:
        """Return recognised words in reading order. May return []."""
        ...
