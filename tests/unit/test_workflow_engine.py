"""
Unit tests for the Workflow Engine.

Owned by: Developer 1 (System Architect)
"""

from workbench.core.context import RequestContext
from workbench.planner.schemas import ExecutionPlan, ExecutionStep
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowStatus
from workbench.models.interfaces import AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.workflow.validation import StepValidator


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class MockModelRegistry(ModelRegistry):
    """Model Registry that always returns a successful AgentResult."""

    def execute(self, request):
        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.SUCCESS,
        )


class FailingMockModelRegistry(ModelRegistry):
    """Model Registry that always returns a failed AgentResult."""

    def execute(self, request):
        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.FAILED,
        )


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def create_context() -> RequestContext:
    return RequestContext(
        request_id="req-engine-test",
        task_id="task-engine-test",
        user_id="test-user",
        source_component="test",
    )


def create_engine(model_registry=None) -> WorkflowEngine:
    """
    Create a WorkflowEngine with the dependencies required by the
    current production constructor.
    """
    if model_registry is None:
        model_registry = MockModelRegistry()

    return WorkflowEngine(
        model_registry=model_registry,
        step_validator=StepValidator(),
    )


def create_plan(steps: list[ExecutionStep]) -> ExecutionPlan:
    context = create_context()

    return ExecutionPlan(
        request_context=context,
        task_description="Test workflow",
        executable_steps=steps,
    )


# ---------------------------------------------------------------------------
# Workflow initialization tests
# ---------------------------------------------------------------------------

def test_execute_plan_initializes_workflow_state():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="First step",
                expected_output="First result",
            )
        ]
    )

    state = engine.execute_plan(plan)

    assert state.task_id == "task-engine-test"
    assert state.plan_id == "plan-task-engine-test"
    assert state.status == WorkflowStatus.RUNNING


def test_step_without_dependencies_is_ready():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="Independent step",
                expected_output="Result",
            )
        ]
    )

    state = engine.execute_plan(plan)

    assert state.step_statuses["step-1"] == StepStatus.READY


def test_step_with_unfinished_dependency_remains_pending():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="First step",
                expected_output="Result",
            ),
            ExecutionStep(
                step_id="step-2",
                objective="Second step",
                expected_output="Result",
                dependencies=["step-1"],
            ),
        ]
    )

    state = engine.execute_plan(plan)

    assert state.step_statuses["step-1"] == StepStatus.READY
    assert state.step_statuses["step-2"] == StepStatus.PENDING


def test_step_becomes_ready_when_all_dependencies_have_passed():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="First step",
                expected_output="Result",
            ),
            ExecutionStep(
                step_id="step-2",
                objective="Second step",
                expected_output="Result",
                dependencies=["step-1"],
            ),
        ]
    )

    state = engine.execute_plan(plan)

    # Simulate successful completion of step-1.
    state.step_statuses["step-1"] = StepStatus.PASSED

    engine._update_ready_steps(plan, state)

    assert state.step_statuses["step-2"] == StepStatus.READY


def test_step_with_multiple_dependencies_waits_for_all():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="First step",
                expected_output="Result",
            ),
            ExecutionStep(
                step_id="step-2",
                objective="Second step",
                expected_output="Result",
            ),
            ExecutionStep(
                step_id="step-3",
                objective="Third step",
                expected_output="Result",
                dependencies=["step-1", "step-2"],
            ),
        ]
    )

    state = engine.execute_plan(plan)

    assert state.step_statuses["step-1"] == StepStatus.READY
    assert state.step_statuses["step-2"] == StepStatus.READY
    assert state.step_statuses["step-3"] == StepStatus.PENDING

    # Only one dependency completed.
    state.step_statuses["step-1"] = StepStatus.PASSED

    engine._update_ready_steps(plan, state)

    assert state.step_statuses["step-3"] == StepStatus.PENDING

    # Both dependencies completed.
    state.step_statuses["step-2"] = StepStatus.PASSED

    engine._update_ready_steps(plan, state)

    assert state.step_statuses["step-3"] == StepStatus.READY


def test_retry_counts_are_initialized_to_zero():
    engine = create_engine()

    plan = create_plan(
        [
            ExecutionStep(
                step_id="step-1",
                objective="Test step",
                expected_output="Result",
            ),
            ExecutionStep(
                step_id="step-2",
                objective="Another step",
                expected_output="Result",
                dependencies=["step-1"],
            ),
        ]
    )

    state = engine.execute_plan(plan)

    assert state.retry_counts["step-1"] == 0
    assert state.retry_counts["step-2"] == 0


# ---------------------------------------------------------------------------
# Step execution tests
# ---------------------------------------------------------------------------

