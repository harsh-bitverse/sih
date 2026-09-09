"""The subsystem honours its own contract. Mocked backend: no binary, no GPU."""

from workbench.core.artifacts import ArtifactType
from workbench.core.types import ConfidenceSource
from workbench.multimodal.processor import DefaultMultimodalProcessor
from workbench.multimodal.schemas import (
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)

from tests.unit.multimodal.conftest import EmptyOcrBackend, ExplodingOcrBackend


def process(backend, resolver, store, context, resource, **params) -> MultimodalResult:
    processor = DefaultMultimodalProcessor(backend, resolver, store, dpi=100)
    return processor.process(
        MultimodalRequest(
            request_context=context,
            resource=resource,
            modalities=["ocr"],
            parameters=params,
        )
    )


def test_returns_a_multimodal_result(backend, resolver, store, context, scanned_resource):
    result = process(backend, resolver, store, context, scanned_resource)
    assert isinstance(result, MultimodalResult)


def test_request_context_is_propagated_unchanged(
    backend, resolver, store, context, scanned_resource
):
    """The audit tree depends on this identity surviving the call."""
    result = process(backend, resolver, store, context, scanned_resource)
    assert result.request_context == context


def test_words_are_grouped_into_lines(backend, resolver, store, context, scanned_resource):
    result = process(backend, resolver, store, context, scanned_resource)
    assert [e.content for e in result.evidence] == ["Surface corrosion", "Flange"]


def test_evidence_ids_are_unique(backend, resolver, store, context, scanned_resource):
    ids = [e.evidence_id for e in process(
        backend, resolver, store, context, scanned_resource).evidence]
    assert len(ids) == len(set(ids))


def test_every_evidence_item_is_independently_traceable(
    backend, resolver, store, context, scanned_resource
):
    """Core requirement: one evidence item alone locates its own source."""
    result = process(backend, resolver, store, context, scanned_resource)
    artifact_ids = {a.artifact_id for a in result.artifacts}

    for item in result.evidence:
        assert item.source_artifact in artifact_ids
        assert item.provenance["page_index"] is not None
        assert item.provenance["document_hash"]
        assert item.provenance["resource_id"] == "res_scanned"
        assert "page=" in item.location


def test_region_is_structured_not_only_a_string(
    backend, resolver, store, context, scanned_resource
):
    """A UI highlighting a region needs numbers, not a string to re-parse."""
    for item in process(backend, resolver, store, context, scanned_resource).evidence:
        region = item.provenance["region"]
        assert 0.0 <= region["x0"] <= region["x1"] <= 1.0
        assert 0.0 <= region["y0"] <= region["y1"] <= 1.0
        assert item.provenance["region_space"] == "normalized_0_1_origin_top_left"


def test_confidence_declares_its_source(
    backend, resolver, store, context, scanned_resource
):
    for item in process(backend, resolver, store, context, scanned_resource).evidence:
        assert item.confidence_source is ConfidenceSource.OCR_ENGINE
        assert 0.0 <= item.confidence <= 1.0


def test_no_aggregate_confidence_is_invented(
    backend, resolver, store, context, scanned_resource
):
    """Averaging across incompatible sources would look meaningful and not be."""
    result = process(backend, resolver, store, context, scanned_resource)
    assert "confidence" not in result.metadata


def test_artifacts_carry_task_identity(
    backend, resolver, store, context, scanned_resource
):
    for artifact in process(
        backend, resolver, store, context, scanned_resource).artifacts:
        assert artifact.task_id == "task-042"
        assert artifact.step_id == "step-2"
        assert artifact.created_by == "multimodal"
        assert artifact.type is ArtifactType.IMAGE
        assert artifact.mime_type == "image/png"


def test_page_images_are_retrievable(
    backend, resolver, store, context, scanned_resource
):
    """Without the stored image, a region points at nothing."""
    result = process(backend, resolver, store, context, scanned_resource)
    for artifact in result.artifacts:
        assert store.exists(artifact.artifact_id)
        assert store.get(artifact.artifact_id).startswith(b"\x89PNG")


def test_artifact_ids_are_deterministic(
    backend, resolver, store, context, scanned_resource
):
    first = process(backend, resolver, store, context, scanned_resource)
    second = process(backend, resolver, store, context, scanned_resource)
    assert [a.artifact_id for a in first.artifacts] == [
        a.artifact_id for a in second.artifacts
    ]


def test_status_success_when_clean(backend, resolver, store, context, scanned_resource):
    result = process(backend, resolver, store, context, scanned_resource)
    assert result.status is MultimodalStatus.SUCCESS
    assert result.errors == []


def test_status_failed_when_no_evidence(resolver, store, context, scanned_resource):
    result = process(EmptyOcrBackend(), resolver, store, context, scanned_resource)
    assert result.status is MultimodalStatus.FAILED
    assert result.errors


def test_backend_failure_is_contained(resolver, store, context, scanned_resource):
    """A crashing backend becomes a FAILED result, never a raised exception."""
    result = process(ExplodingOcrBackend(), resolver, store, context, scanned_resource)
    assert result.status is MultimodalStatus.FAILED
    assert any("OCR failed" in e for e in result.errors)


def test_text_layer_page_yields_partial_with_a_warning(
    backend, resolver, store, context, digital_resource
):
    """Evidence is kept; the caveat is reported rather than swallowed."""
    result = process(backend, resolver, store, context, digital_resource)
    assert result.status is MultimodalStatus.PARTIAL
    assert result.evidence
    assert any("native text layer" in e for e in result.errors)


def test_unsupported_modality_is_reported_not_fatal(
    backend, resolver, store, context, scanned_resource
):
    processor = DefaultMultimodalProcessor(backend, resolver, store, dpi=100)
    result = processor.process(
        MultimodalRequest(
            request_context=context,
            resource=scanned_resource,
            modalities=["ocr", "vision"],
        )
    )
    assert result.evidence
    assert result.metadata["unsupported_modalities"] == ["vision"]


def test_standalone_image_is_handled(
    backend, resolver, store, context, photo_resource
):
    result = process(backend, resolver, store, context, photo_resource)
    assert result.evidence
    assert result.metadata["page_count"] == 1


def test_low_confidence_lines_can_be_dropped(
    backend, resolver, store, context, scanned_resource
):
    result = process(
        backend, resolver, store, context, scanned_resource, min_line_confidence=0.8
    )
    assert [e.content for e in result.evidence] == ["Surface corrosion"]


def test_metadata_reports_execution_facts(
    backend, resolver, store, context, scanned_resource
):
    metadata = process(backend, resolver, store, context, scanned_resource).metadata
    assert metadata["extractor"] == "fake-ocr-1.0"
    assert metadata["page_count"] == 1
    assert metadata["subsystem"] == "multimodal"
    assert metadata["latency_ms"] >= 0


def test_result_is_json_serialisable(
    backend, resolver, store, context, scanned_resource
):
    payload = process(backend, resolver, store, context, scanned_resource
                      ).model_dump_json()
    assert '"OCR_ENGINE"' in payload
