"""
Planner Contract Schemas.

Owned by: Developer 1 (System Architect)
Subsystem: planner
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference


class TaskRequest(BaseModel):
    """
    Contract representing an incoming task request submitted by a user.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    user_input: str = Field(description="Raw user task description or prompt")
    resources: List[ResourceReference] = Field(
        default_factory=list, description="Input resources supplied with the task"
    )
    requested_output_info: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata describing desired deliverable specifications"
    )


class ExecutionStep(BaseModel):
    """
    Contract representing a single executable step decomposed by the Planner.
    """
    step_id: str = Field(description="Unique identifier for this step within the plan")
    objective: str = Field(description="Clear description of the step goal/objective")
    required_context: Dict[str, Any] = Field(
        default_factory=dict, description="Contextual inputs required for execution"
    )
    resources: List[ResourceReference] = Field(
        default_factory=list, description="Resources specifically required for this step"
    )
    expected_output: str = Field(description="Description of expected step output or evidence")
    dependencies: List[str] = Field(
        default_factory=list, description="List of step_ids that must complete prior to this step"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict, description="Execution constraints (e.g. timeout, security level)"
    )
    passing_criteria: Dict[str, Any] = Field(
        default_factory=dict, description="Criteria against which step results are validated"
    )


class ExecutionPlan(BaseModel):
    """
    Contract representing the complete plan produced directly by the Planner.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    task_description: str = Field(description="High-level task description being planned")
    executable_steps: List[ExecutionStep] = Field(
        default_factory=list, description="Sequential/DAG list of executable steps"
    )
