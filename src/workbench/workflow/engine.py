"""
Workflow Engine Interface.

Owned by: Developer 1 (System Architect)
Subsystem: workflow

Architectural Scope:
The Workflow Engine owns:
- execution state
- step scheduling
- dependency readiness
- sequential progression
- retry/failure handling
- validation against Planner-provided passing criteria

The Workflow Engine must NOT synthesize step results.
The Workflow Engine must NOT directly execute tools (Agent handles tools execution).
"""

from workbench.planner.schemas import ExecutionPlan
from workbench.workflow.state import WorkflowState


class WorkflowEngine:
    """
    State machine and step progress engine for task execution plans.
    """

    def execute_plan(self, plan: ExecutionPlan) -> WorkflowState:
        """
        Executes steps in an ExecutionPlan sequentially/DAG-order, validating step completion.
        """
        raise NotImplementedError("WorkflowEngine.execute_plan will be implemented by Developer 1.")
