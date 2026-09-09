"""
Boundary translation: internal extraction model -> core contract objects.

Owned by: Developer 4 (Multimodal Engineer)

The ONLY module that touches both models. When core contracts change, this
file changes and the pipeline does not.

Two decisions worth knowing about, both flagged to the System Architect:

1. core.Evidence.location is a free-text string, so the structured region
   also goes into provenance["region"]. A UI that wants to highlight the
   region needs the numbers, not a string to re-parse.

2. No aggregate confidence is produced anywhere. Averaging OCR_ENGINE values
   with VISION_MODEL values would yield a number that looks meaningful and
   is not. Per-fragment confidence, each carrying its own source, is the
   real signal.
"""

from typing import Any, Dict, List, Optional

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.types import Evidence
from workbench.multimodal.pipeline.internal_model import (
    ExtractedFragment,
    ExtractionOutcome,
    PageArtifact,
)

SUBSYSTEM_NAME = "multimodal"


def fragment_to_evidence(fragment: ExtractedFragment) -> Evidence:
    provenance: Dict[str, Any] = {
        "subsystem": SUBSYSTEM_NAME,
        "resource_id": fragment.provenance.resource_id,
        "document_hash": fragment.provenance.document_hash,
        "page_index": fragment.provenance.page_index,
        "artifact_id": fragment.provenance.artifact_id,
        "extractor": fragment.extractor,
    }
    if fragment.provenance.render_dpi is not None:
        provenance["render_dpi"] = fragment.provenance.render_dpi
    if fragment.region is not None:
        # Structured, so consumers need not parse the location string.
        provenance["region"] = fragment.region.model_dump()
        provenance["region_space"] = "normalized_0_1_origin_top_left"
    if fragment.confidence is not None and fragment.confidence.interpretation:
        provenance["confidence_interpretation"] = fragment.confidence.interpretation

    location = f"page={fragment.provenance.page_index}"
    if fragment.region is not None:
        location = f"{location}; {fragment.region.as_location()}"

    return Evidence(
        evidence_id=fragment.fragment_id,
        source_artifact=fragment.provenance.artifact_id,
        content=fragment.content,
        location=location,
        evidence_type=fragment.kind.value,
        provenance=provenance,
        confidence=fragment.confidence.value if fragment.confidence else None,
        confidence_source=fragment.confidence.source if fragment.confidence else None,
    )


def page_artifact_to_artifact(
    page_artifact: PageArtifact,
    context: RequestContext,
    location: str,
) -> Artifact:
    name = (
        f"{page_artifact.source_filename or page_artifact.resource_id}"
        f"_page_{page_artifact.page_index}.png"
    )
    return Artifact(
        artifact_id=page_artifact.artifact_id,
        task_id=context.task_id,
        step_id=context.step_id,
        type=ArtifactType.IMAGE,
        name=name,
        location=location,
        mime_type=page_artifact.media_type,
        created_by=SUBSYSTEM_NAME,
        source_information={
            "resource_id": page_artifact.resource_id,
            "page_index": page_artifact.page_index,
            "render_dpi": page_artifact.render_dpi,
            "content_hash": page_artifact.content_hash,
        },
        metadata={
            "width_px": page_artifact.width_px,
            "height_px": page_artifact.height_px,
        },
    )


def outcome_to_evidence(outcome: ExtractionOutcome) -> List[Evidence]:
    return [fragment_to_evidence(fragment) for fragment in outcome.fragments]


def outcome_to_errors(outcome: ExtractionOutcome) -> List[str]:
    """core contract takes List[str]; structure is flattened only here."""
    return [issue.as_text() for issue in outcome.issues]


def outcome_metadata(
    outcome: ExtractionOutcome, extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "subsystem": SUBSYSTEM_NAME,
        "internal_model_version": outcome.model_version,
        "extractor": outcome.extractor,
        "page_count": outcome.page_count,
        "fragment_count": len(outcome.fragments),
        "document_hash": outcome.document_hash,
        "extracted_at": outcome.extracted_at.isoformat(),
    }
    if extra:
        metadata.update(extra)
    return metadata
