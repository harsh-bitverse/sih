"""
Multimodal Processor Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

import logging
import time
from typing import Optional

from workbench.multimodal.mapping import (
    outcome_metadata,
    outcome_to_errors,
    outcome_to_evidence,
    page_artifact_to_artifact,
)
from workbench.multimodal.ocr import TesseractOCREngine
from workbench.multimodal.ports.artifact_store import ArtifactStore
from workbench.multimodal.ports.ocr_backend import OcrBackend
from workbench.multimodal.ports.resource_resolver import ResourceResolver
from workbench.multimodal.pipeline.page_render import DEFAULT_DPI
from workbench.multimodal.schemas import (
    SUPPORTED_MODALITIES,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)

logger = logging.getLogger(__name__)


class MultimodalProcessor:
    """
    Main entrypoint interface for multimodal processing requests.
    """

    def process(self, request: MultimodalRequest) -> MultimodalResult:
        """
        Processes document/image/audio input and returns structured MultimodalResult.
        """
        raise NotImplementedError("MultimodalProcessor.process will be implemented by Developer 4.")


class DefaultMultimodalProcessor(MultimodalProcessor):
    """Slice 1 processor: OCR only.

    Never raises for per-document problems. A failure becomes a FAILED result
    with populated errors, because an orchestrator needs a contract object it
    can record and reason about, not an exception to guess at.
    """

    def __init__(
        self,
        backend: OcrBackend,
        resolver: ResourceResolver,
        artifact_store: ArtifactStore,
        dpi: int = DEFAULT_DPI,
    ) -> None:
        self._backend = backend
        self._resolver = resolver
        self._artifact_store = artifact_store
        self._dpi = dpi

    def process(self, request: MultimodalRequest) -> MultimodalResult:
        started = time.monotonic()
        requested = [m.lower() for m in request.modalities] or ["ocr"]
        unsupported = sorted(set(requested) - SUPPORTED_MODALITIES)

        engine = TesseractOCREngine(
            backend=self._backend,
            resolver=self._resolver,
            artifact_store=self._artifact_store,
            dpi=int(request.parameters.get("dpi", self._dpi)),
            min_line_confidence=float(
                request.parameters.get("min_line_confidence", 0.0)
            ),
        )
        max_pages: Optional[int] = request.parameters.get("max_pages")
        outcome = engine.extract(request.resource, max_pages=max_pages)

        artifacts = [
            page_artifact_to_artifact(
                page_artifact,
                request.request_context,
                self._artifact_store.location_of(page_artifact.artifact_id),
            )
            for page_artifact in outcome.page_artifacts
        ]

        errors = outcome_to_errors(outcome)
        if unsupported:
            errors.append(
                "unsupported modalities requested (ignored): "
                + ", ".join(unsupported)
            )

        metadata = outcome_metadata(
            outcome,
            extra={
                "requested_modalities": requested,
                "unsupported_modalities": unsupported,
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )

        return MultimodalResult(
            # Propagated unchanged: the audit tree depends on this identity.
            request_context=request.request_context,
            status=self._status_for(outcome.succeeded, bool(errors)),
            evidence=outcome_to_evidence(outcome),
            artifacts=artifacts,
            errors=errors,
            metadata=metadata,
        )

    @staticmethod
    def _status_for(has_evidence: bool, has_errors: bool) -> MultimodalStatus:
        """SUCCESS / PARTIAL / FAILED, per the architect's definitions.

        Useful evidence is never discarded because something else failed.
        """
        if not has_evidence:
            return MultimodalStatus.FAILED
        if has_errors:
            return MultimodalStatus.PARTIAL
        return MultimodalStatus.SUCCESS
