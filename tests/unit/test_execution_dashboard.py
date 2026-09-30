"""
Unit & Integration Tests for Workbench Execution Dashboard.

Owned by: Developer 1 (System Architect)
"""

import copy
import pytest

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.planner.planner import Planner
from workbench.planner.schemas import ExecutionPlan, ExecutionStep, TaskRequest
from workbench.ui.execution_dashboard import ExecutionDashboard
from workbench.ui.projection import WorkflowProjection
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowState, WorkflowStatus
from workbench.workflow.validation import StepValidator


def create_context(task_id: str = "task-dash-001") -> RequestContext:
    return RequestContext(
        request_id="req-dash-001",
        task_id=task_id,
        user_id="dashboard_user",
        source_component="test",
    )


def test_running_workflow_projection():
    """
    TEST 1: Running workflow projection (status == RUNNING).
    """
    context = create_context("task-running")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Analyze pipeline",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="Step 1", expected_output="Out 1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.RUNNING},
    )

    proj = WorkflowProjection.from_state(state, plan)
    assert proj.workflow_status == WorkflowStatus.RUNNING
    assert not proj.is_terminal
    assert proj.steps[0].status == StepStatus.RUNNING


def test_completed_workflow_projection():
    """
    TEST 2: Completed workflow projection (status == COMPLETED).
    """
    context = create_context("task-completed")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Analyze pipeline",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="Step 1", expected_output="Out 1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.COMPLETED,
        step_statuses={"step-1": StepStatus.PASSED},
    )

    proj = WorkflowProjection.from_state(state, plan)
    assert proj.workflow_status == WorkflowStatus.COMPLETED
    assert proj.is_terminal
    assert proj.completed_steps_count == 1


def test_failed_workflow_projection():
    """
    TEST 3: Failed workflow projection (status == FAILED).
    """
    context = create_context("task-failed")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Analyze pipeline",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="Step 1", expected_output="Out 1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.FAILED,
        step_statuses={"step-1": StepStatus.FAILED},
        step_results={"step-1": "Model execution timeout error"},
    )

    proj = WorkflowProjection.from_state(state, plan)
    assert proj.workflow_status == WorkflowStatus.FAILED
    assert proj.is_terminal
    assert proj.has_failure
    assert proj.failed_steps_count == 1


def test_cancelled_workflow_projection():
    """
    TEST 4: Cancelled workflow projection (status == CANCELLED).
    """
    context = create_context("task-cancelled")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Analyze pipeline",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="Step 1", expected_output="Out 1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.CANCELLED,
        step_statuses={"step-1": StepStatus.PENDING},
    )

    proj = WorkflowProjection.from_state(state, plan)
    assert proj.workflow_status == WorkflowStatus.CANCELLED
    assert proj.is_terminal


def test_step_status_rendering():
    """
    TEST 5: Step status rendering for PENDING, READY, RUNNING, PASSED, FAILED, SKIPPED.
    """
    context = create_context("task-statuses")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Multi step test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
            ExecutionStep(step_id="step-2", objective="S2", expected_output="O2"),
            ExecutionStep(step_id="step-3", objective="S3", expected_output="O3"),
            ExecutionStep(step_id="step-4", objective="S4", expected_output="O4"),
            ExecutionStep(step_id="step-5", objective="S5", expected_output="O5"),
            ExecutionStep(step_id="step-6", objective="S6", expected_output="O6"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={
            "step-1": StepStatus.PASSED,
            "step-2": StepStatus.RUNNING,
            "step-3": StepStatus.READY,
            "step-4": StepStatus.PENDING,
            "step-5": StepStatus.FAILED,
            "step-6": StepStatus.SKIPPED,
        },
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    cards = {c["step_id"]: c["status"] for c in rendered["step_cards"]}
    assert cards["step-1"] == "PASSED"
    assert cards["step-2"] == "RUNNING"
    assert cards["step-3"] == "READY"
    assert cards["step-4"] == "PENDING"
    assert cards["step-5"] == "FAILED"
    assert cards["step-6"] == "SKIPPED"


def test_dependency_rendering():
    """
    TEST 6: Dependency rendering shows prerequisite step_ids.
    """
    context = create_context("task-deps")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Dependency test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
            ExecutionStep(step_id="step-2", objective="S2", expected_output="O2"),
            ExecutionStep(
                step_id="step-3",
                objective="S3",
                expected_output="O3",
                dependencies=["step-1", "step-2"],
            ),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={
            "step-1": StepStatus.PASSED,
            "step-2": StepStatus.PASSED,
            "step-3": StepStatus.READY,
        },
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    step_3_card = next(c for c in rendered["step_cards"] if c["step_id"] == "step-3")
    assert step_3_card["dependencies"] == ["step-1", "step-2"]


def test_result_availability():
    """
    TEST 7: Result availability flag is set correctly when step results exist.
    """
    context = create_context("task-res")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Result test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
        ],
    )
    agent_res = AgentResult(request_context=context, status=AgentResultStatus.SUCCESS)
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_results={"step-1": agent_res},
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    step_1_card = rendered["step_cards"][0]
    assert step_1_card["has_result"] is True


