"""
Shared Core Request Context.

Owned by: Developer 1 (System Architect)
Subsystem: core

RequestContext must be propagated unchanged across subsystem boundaries.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    """
    Context model that tracks invocation metadata across subsystem boundaries.
    
    This object must be passed unchanged along execution paths to maintain
    distributed provenance, auditability, and request tracing.
    """
    request_id: str = Field(description="Unique identity for this execution request")
    task_id: str = Field(description="Identity of the parent task intake request")
    user_id: str = Field(description="Identity of the invoking user or service")
    parent_request_id: Optional[str] = Field(
        default=None, description="Optional parent request ID for nested calls"
    )
    step_id: Optional[str] = Field(
        default=None, description="Optional current step ID within workflow execution"
    )
    source_component: str = Field(
        description="Name of the component creating or propagating this request context"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the context was instantiated or updated",
    )
