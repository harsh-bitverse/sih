"""
Workflow Execution State Schema.

Owned by: Developer 1 (System Architect)
Subsystem: workflow
"""

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from workbench.core.artifacts import Artifact


class StepStatus(str, Enum):
    """Lifecycle status of an execution step."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowState(BaseModel):
    """
    Maintains the runtime execution state of a task plan.
    """
    task_id: str = Field(description="Task identifier being executed")
    plan_id: str = Field(description="Plan identifier associated with this workflow")
    step_statuses: Dict[str, StepStatus] = Field(
        default_factory=dict, description="Map of step_id to current StepStatus"
    )
    step_results: Dict[str, Any] = Field(
        default_factory=dict, description="Map of step_id to step execution results/evidence"
    )
    step_artifacts: Dict[str, List[Artifact]] = Field(
        default_factory=dict, description="Map of step_id to generated artifacts"
    )
    retry_counts: Dict[str, int] = Field(
        default_factory=dict, description="Map of step_id to retry count attempts"
    )