def test_artifact_count_and_metadata_visibility():
    """
    TEST 8: Artifact count and artifact names/metadata are visible on dashboard.
    """
    context = create_context("task-art")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Artifact test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
        ],
    )
    art1 = Artifact(
        artifact_id="art-101",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="safety_analysis.pdf",
        location="outputs/safety_analysis.pdf",
        mime_type="application/pdf",
        created_by="test",
    )
    art2 = Artifact(
        artifact_id="art-102",
        task_id=context.task_id,
        type=ArtifactType.DATASET,
        name="incident_data.json",
        location="outputs/incident_data.json",
        mime_type="application/json",
        created_by="test",
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.PASSED},
        step_artifacts={"step-1": [art1, art2]},
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    step_1_card = rendered["step_cards"][0]
    assert step_1_card["artifact_count"] == 2
    assert "safety_analysis.pdf" in step_1_card["artifact_names"]
    assert "incident_data.json" in step_1_card["artifact_names"]
    assert rendered["summary"]["total_artifacts"] == 2


def test_failure_information_visibility():
    """
    TEST 9: Failure information and error messages are visible when step fails.
    """
    context = create_context("task-err")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Failure visibility test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.FAILED,
        step_statuses={"step-1": StepStatus.FAILED},
        step_results={"step-1": "Retrieval failed: Connection timed out"},
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    step_1_card = rendered["step_cards"][0]
    assert step_1_card["status"] == "FAILED"
    assert "Retrieval failed: Connection timed out" in step_1_card["error_message"]


def test_dashboard_does_not_mutate_workflow_state():
    """
    TEST 10: ExecutionDashboard render does NOT mutate WorkflowState.
    """
    context = create_context("task-no-mutate")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Immutability test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
        ],
    )
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={"step-1": StepStatus.RUNNING},
    )

    original_state_dict = copy.deepcopy(state.model_dump())
    dashboard = ExecutionDashboard()
    _ = dashboard.render(state, plan)

    assert state.model_dump() == original_state_dict


def test_dashboard_uses_workflow_state_as_authoritative_status():
    """
    TEST 11: Dashboard uses WorkflowState.status as authoritative workflow status.
    """
    context = create_context("task-auth")
    plan = ExecutionPlan(
        request_context=context,
        task_description="Authoritative status test",
        executable_steps=[
            ExecutionStep(step_id="step-1", objective="S1", expected_output="O1"),
        ],
    )

    # Force state.status to FAILED explicitly
    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.FAILED,
        step_statuses={"step-1": StepStatus.PENDING},
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan)

    assert rendered["workflow_status"] == "FAILED"
    assert rendered["summary"]["has_failure"] is True


def test_six_step_inspection_dag_renders_correctly():
    """
    TEST 12: Six-step inspection DAG renders correctly with step cards and dependencies.
    """
    planner = Planner()
    context = create_context("task-inspection-dag")
    request = TaskRequest(
        request_context=context,
        user_input=(
            "Analyze the inspection report, identify safety findings, "
            "determine applicable SOP requirements, review previous incidents, "
            "recommend corrective actions, and prepare an approval proposal."
        ),
    )
    plan = planner.create_plan(request)

    state = WorkflowState(
        request_context=context,
        task_id=context.task_id,
        plan_id=f"plan-{context.task_id}",
        status=WorkflowStatus.RUNNING,
        step_statuses={
            "step-1": StepStatus.PASSED,
            "step-2": StepStatus.PASSED,
            "step-3": StepStatus.RUNNING,
            "step-4": StepStatus.READY,
            "step-5": StepStatus.PENDING,
            "step-6": StepStatus.PENDING,
        },
    )

    dashboard = ExecutionDashboard()
    rendered = dashboard.render(state, plan, task_request=request)

    assert len(rendered["step_cards"]) == 6
    assert rendered["summary"]["total_steps"] == 6
    assert rendered["summary"]["completed_steps"] == 2

    step_3_card = next(c for c in rendered["step_cards"] if c["step_id"] == "step-3")
    assert step_3_card["dependencies"] == ["step-1", "step-2"]
    assert step_3_card["status"] == "RUNNING"


class MockModelRegistry(ModelRegistry):
    def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.SUCCESS,
            metadata={"mock": True},
        )


def test_full_flow_intake_planner_engine_to_dashboard():
    """
    FULL FLOW TEST:
    TaskRequest → Planner → ExecutionPlan → WorkflowEngine → WorkflowState → ExecutionDashboard
    """
    planner = Planner()
    context = create_context("task-full-flow")
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

    dashboard = ExecutionDashboard()
    rendered_initial = dashboard.render(state, plan, task_request=request)

    assert rendered_initial["workflow_status"] == "RUNNING"
    assert rendered_initial["summary"]["total_steps"] == len(plan.executable_steps)

    # Execute all steps
    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    rendered_final = dashboard.render(state, plan, task_request=request)

    assert rendered_final["workflow_status"] == "COMPLETED"
    assert rendered_final["summary"]["completed_steps"] == len(plan.executable_steps)
    assert rendered_final["summary"]["is_terminal"] is True
