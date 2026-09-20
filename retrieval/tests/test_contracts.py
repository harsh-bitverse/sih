"""Unit tests for Retrieval Engine data contracts."""

import pytest
from pydantic import ValidationError
from contracts import (
    RequestContext,
    LocationReference,
    Provenance,
    ResourceType,
    RetrievalStatus,
    RetrievedResource,
    RetrievalRequest,
    RetrievalResult,
)


def test_request_context_creation():
    """Verify RequestContext creation and origin tracking."""
    ctx = RequestContext(
        request_id="req-001",
        task_id="task-mrpl-e204",
        user_id="engineer-sagun",
        step_id="step_2",
        source_component="workflow_engine",
        target_component="retrieval_engine",
    )
    assert ctx.request_id == "req-001"
    assert ctx.source_component == "workflow_engine"
    assert ctx.target_component == "retrieval_engine"
    assert ctx.timestamp is not None


def test_request_context_forbids_extra_fields():
    """Ensure strict contract boundary - no undocumented fields allowed."""
    with pytest.raises(ValidationError):
        RequestContext(
            request_id="req-001",
            task_id="task-01",
            user_id="user-1",
            source_component="workflow_engine",
            undocumented_hack="forbidden",  # Should raise ValidationError
        )


def test_retrieval_request_validation():
    """Verify RetrievalRequest parses valid inputs from Planner/Workflow."""
    req = RetrievalRequest(
        request_context=RequestContext(
            request_id="req-101",
            task_id="task-inspection",
            user_id="sagun",
            source_component="planner",
            target_component="retrieval_engine",
        ),
        query="Current SOP requirements for corrosion inspection of E-204",
        source_scope="MRPL safety documentation",
        version_policy="current_only",
        modality_filter=[ResourceType.PDF_PAGE, ResourceType.TABLE],
        max_results=3,
        required_information="Relevant requirements and source references",
    )
    assert req.query.startswith("Current SOP")
    assert req.version_policy == "current_only"
    assert len(req.modality_filter) == 2


def test_retrieval_result_with_multimodal_evidence():
    """Verify RetrievalResult can package text, table, and image evidence for Multimodal."""
    resource = RetrievedResource(
        evidence_id="ev-e204-p14",
        document_id="DOC-INSP-E204-2024",
        document_version="v2.1",
        resource_type=ResourceType.IMAGE,
        content="Corrosion pit detected on shell nozzle weld seam",
        location=LocationReference(
            file_path="simulated_mrpl/photos/e204_corrosion.png",
            page_number=14,
            bounding_box=[100.0, 150.0, 400.0, 550.0],
        ),
        metadata={"equipment_id": "E-204", "defect_type": "pitting"},
        relevance_score=0.96,
        provenance=Provenance(
            document_id="DOC-INSP-E204-2024",
            document_version="v2.1",
            document_title="Heat Exchanger E-204 Annual Inspection",
            author_department="Inspection & Integrity",
            effective_date="2024-05-12",
        ),
    )

    result = RetrievalResult(
        request_context=RequestContext(
            request_id="req-101",
            task_id="task-inspection",
            user_id="sagun",
            step_id="step_2",
            source_component="retrieval_engine",     # Shows it came from us
            target_component="multimodal_engine",   # Headed to multimodal
        ),
        status=RetrievalStatus.SUCCESS,
        results=[resource],
        errors=[],
    )

    # Test round-trip JSON serialization
    json_data = result.model_dump_json()
    assert "retrieval_engine" in json_data
    assert "multimodal_engine" in json_data
    assert "DOC-INSP-E204-2024" in json_data

    # Reconstruct from JSON
    restored = RetrievalResult.model_validate_json(json_data)
    assert restored.results[0].location.bounding_box == [100.0, 150.0, 400.0, 550.0]
    assert restored.results[0].relevance_score == 0.96
