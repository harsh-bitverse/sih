"""
End-to-End Integration Tests for SIH Workbench Demo Composition.

Owned by: Developer 1 (System Architect)
Subsystem: demo

Validates the complete demo composition flow, synthetic MRPL E-204 data loader,
full execution path through human approval (both APPROVE and REJECT outcomes),
and strict consequential action security boundary enforcement.
"""

import pytest

from workbench.approval.schemas import ApprovalStatus
from workbench.core.errors import SecurityViolationError
from workbench.demo.composition import DemoComposition
from workbench.demo.data import (
    E204_TASK_PROMPT,
    create_mrpl_e204_resources,
    create_mrpl_e204_task_request,
)
from workbench.workflow.state import WorkflowStatus


def test_demo_composition_initialization():
    """
    Verifies that DemoComposition wires all subsystems and UI components without error.
    """
    comp = DemoComposition()
    assert comp.planner is not None
    assert comp.engine is not None
    assert comp.synthesizer is not None
    assert comp.reporter is not None
    assert comp.approval_manager is not None
    assert comp.task_intake_ui is not None
    assert comp.execution_dashboard is not None
    assert comp.evidence_artifact_viewer is not None
    assert comp.deliverable_approval_ui is not None


def test_mrpl_e204_data_creation():
    """
    Verifies synthetic MRPL Equipment E-204 resources and TaskRequest structure.
    """
    resources = create_mrpl_e204_resources()
    assert len(resources) == 4
    res_ids = {r.resource_id for r in resources}
    assert "res-e204-inspection-report" in res_ids
    assert "res-e204-casing-photo" in res_ids
    assert "res-e204-safety-sop" in res_ids
    assert "res-e204-incident-17" in res_ids

    task_req = create_mrpl_e204_task_request(task_id="task-test-e204", user_id="test_user")
    assert task_req.request_context.task_id == "task-test-e204"
    assert task_req.request_context.user_id == "test_user"
    assert task_req.user_input == E204_TASK_PROMPT
    assert len(task_req.resources) == 4


def test_full_demo_approval_path():
    """
    Verifies end-to-end demo execution for the explicit APPROVAL path:
    Task Intake -> Planner -> WorkflowEngine (6 steps) -> Synthesis -> Reporting
    -> PROPOSED -> Consequential Action BLOCKED -> APPROVE -> Consequential Action EXECUTED.
    """
    comp = DemoComposition()
    result = comp.run_full_pipeline_approval_path(
        reviewer_id="chief_engineer_01",
        comment="Approved for immediate plant maintenance.",
    )

    assert result["state"].status == WorkflowStatus.COMPLETED
    assert len(result["plan"].executable_steps) == 6
    assert result["deliverable"].artifact_id.startswith("art-final-report-")
    assert result["approval_request"].status == ApprovalStatus.APPROVED
    assert result["approval_request"].reviewer_id == "chief_engineer_01"
    assert result["blocked_before_approval"] is True
    assert result["action_result"]["status"] == "EXECUTED"
    assert result["action_result"]["action_name"] == "dispatch_work_order"

    # Verify UI projections
    assert result["dashboard_view"]["summary"]["completed_steps"] == 6
    assert result["evidence_view"]["summary"]["total_evidence_items"] > 0
    assert result["approval_ui_view"]["approval_view"]["status"] == "APPROVED"


def test_full_demo_rejection_path():
    """
    Verifies end-to-end demo execution for the explicit REJECTION path:
    Task Intake -> Planner -> WorkflowEngine -> Synthesis -> Reporting
    -> PROPOSED -> REJECT -> Consequential Action BLOCKED.
    """
    comp = DemoComposition()
    result = comp.run_full_pipeline_rejection_path(
        reviewer_id="safety_inspector_02",
        comment="Further non-destructive testing required.",
    )

    assert result["state"].status == WorkflowStatus.COMPLETED
    assert result["approval_request"].status == ApprovalStatus.REJECTED
    assert result["approval_request"].reviewer_id == "safety_inspector_02"
    assert result["blocked_after_rejection"] is True
    assert result["approval_ui_view"]["approval_view"]["status"] == "REJECTED"


def test_demo_context_correlation_and_audit():
    """
    Verifies request context correlation (task_id, request_id, user_id)
    and audit trail recording across the full demo run.
    """
    comp = DemoComposition()
    result = comp.run_full_pipeline_approval_path()

    task_id = result["task_request"].request_context.task_id
    records = comp.audit_registry.recorded_events
    assert len(records) > 0

    task_records = [r for r in records if r.request_context.task_id == task_id]
    assert len(task_records) > 0

    event_types = {r.event_type for r in task_records}
    assert "workflow_started" in event_types
    assert "step_started" in event_types
    assert "step_completed" in event_types
    assert "model_executed" in event_types
    assert "tool_executed" in event_types
    assert "approval_requested" in event_types
    assert "approval_granted" in event_types
