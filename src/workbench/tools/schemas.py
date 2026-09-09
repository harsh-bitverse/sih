"""
Tool Subsystem Contract Schemas.

Owned by: Developer 5 (Tool/Sandbox Engineer)
Subsystem: tools
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext
from workbench.core.types import Evidence


class ToolResultStatus(str, Enum):
    """Result status of a tool invocation."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ToolRequest(BaseModel):
    """
    Contract requesting local tool execution.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    tool_name: str = Field(description="Name of registered tool capability to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Named parameters supplied to tool"
    )


class ToolResult(BaseModel):
    """
    Contract returning tool execution result to the invoking Agent.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    status: ToolResultStatus = Field(description="Tool execution status")
    output: Any = Field(default=None, description="Returned tool execution payload/output")
    evidence: List[Evidence] = Field(
        default_factory=list, description="Structured evidence generated during execution"
    )
    artifacts: List[Artifact] = Field(
        default_factory=list, description="Artifacts created during execution"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if tool execution failed"
    )
