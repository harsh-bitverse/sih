"""
The vision extraction pipeline.

Owned by: Developer 4 (Multimodal Engineer)

    ResourceReference
        -> resolver (SECURITY BOUNDARY)   -> bytes
        -> image or rendered PDF pages    -> PNG
        -> artifact store                 -> art_<hash>
        -> vision model (via port)        -> raw text        [UNTRUSTED]
        -> strict parse + validate        -> observations    (one retry)
        -> ExtractedFragment              -> VISION_MODEL confidence

Confidence from a vision model is a number the model generated, not a
measurement. It is recorded ONLY as ConfidenceSource.VISION_MODEL, with an
interpretation string saying so, or dropped entirely if the processor is
configured not to accept self-reported confidence.
"""

import hashlib
import logging
from typing import Iterable, List, Optional

from workbench.core.types import ConfidenceSource, ResourceReference
from workbench.multimodal.errors import (
    MultimodalError,
    ResourceAccessDeniedError,
    ResourceResolutionError,
    VisionModelUnavailableError,
    VisionOutputInvalidError,
)
from workbench.multimodal.pipeline.internal_model import (
    Confidence,
    ErrorStage,
    ExtractedFragment,
    ExtractionOutcome,
    FragmentKind,
    PageArtifact,
    PageProvenance,
    ProcessingIssue,
)
from workbench.multimodal.pipeline.page_render import (
    RenderedPage,
    load_single_image,
    render_pdf_pages,
)
from workbench.multimodal.pipeline.vision_output import (
    ParsedVisionOutput,
    build_prompt,
    parse_vision_output,
)
from workbench.multimodal.ports.artifact_store import ArtifactStore
from workbench.multimodal.ports.resource_resolver import (
    ResolvedResource,
    ResourceResolver,
)
from workbench.multimodal.ports.vision_model import VisionModelClient

logger = logging.getLogger(__name__)

# Vision models are slow and pages add up quickly; a page cap keeps one
# request from monopolising a shared GPU.
DEFAULT_VISION_DPI = 150
DEFAULT_MAX_VISION_PAGES = 5
DEFAULT_MAX_RETRIES = 1

SELF_REPORTED_NOTE = (
    "self-reported by the vision model; a generated value, not a calibrated "
    "probability. Not comparable with OCR_ENGINE confidence."
)


class VisionExtractionPipeline:
    def __init__(
        self,
        client: VisionModelClient,
        resolver: ResourceResolver,
        artifact_store: ArtifactStore,
        dpi: int = DEFAULT_VISION_DPI,
        max_pages: int = DEFAULT_MAX_VISION_PAGES,
        max_retries: int = DEFAULT_MAX_RETRIES,
        accept_model_confidence: bool = True,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._artifacts = artifact_store
        self._dpi = dpi
        self._max_pages = max_pages
        self._max_retries = max(0, max_retries)
        self._accept_model_confidence = accept_model_confidence

    def run(self, resource: ResourceReference, objective: str) -> ExtractionOutcome:
        outcome = ExtractionOutcome(resource_id=resource.resource_id)
        outcome.extractor = self._client.name

        try:
            resolved = self._resolver.resolve(resource)
        except (ResourceAccessDeniedError, ResourceResolutionError) as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.RESOLUTION,
                    message=str(exc),
                    resource_id=resource.resource_id,
                )
            )
            return outcome

        outcome.document_hash = hashlib.sha256(resolved.content).hexdigest()

        try:
            pages = self._pages_for(resolved)
        except MultimodalError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.RENDERING,
                    message=str(exc),
                    resource_id=resource.resource_id,
                )
            )
            return outcome

        for page in pages:
            outcome.page_count += 1
            model_down = self._process_page(page, resolved, objective, outcome)
            if model_down:
                # The model is unreachable; asking again per page only
                # multiplies the same error and the wait.
                break

        logger.info(
            "vision resource=%s pages=%d observations=%d issues=%d",
            resource.resource_id, outcome.page_count,
            len(outcome.fragments), len(outcome.issues),
        )
        return outcome

    # -- internals ---------------------------------------------------------

    def _pages_for(self, resolved: ResolvedResource) -> Iterable[RenderedPage]:
        if resolved.is_image:
            return [load_single_image(resolved.content)]
        return render_pdf_pages(
            resolved.content, dpi=self._dpi, max_pages=self._max_pages
        )

    def _process_page(
        self,
        page: RenderedPage,
        resolved: ResolvedResource,
        objective: str,
        outcome: ExtractionOutcome,
    ) -> bool:
        """Returns True if the model is unavailable, so the caller can stop."""
        try:
            artifact_id = self._artifacts.put(page.png_bytes, media_type="image/png")
        except MultimodalError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.RENDERING,
                    message=f"Could not store page image: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return False

        outcome.page_artifacts.append(
            PageArtifact(
                artifact_id=artifact_id,
                resource_id=resolved.resource_id,
                page_index=page.page_index,
                width_px=page.width_px,
                height_px=page.height_px,
                render_dpi=page.dpi,
                content_hash=hashlib.sha256(page.png_bytes).hexdigest(),
                source_filename=resolved.filename,
            )
        )

        try:
            parsed = self._ask_with_retry(page, objective)
        except VisionModelUnavailableError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=f"Vision model unavailable: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return True
        except VisionOutputInvalidError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.VALIDATION,
                    message=f"Model output rejected after retry: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return False
        except Exception as exc:
            logger.exception("vision model failed on page %d", page.page_index)
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=f"Vision model failed: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return False

        for note in parsed.notes:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.VALIDATION,
                    message=note,
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )

        self._emit(parsed, page, resolved, artifact_id, outcome)
        return False

    def _ask_with_retry(self, page: RenderedPage, objective: str) -> ParsedVisionOutput:
        correction: Optional[str] = None
        last_error: Optional[VisionOutputInvalidError] = None

        for attempt in range(self._max_retries + 1):
            response = self._client.generate(
                page.png_bytes, build_prompt(objective, correction)
            )
            try:
                return parse_vision_output(response.text, box_scale=response.box_scale)
            except VisionOutputInvalidError as exc:
                last_error = exc
                correction = str(exc)
                logger.warning(
                    "vision output invalid (attempt %d): %s", attempt + 1, exc
                )

        assert last_error is not None
        raise last_error

    def _emit(
        self,
        parsed: ParsedVisionOutput,
        page: RenderedPage,
        resolved: ResolvedResource,
        artifact_id: str,
        outcome: ExtractionOutcome,
    ) -> None:
        for sequence, observation in enumerate(parsed.observations):
            confidence = None
            if (
                self._accept_model_confidence
                and observation.self_reported_confidence is not None
            ):
                confidence = Confidence(
                    value=observation.self_reported_confidence,
                    source=ConfidenceSource.VISION_MODEL,
                    interpretation=SELF_REPORTED_NOTE,
                )

            outcome.fragments.append(
                ExtractedFragment(
                    # "v" keeps ids distinct from OCR fragments on the same page
                    fragment_id=(
                        f"ev_{(outcome.document_hash or '')[:8]}"
                        f"_p{page.page_index}_v{sequence:04d}"
                    ),
                    kind=FragmentKind.VISUAL_OBSERVATION,
                    content=observation.text,
                    provenance=PageProvenance(
                        resource_id=resolved.resource_id,
                        document_hash=outcome.document_hash or "",
                        page_index=page.page_index,
                        artifact_id=artifact_id,
                        render_dpi=page.dpi,
                    ),
                    region=observation.region,
                    confidence=confidence,
                    category=observation.category,
                    extractor=outcome.extractor or "unknown",
                )
            )
