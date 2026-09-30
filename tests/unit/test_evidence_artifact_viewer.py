"""
Unit & Integration Tests for Read-Only Evidence & Artifact Viewer.

Owned by: Developer 1 (System Architect)
"""

import copy
import pytest

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.types import ConfidenceSource, Evidence
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.planner.planner import Planner
from workbench.planner.schemas import TaskRequest
from workbench.ui.evidence_artifact_viewer import (
    ArtifactProjection,
    EvidenceArtifactViewer,
    EvidenceProjection,
)
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowState, WorkflowStatus
from workbench.workflow.validation import StepValidator


def create_context(task_id: str = "task-view-001") -> RequestContext:
    return RequestContext(
        request_id="req-view-001",
        task_id=task_id,
        user_id="viewer_user",
        source_component="test",
    )


def test_evidence_projection():
    """
    TEST 1: EvidenceProjection extracts fields from Evidence correctly.
    """
    ev = Evidence(
        evidence_id="ev-101",
        source_artifact="art-999",
        content="Vibration frequency spikes detected on bearing #3",
        location="page 4, paragraph 2",
        evidence_type="vibration_anomaly",
        provenance={"sensor_id": "vib-301", "calibrated": True},
        confidence=0.92,
        confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
    )

    proj = EvidenceProjection.from_evidence(ev)

    assert proj.evidence_id == "ev-101"
    assert proj.source_artifact == "art-999"
    assert proj.content_preview == "Vibration frequency spikes detected on bearing #3"
    assert proj.location == "page 4, paragraph 2"
    assert proj.evidence_type == "vibration_anomaly"
    assert proj.provenance == {"sensor_id": "vib-301", "calibrated": True}
    assert proj.confidence == 0.92
    assert proj.confidence_source == "SYSTEM_ASSESSMENT"
    assert proj.has_confidence is True
    assert proj.has_provenance is True


def test_artifact_projection():
    """
    TEST 2: ArtifactProjection extracts fields from Artifact correctly.
    """
    art = Artifact(
        artifact_id="art-201",
        task_id="task-001",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="vibration_report.pdf",
        location="outputs/vibration_report.pdf",
        mime_type="application/pdf",
        created_by="analysis_agent",
        source_information={"tool": "pdf_gen", "version": "1.0"},
        metadata={"confidential": True, "author": "eng_lead"},
    )

    proj = ArtifactProjection.from_artifact(art)

    assert proj.artifact_id == "art-201"
    assert proj.task_id == "task-001"
    assert proj.step_id == "step-1"
    assert proj.type == "REPORT"
    assert proj.name == "vibration_report.pdf"
    assert proj.location == "outputs/vibration_report.pdf"
    assert proj.mime_type == "application/pdf"
    assert proj.created_by == "analysis_agent"
    assert proj.source_information == {"tool": "pdf_gen", "version": "1.0"}
    assert proj.metadata == {"confidential": True, "author": "eng_lead"}
    assert proj.has_metadata is True
    assert proj.has_source_info is True


def test_evidence_provenance_visibility():
    """
    TEST 3: Provenance details are visible in EvidenceProjection.
    """
    ev = Evidence(
        evidence_id="ev-102",
        content="Temperature reading 145 C",
        evidence_type="thermal_reading",
        provenance={"sensor": "thermo-4", "zone": "reactor_core"},
    )
    proj = EvidenceProjection.from_evidence(ev)

    assert proj.has_provenance is True
    assert proj.provenance["zone"] == "reactor_core"


def test_evidence_confidence_visibility_when_present():
    """
    TEST 4: Confidence score and confidence_source are visible when present.
    """
    ev = Evidence(
        evidence_id="ev-103",
        content="Crack detected on flange F-12",
        evidence_type="visual_crack",
        confidence=0.98,
        confidence_source=ConfidenceSource.VISION_MODEL,
    )
    proj = EvidenceProjection.from_evidence(ev)

    assert proj.has_confidence is True
    assert proj.confidence == 0.98
    assert proj.confidence_source == "VISION_MODEL"


def test_optional_confidence_absence():
    """
    TEST 5: Evidence with confidence=None and confidence_source=None handles absence gracefully.
    """
    ev = Evidence(
        evidence_id="ev-104",
        content="Manual log entry: valve inspected",
        evidence_type="log_entry",
        confidence=None,
        confidence_source=None,
    )
    proj = EvidenceProjection.from_evidence(ev)

    assert proj.has_confidence is False
    assert proj.confidence is None
    assert proj.confidence_source is None


