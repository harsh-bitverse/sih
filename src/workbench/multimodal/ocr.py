"""
OCR Engine Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from typing import List, Optional

from workbench.core.types import Evidence, ResourceReference
from workbench.multimodal.mapping import outcome_to_evidence
from workbench.multimodal.pipeline.extraction import OcrExtractionPipeline
from workbench.multimodal.pipeline.internal_model import ExtractionOutcome
from workbench.multimodal.pipeline.page_render import DEFAULT_DPI
from workbench.multimodal.ports.artifact_store import ArtifactStore
from workbench.multimodal.ports.ocr_backend import OcrBackend
from workbench.multimodal.ports.resource_resolver import ResourceResolver


class OCREngine:
    """
    Interface for optical character recognition engines.
    """

    def extract_text(self, resource: ResourceReference) -> list[Evidence]:
        """
        Extracts text bounding boxes and line evidence from document images.
        """
        raise NotImplementedError("OCREngine.extract_text will be implemented by Developer 4.")


class TesseractOCREngine(OCREngine):
    """OCR engine backed by the injected OcrBackend port.

    Despite the name this class is backend-agnostic: it is called Tesseract
    only because that is the backend wired in by default. Swapping to
    PaddleOCR means injecting a different OcrBackend, nothing more.
    """

    def __init__(
        self,
        backend: OcrBackend,
        resolver: ResourceResolver,
        artifact_store: ArtifactStore,
        dpi: int = DEFAULT_DPI,
        min_line_confidence: float = 0.0,
    ) -> None:
        self._pipeline = OcrExtractionPipeline(
            backend=backend,
            resolver=resolver,
            artifact_store=artifact_store,
            dpi=dpi,
            min_line_confidence=min_line_confidence,
        )

    def extract_text(self, resource: ResourceReference) -> list[Evidence]:
        """Contract method: evidence only.

        Page images are still stored, and every Evidence item still points at
        one via source_artifact. The core Artifact records for those images
        need a task_id, so they are emitted by MultimodalProcessor.process,
        which is the call that carries a RequestContext. Prefer process()
        when you need the artifact records too.
        """
        return outcome_to_evidence(self._pipeline.run(resource))

    def extract(
        self,
        resource: ResourceReference,
        max_pages: Optional[int] = None,
    ) -> ExtractionOutcome:
        """Internal richer form used by MultimodalProcessor."""
        return self._pipeline.run(resource, max_pages=max_pages)
