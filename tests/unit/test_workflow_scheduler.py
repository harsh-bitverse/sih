"""
Unit tests for the Workflow Step Scheduler.

Owned by: Developer 1 (System Architect)
"""

from workbench.core.context import RequestContext
from workbench.planner.schemas import ExecutionPlan, ExecutionStep
from workbench.workflow.scheduler import StepScheduler
from workbench.workflow.state import StepStatus, WorkflowState


def create_context() -> RequestContext:
    return RequestContext(
        request_id="req-scheduler-test",
        task_id="task-scheduler-test",
        user_id="test-user",
        source_component="test",
    )


def create_plan(steps: list[ExecutionStep]) -> ExecutionPlan:
    return ExecutionPlan(
        request_context=create_context(),
        task_description="Scheduler test",
        executable_steps=steps,
    )


def create_state(
    plan: ExecutionPlan,
    statuses: dict[str, StepStatus],
) -> WorkflowState:
    return WorkflowState(
        request_context=plan.request_context,
        task_id=plan.request_context.task_id,
        plan_id=f"plan-{plan.request_context.task_id}",
        step_statuses=statuses,
    )


def test_step_without_dependencies_is_ready():
    scheduler = StepScheduler()

    step = ExecutionStep(
        step_id="step-1",
        objective="Independent step",
        expected_output="Result",
    )

    plan = create_plan([step])

    state = create_state(
        plan,
        {"step-1": StepStatus.PENDING},
    )

    ready_steps = scheduler.get_ready_steps(plan, state)

    assert [step.step_id for step in ready_steps] == ["step-1"]


def test_step_with_unpassed_dependency_is_not_ready():
    scheduler = StepScheduler()

    steps = [
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

    plan = create_plan(steps)

    state = create_state(
        plan,
        {
            "step-1": StepStatus.PENDING,
            "step-2": StepStatus.PENDING,
        },
    )

    ready_steps = scheduler.get_ready_steps(plan, state)

    assert [step.step_id for step in ready_steps] == ["step-1"]


def test_step_becomes_ready_after_dependency_passes():
    scheduler = StepScheduler()

    steps = [
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

    plan = create_plan(steps)

    state = create_state(
        plan,
        {
            "step-1": StepStatus.PASSED,
            "step-2": StepStatus.PENDING,
        },
    )

    ready_steps = scheduler.get_ready_steps(plan, state)

    assert [step.step_id for step in ready_steps] == ["step-2"]


def test_step_with_multiple_dependencies_waits_for_all():
    scheduler = StepScheduler()

    steps = [
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

    plan = create_plan(steps)

    state = create_state(
        plan,
        {
            "step-1": StepStatus.PASSED,
            "step-2": StepStatus.PENDING,
            "step-3": StepStatus.PENDING,
        },
    )

    ready_steps = scheduler.get_ready_steps(plan, state)

    assert [step.step_id for step in ready_steps] == ["step-2"]


def test_scheduler_does_not_return_completed_steps():
    scheduler = StepScheduler()

    step = ExecutionStep(
        step_id="step-1",
        objective="Completed step",
        expected_output="Result",
    )

    plan = create_plan([step])

    state = create_state(
        plan,
        {"step-1": StepStatus.PASSED},
    )

    ready_steps = scheduler.get_ready_steps(plan, state)

    assert ready_steps == []


def test_scheduler_does_not_mutate_state():
    scheduler = StepScheduler()

    step = ExecutionStep(
        step_id="step-1",
        objective="Test step",
        expected_output="Result",
    )

    plan = create_plan([step])

    state = create_state(
        plan,
        {"step-1": StepStatus.PENDING},
    )

    scheduler.get_ready_steps(plan, state)

    assert state.step_statuses["step-1"] == StepStatus.PENDING