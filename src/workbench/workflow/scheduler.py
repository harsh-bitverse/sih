"""
Workflow Step Scheduler Interface.

Owned by: Developer 1 (System Architect)
Subsystem: workflow
"""

from typing import List
from workbench.planner.schemas import ExecutionPlan, ExecutionStep
from workbench.workflow.state import WorkflowState


class StepScheduler:
    """
    Evaluates step dependency readiness and determines which steps are executable.
    """

    def get_ready_steps(self, plan: ExecutionPlan, state: WorkflowState) -> List[ExecutionStep]:
        """
        Returns steps whose dependencies are fully satisfied and status is PENDING/READY.
        """
        raise NotImplementedError("StepScheduler.get_ready_steps will be implemented by Developer 1.")
