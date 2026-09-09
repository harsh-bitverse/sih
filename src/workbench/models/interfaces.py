"""
Model Subsystem Contract Interfaces & Schemas.

Owned by: Developer 2 (Model Engineer)
Subsystem: models
"""

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext
from workbench.core.types import Evidence, ResourceReference


class AgentResultStatus(str, Enum):
    """Execution status of an Agent invocation."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class AgentRequest(BaseModel):
    """
    Contract for requesting agent execution for a specific step or task objective.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    objective: str = Field(description="Goal or objective for agent execution")
    context_resources: List[ResourceReference] = Field(
        default_factory=list, description="Input resources supplied to agent"
    )
    required_capabilities: List[str] = Field(
        default_factory=list, description="Capabilities required for model/agent selection"
    )
    expected_output: str = Field(description="Description of expected output format/content")


class AgentResult(BaseModel):
    """
    Contract for agent execution result returned to Workflow Engine.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    status: AgentResultStatus = Field(description="Final result status of agent execution")
    result_evidence: List[Evidence] = Field(
        default_factory=list, description="Structured evidence extracted during execution"
    )
    artifacts: List[Artifact] = Field(
        default_factory=list, description="Artifacts created during agent execution"
    )
    errors: List[str] = Field(
        default_factory=list, description="Error messages if execution failed or was partial"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Model execution stats, token usage, latency"
    )