def test_execute_next_step_passes_successful_step():
    context = RequestContext(
        request_id="req-1",
        task_id="task-1",
        user_id="user-1",
        source_component="test",
    )

    step = ExecutionStep(
        step_id="step-1",
        objective="Perform test task",
        expected_output="Test result",
        passing_criteria={
            "agent_status": "SUCCESS",
        },
    )

    plan = ExecutionPlan(
        request_context=context,
        task_description="Test workflow",
        executable_steps=[step],
    )

    engine = WorkflowEngine(
        model_registry=MockModelRegistry(),
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.PASSED
    assert "step-1" in state.step_results


def test_execute_next_step_fails_when_validation_fails():
    context = RequestContext(
        request_id="req-2",
        task_id="task-2",
        user_id="user-1",
        source_component="test",
    )

    step = ExecutionStep(
        step_id="step-1",
        objective="Perform test task",
        expected_output="Test result",
        passing_criteria={
            "agent_status": "SUCCESS",
        },
    )

    plan = ExecutionPlan(
        request_context=context,
        task_description="Test workflow",
        executable_steps=[step],
    )

    engine = WorkflowEngine(
        model_registry=FailingMockModelRegistry(),
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.FAILED


def test_execute_next_step_releases_dependent_step():
    context = RequestContext(
        request_id="req-3",
        task_id="task-3",
        user_id="user-1",
        source_component="test",
    )

    step_1 = ExecutionStep(
        step_id="step-1",
        objective="Complete first task",
        expected_output="First result",
        passing_criteria={
            "agent_status": "SUCCESS",
        },
    )

    step_2 = ExecutionStep(
        step_id="step-2",
        objective="Complete second task",
        expected_output="Second result",
        dependencies=["step-1"],
        passing_criteria={
            "agent_status": "SUCCESS",
        },
    )

    plan = ExecutionPlan(
        request_context=context,
        task_description="Test dependent workflow",
        executable_steps=[step_1, step_2],
    )

    engine = WorkflowEngine(
        model_registry=MockModelRegistry(),
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)

    assert state.step_statuses["step-1"] == StepStatus.READY
    assert state.step_statuses["step-2"] == StepStatus.PENDING

    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.PASSED
    assert state.step_statuses["step-2"] == StepStatus.READY


def test_execute_next_step_does_nothing_when_no_step_is_ready():
    context = RequestContext(
        request_id="req-4",
        task_id="task-4",
        user_id="user-1",
        source_component="test",
    )

    step = ExecutionStep(
        step_id="step-1",
        objective="Complete dependent task",
        expected_output="Result",
        dependencies=["missing-step"],
        passing_criteria={
            "agent_status": "SUCCESS",
        },
    )

    plan = ExecutionPlan(
        request_context=context,
        task_description="Test blocked workflow",
        executable_steps=[step],
    )

    engine = WorkflowEngine(
        model_registry=MockModelRegistry(),
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)

    assert state.step_statuses["step-1"] == StepStatus.PENDING

    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.PENDING
    assert "step-1" not in state.step_results


# ---------------------------------------------------------------------------
# Workflow lifecycle tests
# ---------------------------------------------------------------------------

def test_workflow_starts_as_running():
    engine = create_engine()
    plan = create_plan([
        ExecutionStep(step_id="step-1", objective="Step 1", expected_output="Output 1"),
        ExecutionStep(step_id="step-2", objective="Step 2", expected_output="Output 2", dependencies=["step-1"]),
    ])

    state = engine.execute_plan(plan)

    assert state.status == WorkflowStatus.RUNNING
    assert state.step_statuses["step-1"] == StepStatus.READY
    assert state.step_statuses["step-2"] == StepStatus.PENDING


def test_workflow_becomes_completed_after_all_steps_pass():
    engine = create_engine()
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            passing_criteria={"agent_status": "SUCCESS"},
        )
    ])

    state = engine.execute_plan(plan)
    assert state.status == WorkflowStatus.RUNNING

    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED


def test_workflow_becomes_failed_when_step_fails():
    engine = create_engine(model_registry=FailingMockModelRegistry())
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            passing_criteria={"agent_status": "SUCCESS"},
        )
    ])

    state = engine.execute_plan(plan)
    assert state.status == WorkflowStatus.RUNNING

    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED


def test_failed_workflow_does_not_execute_downstream_steps():
    engine = create_engine(model_registry=FailingMockModelRegistry())
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            passing_criteria={"agent_status": "SUCCESS"},
        ),
        ExecutionStep(
            step_id="step-2",
            objective="Step 2",
            expected_output="Output 2",
            dependencies=["step-1"],
            passing_criteria={"agent_status": "SUCCESS"},
        ),
    ])

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED
    assert state.step_statuses["step-2"] == StepStatus.PENDING


def test_completed_workflow_does_not_execute_more_steps():
    mock_registry = MockModelRegistry()
    engine = create_engine(model_registry=mock_registry)
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            passing_criteria={"agent_status": "SUCCESS"},
        )
    ])

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)
    assert state.status == WorkflowStatus.COMPLETED

    state_after = engine.execute_next_step(plan, state)
    assert state_after.status == WorkflowStatus.COMPLETED


def test_failed_workflow_does_not_execute_more_steps():
    mock_registry = FailingMockModelRegistry()
    engine = create_engine(model_registry=mock_registry)
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            passing_criteria={"agent_status": "SUCCESS"},
        )
    ])

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)
    assert state.status == WorkflowStatus.FAILED

    state_after = engine.execute_next_step(plan, state)
    assert state_after.status == WorkflowStatus.FAILED


def test_workflow_does_not_complete_when_no_ready_steps_exist_but_steps_remain_unfinished():
    engine = create_engine()
    plan = create_plan([
        ExecutionStep(
            step_id="step-1",
            objective="Step 1",
            expected_output="Output 1",
            dependencies=["nonexistent-step"],
            passing_criteria={"agent_status": "SUCCESS"},
        )
    ])

    state = engine.execute_plan(plan)
    assert state.status == WorkflowStatus.RUNNING

    state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.RUNNING
    assert state.step_statuses["step-1"] == StepStatus.PENDING