"""
Workbench Execution Dashboard Component.

Owned by: Developer 1 (System Architect)
Subsystem: ui

Provides the user-facing workflow execution visualization dashboard.
Renders read-only views derived from WorkflowState and ExecutionPlan.
Does NOT mutate backend state or execute backend services.
"""

from typing import Any, Dict, Optional

from workbench.planner.schemas import ExecutionPlan, TaskRequest
from workbench.ui.projection import WorkflowProjection
from workbench.workflow.state import WorkflowState


class ExecutionDashboard:
    """
    UI Dashboard Component for visualizing workflow execution state.
    """

    def render(
        self,
        state: WorkflowState,
        plan: ExecutionPlan,
        task_request: Optional[TaskRequest] = None,
    ) -> Dict[str, Any]:
        """
        Renders the execution dashboard for the given WorkflowState and ExecutionPlan.
        Returns a structured presentation rendering dictionary.
        Does NOT mutate state.
        """
        projection = WorkflowProjection.from_state(state, plan, task_request)
        return self.render_projection(projection)

    def render_projection(self, projection: WorkflowProjection) -> Dict[str, Any]:
        """
        Formats a WorkflowProjection into a structured presentation dashboard dictionary.
        """
        step_cards = []
        for step in projection.steps:
            card = {
                "step_id": step.step_id,
                "objective": step.objective,
                "status": step.status.value,
                "dependencies": step.dependencies,
                "has_result": step.has_result,
                "artifact_count": step.artifact_count,
                "artifact_names": step.artifact_names,
                "error_message": step.error_message,
                "result_summary": step.result_summary,
            }
            step_cards.append(card)

        return {
            "title": f"Workflow Execution Dashboard - {projection.task_id}",
            "task_id": projection.task_id,
            "plan_id": projection.plan_id,
            "task_description": projection.task_description,
            "workflow_status": projection.workflow_status.value,
            "summary": {
                "total_steps": projection.total_steps_count,
                "completed_steps": projection.completed_steps_count,
                "failed_steps": projection.failed_steps_count,
                "total_artifacts": projection.total_artifacts_count,
                "is_terminal": projection.is_terminal,
                "has_failure": projection.has_failure,
            },
            "step_cards": step_cards,
        }