def test_artifact_metadata_visibility():
    """
    TEST 6: Artifact metadata and source_information are visible.
    """
    art = Artifact(
        artifact_id="art-202",
        task_id="task-002",
        step_id="step-2",
        type=ArtifactType.DATASET,
        name="readings.json",
        location="outputs/readings.json",
        mime_type="application/json",
        created_by="logger",
        source_information={"sensor_count": 8},
        metadata={"units": "celsius"},
    )
    proj = ArtifactProjection.from_artifact(art)

    assert proj.has_metadata is True
    assert proj.has_source_info is True
    assert proj.metadata["units"] == "celsius"
    assert proj.source_information["sensor_count"] == 8


def test_step_level_evidence_association():
    """
    TEST 7: Evidence is associated with its step_id correctly.
    """
    context = create_context("task-step-ev")
    ev1 = Evidence(
        evidence_id="ev-s1",
        content="Finding step 1",
        evidence_type="finding",
    )
    agent_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.SUCCESS,
        result_evidence=[ev1],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_results={"step-1": agent_res},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.step_id == "step-1"
    assert step_proj.evidence_count == 1
    assert step_proj.evidence_list[0].evidence_id == "ev-s1"


def test_step_level_artifact_association():
    """
    TEST 8: Artifacts are associated with their step_id correctly.
    """
    context = create_context("task-step-art")
    art1 = Artifact(
        artifact_id="art-s1",
        task_id=context.task_id,
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="report_s1.pdf",
        location="outputs/report_s1.pdf",
        mime_type="application/pdf",
        created_by="test",
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_artifacts={"step-1": [art1]},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.step_id == "step-1"
    assert step_proj.artifact_count == 1
    assert step_proj.artifacts_list[0].artifact_id == "art-s1"


def test_multiple_evidence_items():
    """
    TEST 9: Multiple evidence items for a single step are projected.
    """
    context = create_context("task-multi-ev")
    ev1 = Evidence(evidence_id="ev-1", content="Finding 1", evidence_type="type_a")
    ev2 = Evidence(evidence_id="ev-2", content="Finding 2", evidence_type="type_b")
    agent_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.SUCCESS,
        result_evidence=[ev1, ev2],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_results={"step-1": agent_res},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.evidence_count == 2
    ev_ids = [e.evidence_id for e in step_proj.evidence_list]
    assert "ev-1" in ev_ids
    assert "ev-2" in ev_ids


def test_multiple_artifacts():
    """
    TEST 10: Multiple artifacts for a single step are projected.
    """
    context = create_context("task-multi-art")
    art1 = Artifact(
        artifact_id="art-1",
        task_id=context.task_id,
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="report.pdf",
        location="outputs/report.pdf",
        mime_type="application/pdf",
        created_by="agent",
    )
    art2 = Artifact(
        artifact_id="art-2",
        task_id=context.task_id,
        step_id="step-1",
        type=ArtifactType.IMAGE,
        name="photo.png",
        location="outputs/photo.png",
        mime_type="image/png",
        created_by="agent",
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_artifacts={"step-1": [art1, art2]},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.artifact_count == 2
    art_ids = [a.artifact_id for a in step_proj.artifacts_list]
    assert "art-1" in art_ids
    assert "art-2" in art_ids


def test_no_evidence_case():
    """
    TEST 11: Step with no evidence returns evidence_count=0 without errors.
    """
    context = create_context("task-no-ev")
    agent_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.SUCCESS,
        result_evidence=[],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_results={"step-1": agent_res},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.evidence_count == 0
    assert step_proj.evidence_list == []


def test_no_artifacts_case():
    """
    TEST 12: Step with no artifacts returns artifact_count=0 without errors.
    """
    context = create_context("task-no-art")
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_artifacts={},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.artifact_count == 0
    assert step_proj.artifacts_list == []


def test_failed_step_evidence_artifact_handling():
    """
    TEST 13: Evidence and artifacts generated before step failure are preserved and viewer indicates is_failed=True.
    """
    context = create_context("task-fail-ev-art")
    ev_early = Evidence(
        evidence_id="ev-early",
        content="Partial finding before error",
        evidence_type="partial_finding",
    )
    art_early = Artifact(
        artifact_id="art-early",
        task_id=context.task_id,
        step_id="step-1",
        type=ArtifactType.DOCUMENT,
        name="draft.txt",
        location="outputs/draft.txt",
        mime_type="text/plain",
        created_by="agent",
    )
    failed_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.FAILED,
        result_evidence=[ev_early],
        artifacts=[art_early],
        errors=["Model execution failed unexpectedly."],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.FAILED,
        step_statuses={"step-1": StepStatus.FAILED},
        step_results={"step-1": failed_res},
        step_artifacts={"step-1": [art_early]},
    )

    viewer = EvidenceArtifactViewer()
    step_proj = viewer.project_step(state, "step-1")

    assert step_proj.is_failed is True
    assert step_proj.evidence_count == 1
    assert step_proj.artifact_count == 1
    assert step_proj.evidence_list[0].evidence_id == "ev-early"
    assert step_proj.artifacts_list[0].artifact_id == "art-early"


def test_viewer_does_not_mutate_source_objects():
    """
    TEST 14: EvidenceArtifactViewer operations do NOT mutate WorkflowState, Evidence, or Artifact.
    """
    context = create_context("task-no-mutate-viewer")
    ev = Evidence(
        evidence_id="ev-orig",
        content="Original evidence text",
        evidence_type="original",
    )
    art = Artifact(
        artifact_id="art-orig",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="orig.pdf",
        location="outputs/orig.pdf",
        mime_type="application/pdf",
        created_by="test",
    )
    agent_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.SUCCESS,
        result_evidence=[ev],
        artifacts=[art],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id="plan-1",
        status=WorkflowStatus.COMPLETED,
        step_statuses={"step-1": StepStatus.PASSED},
        step_results={"step-1": agent_res},
        step_artifacts={"step-1": [art]},
    )

    state_before = copy.deepcopy(state.model_dump())
    ev_before = copy.deepcopy(ev.model_dump())
    art_before = copy.deepcopy(art.model_dump())

    viewer = EvidenceArtifactViewer()
    _ = viewer.render_full_viewer(state)

    assert state.model_dump() == state_before
    assert ev.model_dump() == ev_before
    assert art.model_dump() == art_before


