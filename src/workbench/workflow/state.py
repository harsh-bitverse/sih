"""
Workflow Execution State Schema.

Owned by: Developer 1 (System Architect)
Subsystem: workflow
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext


class StepStatus(str, Enum):
    """Lifecycle status of an execution step."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowStatus(str, Enum):
    """Lifecycle status of the overall workflow."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowState(BaseModel):
    """
    Maintains the runtime execution state of a task plan.

    WorkflowState represents what has happened during workflow execution.
    It does not contain orchestration logic; transitions are controlled by
    the Workflow Engine.
    """

    request_context: RequestContext = Field(
        description="Request context associated with this workflow execution"
    )

    task_id: str = Field(
        description="Task identifier being executed"
    )

    plan_id: str = Field(
        description="Execution plan identifier associated with this workflow"
    )

    status: WorkflowStatus = Field(
        default=WorkflowStatus.CREATED,
        description="Current lifecycle status of the overall workflow"
    )

    step_statuses: dict[str, StepStatus] = Field(
        default_factory=dict,
        description="Map of step_id to current StepStatus"
    )

    step_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Map of step_id to step execution results or evidence"
    )

    step_artifacts: dict[str, list[Artifact]] = Field(
        default_factory=dict,
        description="Map of step_id to artifacts generated during execution"
    )

    retry_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Map of step_id to number of retries already performed for "
            "that step"
        )
    )