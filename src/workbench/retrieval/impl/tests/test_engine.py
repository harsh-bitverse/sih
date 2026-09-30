"""Unit and integration tests for KnowledgeRetrievalEngine."""

import pytest
from contracts import (
    RequestContext,
    ResourceType,
    RetrievalRequest,
    RetrievalStatus,
)
from engine import KnowledgeRetrievalEngine


@pytest.fixture
def engine():
    """Provides an initialized retrieval engine instance."""
    return KnowledgeRetrievalEngine()


def test_version_policy_rejects_superseded_sops(engine):
    """CRITICAL SAFETY TEST: Verify engine rejects superseded v1.0 and returns active v3.2."""
    req = RetrievalRequest(
        request_context=RequestContext(
            request_id="req-v-test",
            task_id="task-mrpl-flange-safety",
            user_id="lead-engineer",
            step_id="step_2",
            source_component="planner",
            target_component="retrieval_engine",
        ),
        query="Current SOP torque requirements for Heat Exchanger E-204 flange bolts",
        source_scope="MRPL safety documentation",
        version_policy="current_only",  # Demand only active versions
        required_information="Bolt torque value in Nm",
    )

    result = engine.execute_retrieval(req)

    assert result.status == RetrievalStatus.SUCCESS
    assert len(result.results) > 0

    # Ensure SOP-CRU-401 is returned as v3.2 and NEVER as superseded v1.0
    sop_results = [r for r in result.results if r.document_id == "DOC-SOP-CRU-401"]
    assert len(sop_results) > 0, "Active SOP v3.2 was not found in results!"
    for sop in sop_results:
        assert sop.document_version == "v3.2"
        assert sop.document_version != "v1.0", "SECURITY VIOLATION: Superseded v1.0 was returned!"
        assert "300 Nm" in sop.content or "300" in sop.content

    # Ensure no superseded document of ANY type was returned
    for item in result.results:
        assert item.evidence_id != "ev-sop401-v1-sec3", "SECURITY VIOLATION: Superseded evidence was returned!"

    # Ensure source and target component envelopes are properly stamped
    assert result.request_context.source_component == "retrieval_engine"
    assert result.request_context.target_component == "multimodal_engine"



def test_noise_rejection_discards_weak_matches(engine):
    """PRECISION TEST: Query with 1-2 random words is discarded and not returned as noise."""
    req = RetrievalRequest(
        request_context=RequestContext(
            request_id="req-noise-test",
            task_id="task-unrelated",
            user_id="inspector-1",
            step_id="step_1",
            source_component="workflow_engine",
            target_component="retrieval_engine",
        ),
        query="Where is the lunch cafeteria and printer paper?",
        source_scope="MRPL general",
        version_policy="current_only",
        required_information="Cafeteria location",
    )

    result = engine.execute_retrieval(req)

    # Must be NO_DATA with 0 results returned
    assert result.status == RetrievalStatus.NO_DATA
    assert len(result.results) == 0


def test_modality_filtering_for_multimodal_vision(engine):
    """VISION TEST: Requesting only IMAGE returns only visual assets with bounding boxes."""
    req = RetrievalRequest(
        request_context=RequestContext(
            request_id="req-vision-01",
            task_id="task-defect-analysis",
            user_id="corrosion-specialist",
            step_id="step_2",
            source_component="planner",
            target_component="multimodal_engine",
        ),
        query="Corrosion inspection photograph of E-204 flange nozzle",
        source_scope="MRPL inspection reports",
        version_policy="current_only",
        modality_filter=[ResourceType.IMAGE],  # ONLY IMAGES
        required_information="Visual evidence of flange defect",
    )

    result = engine.execute_retrieval(req)

    assert result.status == RetrievalStatus.SUCCESS
    assert len(result.results) >= 1

    # Every item must be an IMAGE
    for item in result.results:
        assert item.resource_type == ResourceType.IMAGE
        assert item.location.bounding_box is not None
        assert "photo" in item.location.file_path.lower() or "png" in item.location.file_path.lower()


def test_equipment_tag_isolation(engine):
    """EQUIPMENT TEST: Querying for pump P-101A does not pollute results with E-204 heat exchanger."""
    req = RetrievalRequest(
        request_context=RequestContext(
            request_id="req-pump-01",
            task_id="task-p101a-service",
            user_id="reliability-eng",
            step_id="step_2",
            source_component="planner",
            target_component="retrieval_engine",
        ),
        query="What is the seal plan and vibration limit for crude pump P-101A?",
        source_scope="MRPL mechanical manuals",
        version_policy="current_only",
        required_information="API seal plan and vibration limit",
    )

    result = engine.execute_retrieval(req)

    assert result.status == RetrievalStatus.SUCCESS
    assert len(result.results) >= 1

    top_item = result.results[0]
    assert top_item.metadata["equipment_id"] == "P-101A"
    assert "Plan 53B" in top_item.content
    assert "3.5 mm/s" in top_item.content


def test_search_convenience_helper(engine):
    """CONVENIENCE TEST: Verify that engine.search() works in 1 line with auto-enveloping."""
    result = engine.search("E-204 torque requirements")
    assert result.status == RetrievalStatus.SUCCESS
    assert len(result.results) >= 1
    assert result.request_context.source_component == "retrieval_engine"
    assert result.request_context.target_component == "multimodal_engine"


def test_universal_package_import():
    """IMPORT TEST: Verify that top-level retrieval package exports all essential symbols."""
    import retrieval
    assert hasattr(retrieval, "KnowledgeRetrievalEngine")
    assert hasattr(retrieval, "RetrievalRequest")
    assert hasattr(retrieval, "RetrievalResult")
    assert hasattr(retrieval, "RequestContext")
    assert hasattr(retrieval, "SimulatedMRPLDatabase")
    assert hasattr(retrieval, "IndustrialDocumentChunker")