class MockModelRegistry(ModelRegistry):
    def execute(self, request: AgentRequest) -> AgentResult:
        ev = Evidence(
            evidence_id=f"ev-agent-{request.request_context.step_id or '001'}",
            content=f"Evidence for objective: {request.objective}",
            evidence_type="agent_analysis",
            confidence=0.95,
            confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
        )
        art = Artifact(
            artifact_id=f"art-agent-{request.request_context.step_id or '001'}",
            task_id=request.request_context.task_id,
            step_id=request.request_context.step_id,
            type=ArtifactType.REPORT,
            name="agent_output.pdf",
            location="outputs/agent_output.pdf",
            mime_type="application/pdf",
            created_by="mock_model_registry",
        )
        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.SUCCESS,
            result_evidence=[ev],
            artifacts=[art],
        )


def test_full_flow_intake_planner_engine_to_viewer():
    """
    TEST 15 FULL FLOW:
    TaskRequest → Planner → WorkflowEngine → WorkflowState → Evidence/Artifact Viewer
    """
    planner = Planner()
    context = create_context("task-full-viewer-flow")
    request = TaskRequest(
        request_context=context,
        user_input="Analyze inspection report findings and generate proposal.",
        requested_output_info={"format": "docx"},
    )

    plan = planner.create_plan(request)
    mock_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    viewer = EvidenceArtifactViewer()
    rendered = viewer.render_full_viewer(state, plan)

    assert rendered["workflow_status"] == "COMPLETED"
    assert rendered["summary"]["total_evidence_items"] == 6
    assert rendered["summary"]["total_artifacts"] == 6
    assert len(rendered["step_inspections"]) == 6

    step_1_inspection = rendered["step_inspections"][0]
    assert step_1_inspection["evidence_count"] == 1
    assert step_1_inspection["artifact_count"] == 1
    assert step_1_inspection["evidence_list"][0]["confidence"] == 0.95
    assert step_1_inspection["artifacts_list"][0]["name"] == "agent_output.pdf"
