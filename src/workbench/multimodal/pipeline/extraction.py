"""
The OCR extraction pipeline.

Owned by: Developer 4 (Multimodal Engineer)

    ResourceReference
        -> resolver (SECURITY BOUNDARY)   -> bytes + identity
        -> render page                    -> PNG
        -> artifact store                 -> art_<hash>
        -> OCR backend                    -> words
        -> ExtractedFragment              -> region on that artifact

Depends only on ports. Concrete backends and stores are injected, so the same
pipeline runs against real Tesseract or a test double with no branching.
"""

import hashlib
import logging
from typing import Iterable, List, Optional

from workbench.core.types import ConfidenceSource, ResourceReference
from workbench.multimodal.errors import (
    MultimodalError,
    ResourceAccessDeniedError,
    ResourceResolutionError,
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
    Region,
)
from workbench.multimodal.pipeline.page_render import (
    DEFAULT_DPI,
    RenderedPage,
    load_single_image,
    render_pdf_pages,
)
from workbench.multimodal.ports.artifact_store import ArtifactStore
from workbench.multimodal.ports.ocr_backend import OcrBackend, OcrWord
from workbench.multimodal.ports.resource_resolver import (
    ResolvedResource,
    ResourceResolver,
)

logger = logging.getLogger(__name__)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _region_for(words: List[OcrWord], width_px: int, height_px: int) -> Region:
    """Pixel boxes (top-left origin) -> one normalised region covering them."""
    left = min(word.box.left for word in words)
    top = min(word.box.top for word in words)
    right = max(word.box.left + word.box.width for word in words)
    bottom = max(word.box.top + word.box.height for word in words)
    return Region(
        x0=_clamp(left / width_px),
        y0=_clamp(top / height_px),
        x1=_clamp(right / width_px),
        y1=_clamp(bottom / height_px),
    )


def _group_into_lines(words: List[OcrWord]) -> List[List[OcrWord]]:
    """Group by the backend's own line id, preserving reading order."""
    lines: List[List[OcrWord]] = []
    current: Optional[str] = None
    for word in words:
        if word.line_id != current:
            lines.append([])
            current = word.line_id
        lines[-1].append(word)
    return lines


def _line_confidence(words: List[OcrWord]) -> Optional[Confidence]:
    scores = [w.confidence for w in words if w.confidence is not None]
    if not scores:
        return None
    return Confidence(
        value=sum(scores) / len(scores),
        source=ConfidenceSource.OCR_ENGINE,
        interpretation="mean of per-word engine-measured confidence",
    )


class OcrExtractionPipeline:
    def __init__(
        self,
        backend: OcrBackend,
        resolver: ResourceResolver,
        artifact_store: ArtifactStore,
        dpi: int = DEFAULT_DPI,
        min_line_confidence: float = 0.0,
    ) -> None:
        self._backend = backend
        self._resolver = resolver
        self._artifacts = artifact_store
        self._dpi = dpi
        self._min_line_confidence = min_line_confidence

    def run(
        self,
        resource: ResourceReference,
        max_pages: Optional[int] = None,
    ) -> ExtractionOutcome:
        outcome = ExtractionOutcome(resource_id=resource.resource_id)

        try:
            outcome.extractor = self._backend.name
        except MultimodalError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=str(exc),
                    resource_id=resource.resource_id,
                )
            )
            return outcome

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
            pages = self._pages_for(resolved, max_pages)
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
            self._process_page(page, resolved, outcome)

        if outcome.page_count == 0:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.RENDERING,
                    message="Document contained no pages",
                    resource_id=resource.resource_id,
                )
            )

        logger.info(
            "extraction resource=%s pages=%d fragments=%d issues=%d",
            resource.resource_id, outcome.page_count,
            len(outcome.fragments), len(outcome.issues),
        )
        return outcome

    # -- internals ---------------------------------------------------------

    def _pages_for(
        self, resolved: ResolvedResource, max_pages: Optional[int]
    ) -> Iterable[RenderedPage]:
        if resolved.is_image:
            return [load_single_image(resolved.content)]
        if resolved.is_pdf:
            return render_pdf_pages(
                resolved.content, dpi=self._dpi, max_pages=max_pages
            )
        # Unknown suffix: try PDF first, fall back to image, rather than
        # refusing a file whose extension is merely missing or wrong.
        try:
            return list(
                render_pdf_pages(resolved.content, dpi=self._dpi, max_pages=max_pages)
            )
        except MultimodalError:
            return [load_single_image(resolved.content)]

    def _process_page(
        self,
        page: RenderedPage,
        resolved: ResolvedResource,
        outcome: ExtractionOutcome,
    ) -> None:
        if page.has_text_layer:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=(
                        "Page has a native text layer; OCR is a lossy "
                        "substitute. Routing belongs in the page classifier."
                    ),
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )

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
            return

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
            words = self._backend.recognize(page.image)
        except MultimodalError as exc:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=f"OCR backend unavailable: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return
        except Exception as exc:
            # A backend misbehaving on one page must not lose the other pages.
            logger.exception("OCR failed on page %d", page.page_index)
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=f"OCR failed: {exc}",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return

        if not words:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message="No text recognised on page",
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
            return

        self._emit_fragments(words, page, resolved, artifact_id, outcome)

    def _emit_fragments(
        self,
        words: List[OcrWord],
        page: RenderedPage,
        resolved: ResolvedResource,
        artifact_id: str,
        outcome: ExtractionOutcome,
    ) -> None:
        kept = 0
        for sequence, line_words in enumerate(_group_into_lines(words)):
            confidence = _line_confidence(line_words)
            if confidence is not None and confidence.value < self._min_line_confidence:
                continue

            outcome.fragments.append(
                ExtractedFragment(
                    fragment_id=(
                        f"ev_{(outcome.document_hash or '')[:8]}"
                        f"_p{page.page_index}_{sequence:04d}"
                    ),
                    kind=FragmentKind.TEXT_LINE,
                    content=" ".join(word.text for word in line_words),
                    provenance=PageProvenance(
                        resource_id=resolved.resource_id,
                        document_hash=outcome.document_hash or "",
                        page_index=page.page_index,
                        artifact_id=artifact_id,
                        render_dpi=page.dpi,
                    ),
                    region=_region_for(line_words, page.width_px, page.height_px),
                    confidence=confidence,
                    extractor=outcome.extractor or "unknown",
                )
            )
            kept += 1

        if kept == 0:
            outcome.issues.append(
                ProcessingIssue(
                    stage=ErrorStage.EXTRACTION,
                    message=(
                        "All lines fell below the confidence threshold "
                        f"{self._min_line_confidence}"
                    ),
                    resource_id=resolved.resource_id,
                    page_index=page.page_index,
                )
            )
