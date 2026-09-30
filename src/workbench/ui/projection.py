"""
Workflow Presentation Projection Model.

Owned by: Developer 1 (System Architect)
Subsystem: ui

Provides a read-only presentation projection derived strictly from WorkflowState,
ExecutionPlan, and TaskRequest. Does NOT maintain independent state.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from workbench.planner.schemas import ExecutionPlan, TaskRequest
from workbench.workflow.state import StepStatus, WorkflowState, WorkflowStatus


class StepProjection(BaseModel):
    """
    Read-only presentation projection of a single execution step.
    """
    step_id: str = Field(description="Unique step identifier")
    objective: str = Field(description="Step objective/goal description")
    status: StepStatus = Field(description="Current step execution status")
    dependencies: List[str] = Field(default_factory=list, description="Step dependency step_ids")
    has_result: bool = Field(default=False, description="Whether execution result is available")
    artifact_count: int = Field(default=0, description="Number of generated artifacts")
    artifact_names: List[str] = Field(default_factory=list, description="Names of generated artifacts")
    error_message: Optional[str] = Field(default=None, description="Step failure or error details")
    result_summary: Optional[str] = Field(default=None, description="Step result summary")


class WorkflowProjection(BaseModel):
    """
    Read-only presentation projection of an entire workflow execution.
    Derived directly from WorkflowState and ExecutionPlan.
    """
    task_id: str = Field(description="Task identifier")
    plan_id: str = Field(description="Execution plan identifier")
    task_description: str = Field(description="Task description being executed")
    workflow_status: WorkflowStatus = Field(description="Authoritative workflow lifecycle status")
    steps: List[StepProjection] = Field(default_factory=list, description="Step projections")
    completed_steps_count: int = Field(default=0, description="Count of passed steps")
    failed_steps_count: int = Field(default=0, description="Count of failed steps")
    total_steps_count: int = Field(default=0, description="Total steps count")
    total_artifacts_count: int = Field(default=0, description="Total artifacts count across steps")
    is_terminal: bool = Field(default=False, description="Whether workflow is in terminal state")
    has_failure: bool = Field(default=False, description="Whether workflow or any step has failed")

    @classmethod
    def from_state(
        cls,
        state: WorkflowState,
        plan: ExecutionPlan,
        task_request: Optional[TaskRequest] = None,
    ) -> "WorkflowProjection":
        """
        Constructs a read-only WorkflowProjection from authoritative WorkflowState and ExecutionPlan.
        """
        task_desc = plan.task_description
        if task_request and task_request.user_input:
            task_desc = task_request.user_input

        step_projections: List[StepProjection] = []
        total_artifacts = 0
        completed_count = 0
        failed_count = 0

        for step in plan.executable_steps:
            st = state.step_statuses.get(step.step_id, StepStatus.PENDING)
            if st == StepStatus.PASSED:
                completed_count += 1
            elif st == StepStatus.FAILED:
                failed_count += 1

            artifacts = state.step_artifacts.get(step.step_id, [])
            art_count = len(artifacts)
            total_artifacts += art_count
            art_names = [art.name for art in artifacts if hasattr(art, "name")]

            step_res = state.step_results.get(step.step_id)
            has_res = step_res is not None

            err_msg: Optional[str] = None
            res_sum: Optional[str] = None

            if step_res is not None:
                if isinstance(step_res, str):
                    if st == StepStatus.FAILED:
                        err_msg = step_res
                    else:
                        res_sum = step_res
                elif hasattr(step_res, "errors") and step_res.errors:
                    err_msg = ", ".join(step_res.errors)
                    res_sum = f"Result status: {getattr(step_res, 'status', 'UNKNOWN')}"
                elif hasattr(step_res, "status"):
                    res_sum = f"Result status: {step_res.status.value}"

            step_proj = StepProjection(
                step_id=step.step_id,
                objective=step.objective,
                status=st,
                dependencies=list(step.dependencies),
                has_result=has_res,
                artifact_count=art_count,
                artifact_names=art_names,
                error_message=err_msg,
                result_summary=res_sum,
            )
            step_projections.append(step_proj)

        terminal_statuses = {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
        is_term = state.status in terminal_statuses
        has_fail = state.status == WorkflowStatus.FAILED or failed_count > 0

        return cls(
            task_id=state.task_id,
            plan_id=state.plan_id,
            task_description=task_desc,
            workflow_status=state.status,
            steps=step_projections,
            completed_steps_count=completed_count,
            failed_steps_count=failed_count,
            total_steps_count=len(plan.executable_steps),
            total_artifacts_count=total_artifacts,
            is_terminal=is_term,
            has_failure=has_fail,
        )


class DeliverableProjection(BaseModel):
    """
    Read-only presentation projection of a generated final deliverable Artifact.
    """
    artifact_id: str = Field(description="Deliverable artifact identifier")
    task_id: str = Field(description="Task identifier")
    name: str = Field(description="Deliverable name/filename")
    type: str = Field(description="Artifact type classification")
    location: str = Field(description="Storage URI or path")
    mime_type: str = Field(description="MIME type classification")
    created_by: str = Field(description="Creator component/subsystem")
    source_information: dict[str, Any] = Field(default_factory=dict, description="Creation process metadata")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")

    @classmethod
    def from_artifact(cls, art: Any) -> "DeliverableProjection":
        type_str = art.type.value if hasattr(art.type, "value") else str(art.type)
        return cls(
            artifact_id=art.artifact_id,
            task_id=art.task_id,
            name=art.name,
            type=type_str,
            location=art.location,
            mime_type=art.mime_type,
            created_by=art.created_by,
            source_information=dict(art.source_information or {}),
            metadata=dict(art.metadata or {}),
        )


class ApprovalProjection(BaseModel):
    """
    Read-only presentation projection of an ApprovalRequest.
    """
    approval_id: str = Field(description="Unique approval request identifier")
    deliverable_id: str = Field(description="Deliverable artifact ID under review")
    deliverable_name: str = Field(description="Deliverable artifact name")
    task_id: str = Field(description="Associated task identifier")
    status: str = Field(description="Approval decision status: PROPOSED, APPROVED, or REJECTED")
    reviewer_id: Optional[str] = Field(default=None, description="Reviewer identity if decided")
    decided_at: Optional[str] = Field(default=None, description="ISO timestamp of decision if decided")
    comment: Optional[str] = Field(default=None, description="Reviewer comment or rejection reason")
    can_decide: bool = Field(default=False, description="True ONLY when status is PROPOSED")
    consequential_action_boundary_message: str = Field(description="Security boundary status message")

    @classmethod
    def from_request(cls, req: Any) -> "ApprovalProjection":
        st_val = req.status.value if hasattr(req.status, "value") else str(req.status)
        can_dec = st_val == "PROPOSED"

        decided_at_str: Optional[str] = None
        if getattr(req, "decided_at", None) is not None:
            decided_at_str = req.decided_at.isoformat()

        if st_val == "PROPOSED":
            msg = "Consequential actions are blocked until approval."
        elif st_val == "APPROVED":
            msg = "Deliverable approved. Consequential action is permitted by the approval boundary."
        else:
            msg = "Deliverable rejected. Consequential action remains blocked."

        return cls(
            approval_id=req.approval_id,
            deliverable_id=req.deliverable.artifact_id,
            deliverable_name=req.deliverable.name,
            task_id=req.request_context.task_id,
            status=st_val,
            reviewer_id=req.reviewer_id,
            decided_at=decided_at_str,
            comment=req.comment,
            can_decide=can_dec,
            consequential_action_boundary_message=msg,
        )
