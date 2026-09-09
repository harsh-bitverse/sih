"""
Tesseract implementation of the OcrBackend port.

Owned by: Developer 4 (Multimodal Engineer)

The ONLY module permitted to import pytesseract.

image_to_data is used rather than image_to_string because it returns
per-word bounding boxes, per-word confidence and line grouping. A flat text
blob would make the visual-grounding requirement impossible to satisfy.
"""

import logging
from typing import List, Optional

import pytesseract
from PIL import Image
from pytesseract import Output, TesseractError, TesseractNotFoundError

from workbench.multimodal.errors import OcrBackendUnavailableError
from workbench.multimodal.ports.ocr_backend import OcrWord, PixelBox

logger = logging.getLogger(__name__)

_NOT_FOUND_HINT = (
    "Tesseract binary not found. Install tesseract-ocr and put it on PATH, "
    "or pass binary_path=... to TesseractOcrBackend."
)


class TesseractOcrBackend:
    """CPU-only OCR. Emits engine-measured per-word confidence."""

    def __init__(
        self,
        lang: str = "eng",
        psm: int = 3,
        binary_path: Optional[str] = None,
    ) -> None:
        self._lang = lang
        self._config = f"--psm {psm}"
        self._version: Optional[str] = None
        # Configuration, not PATH archaeology: the demo machine may install
        # Tesseract somewhere other than the developer laptop.
        if binary_path:
            pytesseract.pytesseract.tesseract_cmd = binary_path

    @property
    def name(self) -> str:
        if self._version is None:
            try:
                raw = str(pytesseract.get_tesseract_version())
            except TesseractNotFoundError as exc:
                raise OcrBackendUnavailableError(_NOT_FOUND_HINT) from exc
            self._version = raw.split()[0].lstrip("v")
        return f"tesseract-{self._version}"

    def recognize(self, image: Image.Image) -> List[OcrWord]:
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self._lang,
                config=self._config,
                output_type=Output.DICT,
            )
        except TesseractNotFoundError as exc:
            raise OcrBackendUnavailableError(_NOT_FOUND_HINT) from exc
        except TesseractError as exc:
            raise OcrBackendUnavailableError(f"Tesseract failed: {exc}") from exc

        words: List[OcrWord] = []
        for index in range(len(data["text"])):
            text = (data["text"][index] or "").strip()
            if not text:
                continue

            raw_conf = float(data["conf"][index])
            if raw_conf < 0:
                continue  # -1 marks layout rows, not recognised words

            words.append(
                OcrWord(
                    text=text,
                    box=PixelBox(
                        left=int(data["left"][index]),
                        top=int(data["top"][index]),
                        width=int(data["width"][index]),
                        height=int(data["height"][index]),
                    ),
                    confidence=max(0.0, min(1.0, raw_conf / 100.0)),
                    line_id=(
                        f'{data["block_num"][index]}-'
                        f'{data["par_num"][index]}-'
                        f'{data["line_num"][index]}'
                    ),
                )
            )

        logger.debug("tesseract recognised %d words", len(words))
        return words
