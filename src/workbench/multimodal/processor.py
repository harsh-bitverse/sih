"""
Multimodal Processor Interface.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

import logging
import time
from typing import Dict, List, Optional

from workbench.core.artifacts import Artifact
from workbench.multimodal.adapters.unavailable_vision_client import (
    UnavailableVisionClient,
)
from workbench.multimodal.mapping import (
    outcome_metadata,
    outcome_to_errors,
    outcome_to_evidence,
    page_artifact_to_artifact,
)
from workbench.multimodal.ocr import TesseractOCREngine
from workbench.multimodal.pipeline.internal_model import ExtractionOutcome
from workbench.multimodal.pipeline.page_render import DEFAULT_DPI
from workbench.multimodal.ports.artifact_store import ArtifactStore
from workbench.multimodal.ports.ocr_backend import OcrBackend
from workbench.multimodal.ports.resource_resolver import ResourceResolver
from workbench.multimodal.ports.vision_model import VisionModelClient
from workbench.multimodal.schemas import (
    SUPPORTED_MODALITIES,
    Modality,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)
from workbench.multimodal.vision import LocalVisionEngine

logger = logging.getLogger(__name__)

DEFAULT_VISION_OBJECTIVE = (
    "Identify visible equipment condition, defects such as corrosion, leaks, "
    "cracks or damage, and any readable labels or tag numbers."
)


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
    """Runs the requested modalities and merges them into one result.

    Never raises for per-document problems. Failures become errors in the
    result, because an orchestrator needs a contract object it can record
    and reason about, not an exception to guess at.

    With no vision client injected, vision requests fail honestly via
    UnavailableVisionClient rather than returning an empty result that could
    be mistaken for "no defects found".
    """

    def __init__(
        self,
        backend: OcrBackend,
        resolver: ResourceResolver,
        artifact_store: ArtifactStore,
        dpi: int = DEFAULT_DPI,
        vision_client: Optional[VisionModelClient] = None,
        accept_model_confidence: bool = True,
    ) -> None:
        self._backend = backend
        self._resolver = resolver
        self._artifact_store = artifact_store
        self._dpi = dpi
        self._vision_client = vision_client or UnavailableVisionClient()
        self._accept_model_confidence = accept_model_confidence

    def process(self, request: MultimodalRequest) -> MultimodalResult:
        started = time.monotonic()
        requested = self._normalise(request.modalities)
        unsupported = sorted(set(requested) - SUPPORTED_MODALITIES)

        outcomes: Dict[str, ExtractionOutcome] = {}
        if Modality.OCR.value in requested:
            outcomes[Modality.OCR.value] = self._run_ocr(request)
        if Modality.VISION.value in requested:
            outcomes[Modality.VISION.value] = self._run_vision(request)

        evidence = []
        errors: List[str] = []
        artifacts: Dict[str, Artifact] = {}
        modality_metadata = {}

        for modality, outcome in outcomes.items():
            evidence.extend(outcome_to_evidence(outcome))
            errors.extend(f"[{modality}] {e}" for e in outcome_to_errors(outcome))
            for page_artifact in outcome.page_artifacts:
                # OCR and vision may render the same page; content-addressed
                # ids make that one artifact, listed once.
                if page_artifact.artifact_id not in artifacts:
                    artifacts[page_artifact.artifact_id] = page_artifact_to_artifact(
                        page_artifact,
                        request.request_context,
                        self._artifact_store.location_of(page_artifact.artifact_id),
                    )
            modality_metadata[modality] = outcome_metadata(outcome)

        if unsupported:
            errors.append(
                "unsupported modalities requested (ignored): " + ", ".join(unsupported)
            )

        return MultimodalResult(
            # Propagated unchanged: the audit tree depends on this identity.
            request_context=request.request_context,
            status=self._status_for(bool(evidence), bool(errors)),
            evidence=evidence,
            artifacts=list(artifacts.values()),
            errors=errors,
            metadata={
                "subsystem": "multimodal",
                "requested_modalities": requested,
                "unsupported_modalities": unsupported,
                "modalities": modality_metadata,
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _normalise(modalities: List[str]) -> List[str]:
        seen: List[str] = []
        for modality in modalities or [Modality.OCR.value]:
            value = modality.strip().lower()
            if value and value not in seen:
                seen.append(value)
        return seen or [Modality.OCR.value]

    def _run_ocr(self, request: MultimodalRequest) -> ExtractionOutcome:
        engine = TesseractOCREngine(
            backend=self._backend,
            resolver=self._resolver,
            artifact_store=self._artifact_store,
            dpi=int(request.parameters.get("dpi", self._dpi)),
            min_line_confidence=float(request.parameters.get("min_line_confidence", 0.0)),
        )
        return engine.extract(request.resource, max_pages=request.parameters.get("max_pages"))

    def _run_vision(self, request: MultimodalRequest) -> ExtractionOutcome:
        engine = LocalVisionEngine(
            client=self._vision_client,
            resolver=self._resolver,
            artifact_store=self._artifact_store,
            accept_model_confidence=self._accept_model_confidence,
        )
        objective = str(request.parameters.get("objective") or DEFAULT_VISION_OBJECTIVE)
        return engine.analyze(request.resource, objective)

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
