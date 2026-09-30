"""
Unit & Integration Tests for Final Deliverable & Human Approval UI Component.

Owned by: Developer 1 (System Architect)
"""

import copy
import pytest

from workbench.approval.manager import ApprovalManager
from workbench.approval.schemas import ApprovalRequest, ApprovalStatus
from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.planner.planner import Planner
from workbench.planner.schemas import TaskRequest
from workbench.synthesis.reporting import ReportGenerator
from workbench.synthesis.synthesizer import FinalSynthesizer
from workbench.ui.deliverable_approval_ui import DeliverableApprovalUI
from workbench.ui.projection import ApprovalProjection, DeliverableProjection
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowState, WorkflowStatus
from workbench.workflow.validation import StepValidator


def create_context(task_id: str = "task-ui-appr-001") -> RequestContext:
    return RequestContext(
        request_id="req-ui-appr-001",
        task_id=task_id,
        user_id="reviewer_lead",
        source_component="test",
    )


def create_sample_artifact(task_id: str = "task-ui-appr-001") -> Artifact:
    return Artifact(
        artifact_id=f"art-final-{task_id}",
        task_id=task_id,
        type=ArtifactType.REPORT,
        name=f"final_proposal_{task_id}.pdf",
        location=f"outputs/final_proposal_{task_id}.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
        source_information={"synthesized_text": "Corrective proposal text"},
        metadata={"author": "engineer_lead"},
    )


def test_proposed_deliverable_renders_correctly():
    """
    TEST 1: Proposed deliverable renders correctly in PROPOSED state.
    """
    ctx = create_context("task-p1")
    art = create_sample_artifact("task-p1")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_full_view(req)

    assert view["deliverable_view"]["name"] == "final_proposal_task-p1.pdf"
    assert view["approval_view"]["status"] == "PROPOSED"
    assert view["approval_view"]["can_decide"] is True
    assert len(view["approval_view"]["available_actions"]) == 2


def test_approved_deliverable_renders_correctly():
    """
    TEST 2: Approved deliverable renders correctly with decision details.
    """
    ctx = create_context("task-p2")
    art = create_sample_artifact("task-p2")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.approve_deliverable(req.approval_id, reviewer_id="chief_eng", comment="LGTM")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_full_view(req)

    assert view["approval_view"]["status"] == "APPROVED"
    assert view["approval_view"]["reviewer_id"] == "chief_eng"
    assert view["approval_view"]["comment"] == "LGTM"
    assert view["approval_view"]["decided_at"] is not None


def test_rejected_deliverable_renders_correctly():
    """
    TEST 3: Rejected deliverable renders correctly with rejection details.
    """
    ctx = create_context("task-p3")
    art = create_sample_artifact("task-p3")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.reject_deliverable(req.approval_id, reviewer_id="safety_lead", comment="Incomplete checklist")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_full_view(req)

    assert view["approval_view"]["status"] == "REJECTED"
    assert view["approval_view"]["reviewer_id"] == "safety_lead"
    assert view["approval_view"]["comment"] == "Incomplete checklist"
    assert view["approval_view"]["decided_at"] is not None


def test_approve_reject_controls_only_appear_for_proposed():
    """
    TEST 4: Approve/Reject controls only appear when status is PROPOSED.
    """
    ctx = create_context("task-p4")
    art = create_sample_artifact("task-p4")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    ui = DeliverableApprovalUI(approval_manager=manager)
    view_proposed = ui.render_approval_view(req)
    assert len(view_proposed["available_actions"]) == 2

    manager.approve_deliverable(req.approval_id, reviewer_id="user-1")
    view_approved = ui.render_approval_view(req)
    assert len(view_approved["available_actions"]) == 0


def test_reviewer_information_shown_after_decision():
    """
    TEST 5: Reviewer identity is shown after decision.
    """
    ctx = create_context("task-p5")
    art = create_sample_artifact("task-p5")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.approve_deliverable(req.approval_id, reviewer_id="inspector_99")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_approval_view(req)

    assert view["reviewer_id"] == "inspector_99"


def test_timestamp_shown_after_decision():
    """
    TEST 6: Timestamp is shown after decision.
    """
    ctx = create_context("task-p6")
    art = create_sample_artifact("task-p6")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.reject_deliverable(req.approval_id, reviewer_id="inspector_99")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_approval_view(req)

    assert view["decided_at"] is not None
    assert len(view["decided_at"]) > 0


def test_rejection_comment_shown():
    """
    TEST 7: Rejection comment/reason is shown.
    """
    ctx = create_context("task-p7")
    art = create_sample_artifact("task-p7")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.reject_deliverable(req.approval_id, reviewer_id="inspector_99", comment="Missing pressure calculations.")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_approval_view(req)

    assert view["comment"] == "Missing pressure calculations."


def test_consequential_action_messaging_reflects_approval_status():
    """
    TEST 8: Consequential action message reflects status for PROPOSED, APPROVED, REJECTED.
    """
    ctx = create_context("task-p8")
    art = create_sample_artifact("task-p8")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    ui = DeliverableApprovalUI(approval_manager=manager)

    # PROPOSED
    view_prop = ui.render_approval_view(req)
    assert "blocked until approval" in view_prop["consequential_action_boundary_message"]

    # APPROVED
    manager.approve_deliverable(req.approval_id, reviewer_id="user-1")
    view_appr = ui.render_approval_view(req)
    assert "permitted by the approval boundary" in view_appr["consequential_action_boundary_message"]

    # REJECTED (fresh request)
    ctx2 = create_context("task-p8b")
    art2 = create_sample_artifact("task-p8b")
    req2 = manager.create_approval_request(art2, ctx2)
    manager.reject_deliverable(req2.approval_id, reviewer_id="user-2")
    view_rej = ui.render_approval_view(req2)
    assert "remains blocked" in view_rej["consequential_action_boundary_message"]


