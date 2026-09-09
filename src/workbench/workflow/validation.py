"""
Workflow Step Validation Interface.

Owned by: Developer 1 (System Architect)
Subsystem: workflow
"""

from workbench.models.interfaces import AgentResult
from workbench.planner.schemas import ExecutionStep


class StepValidator:
    """
    Validates step results against Planner-provided passing criteria.
    """

    def validate_step_result(self, step: ExecutionStep, agent_result: AgentResult) -> bool:
        """
        Evaluates AgentResult against the step's passing_criteria.
        """
        raise NotImplementedError("StepValidator.validate_step_result will be implemented by Developer 1.")
