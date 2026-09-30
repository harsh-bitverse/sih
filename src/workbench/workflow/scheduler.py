"""
Workflow Step Scheduler.

Owned by: Developer 1 (System Architect)
Subsystem: workflow

The scheduler determines which execution steps are currently ready.
It does not mutate workflow state and does not execute steps.
"""

from workbench.planner.schemas import ExecutionPlan, ExecutionStep
from workbench.workflow.state import StepStatus, WorkflowState


class StepScheduler:
    """
    Evaluates step dependency readiness and determines which steps
    are currently executable.
    """

    def get_ready_steps(
        self,
        plan: ExecutionPlan,
        state: WorkflowState,
    ) -> list[ExecutionStep]:
        """
        Return steps that are currently ready for execution.

        A step is ready when:
        1. Its current status is PENDING or READY.
        2. Every declared dependency has PASSED.

        Steps with no dependencies are ready immediately.

        This method does not modify WorkflowState.
        """

        ready_steps: list[ExecutionStep] = []

        for step in plan.executable_steps:
            current_status = state.step_statuses.get(
                step.step_id,
                StepStatus.PENDING,
            )

            if current_status not in {
                StepStatus.PENDING,
                StepStatus.READY,
            }:
                continue

            dependencies_satisfied = all(
                state.step_statuses.get(dependency_id) == StepStatus.PASSED
                for dependency_id in step.dependencies
            )

            if dependencies_satisfied:
                ready_steps.append(step)

        return ready_steps