def test_approve_action_delegates_to_approval_manager():
    """
    TEST 9: Approve action delegates to ApprovalManager.approve_deliverable.
    """
    ctx = create_context("task-p9")
    art = create_sample_artifact("task-p9")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    ui = DeliverableApprovalUI(approval_manager=manager)
    updated_view = ui.handle_approve_action(req.approval_id, reviewer_id="plant_manager", comment="Approved!")

    assert updated_view["approval_view"]["status"] == "APPROVED"
    assert updated_view["approval_view"]["reviewer_id"] == "plant_manager"
    assert manager.get_approval_request(req.approval_id).status == ApprovalStatus.APPROVED


def test_reject_action_delegates_to_approval_manager():
    """
    TEST 10: Reject action delegates to ApprovalManager.reject_deliverable.
    """
    ctx = create_context("task-p10")
    art = create_sample_artifact("task-p10")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    ui = DeliverableApprovalUI(approval_manager=manager)
    updated_view = ui.handle_reject_action(req.approval_id, reviewer_id="auditor_01", comment="Failed audit.")

    assert updated_view["approval_view"]["status"] == "REJECTED"
    assert updated_view["approval_view"]["comment"] == "Failed audit."
    assert manager.get_approval_request(req.approval_id).status == ApprovalStatus.REJECTED


def test_ui_does_not_mutate_approval_request_directly():
    """
    TEST 11: UI render methods do NOT mutate ApprovalRequest directly.
    """
    ctx = create_context("task-p11")
    art = create_sample_artifact("task-p11")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)

    req_before = copy.deepcopy(req.model_dump())
    ui = DeliverableApprovalUI(approval_manager=manager)
    _ = ui.render_full_view(req)

    assert req.model_dump() == req_before


def test_terminal_approval_cannot_expose_active_decision_controls():
    """
    TEST 12: Terminal APPROVED status does not expose active decision controls.
    """
    ctx = create_context("task-p12")
    art = create_sample_artifact("task-p12")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.approve_deliverable(req.approval_id, reviewer_id="user-1")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_approval_view(req)

    assert view["can_decide"] is False
    assert view["available_actions"] == []


def test_terminal_rejection_cannot_expose_active_decision_controls():
    """
    TEST 13: Terminal REJECTED status does not expose active decision controls.
    """
    ctx = create_context("task-p13")
    art = create_sample_artifact("task-p13")
    manager = ApprovalManager()
    req = manager.create_approval_request(art, ctx)
    manager.reject_deliverable(req.approval_id, reviewer_id="user-1")

    ui = DeliverableApprovalUI(approval_manager=manager)
    view = ui.render_approval_view(req)

    assert view["can_decide"] is False
    assert view["available_actions"] == []


class MockModelRegistry(ModelRegistry):
    def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.SUCCESS,
            metadata={"mock": True},
        )


def test_full_pipeline_to_deliverable_approval_ui():
    """
    TEST 14 FULL PIPELINE:
    TaskRequest → Planner → Workflow → Synthesis → Reporting → ApprovalRequest(PROPOSED)
    → Deliverable/Approval UI → explicit APPROVE / REJECT → UI reflects status.
    """
    planner = Planner()
    ctx = create_context("task-full-ui-appr")
    request = TaskRequest(
        request_context=ctx,
        user_input="Analyze equipment inspection report.",
        requested_output_info={"format": "pdf"},
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

    # Final Synthesis & Reporting
    synthesizer = FinalSynthesizer(model_registry=mock_registry)
    synth_res = synthesizer.synthesize_deliverable(request, state)

    reporter = ReportGenerator()
    deliverable_art = reporter.generate_report(synth_res)

    # Create Approval Request in ApprovalManager
    manager = ApprovalManager()
    appr_req = manager.create_approval_request(deliverable_art, ctx)

    # UI Rendering of PROPOSED deliverable
    ui = DeliverableApprovalUI(approval_manager=manager)
    view_initial = ui.render_full_view(appr_req)

    assert view_initial["approval_view"]["status"] == "PROPOSED"
    assert view_initial["approval_view"]["can_decide"] is True
    assert len(view_initial["approval_view"]["available_actions"]) == 2

    # User clicks APPROVE in UI
    view_after_approve = ui.handle_approve_action(
        approval_id=appr_req.approval_id,
        reviewer_id="chief_plant_engineer",
        comment="Proposal verified and approved.",
    )

    assert view_after_approve["approval_view"]["status"] == "APPROVED"
    assert view_after_approve["approval_view"]["reviewer_id"] == "chief_plant_engineer"
    assert view_after_approve["approval_view"]["can_decide"] is False
    assert view_after_approve["approval_view"]["available_actions"] == []
    assert "permitted by the approval boundary" in view_after_approve["approval_view"]["consequential_action_boundary_message"]
