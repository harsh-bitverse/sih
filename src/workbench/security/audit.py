"""
Security Audit Registry Interface.

Owned by: Developer 6 (Security/Audit Engineer)
Subsystem: security

Audit records security-relevant and execution-relevant events, not merely HTTP/API calls.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from workbench.core.context import RequestContext


class AuditRecord(BaseModel):
    """
    Schema for recording security-relevant and execution-relevant audit events.
    """
    event_id: str = Field(description="Unique event record identity")
    event_type: str = Field(description="Categorical event type (e.g. tool_execution, model_access, authorization_check)")
    request_context: RequestContext = Field(description="Propagated context associated with the event")
    component: str = Field(description="Subsystem or module raising the audit event")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Event specific details and parameters"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of event occurrence"
    )


class AuditRegistry:
    """
    Registry interface for recording and persisting security & execution audit events.
    """

    def record_event(self, record: AuditRecord) -> None:
        """
        Persists an audit record to secure local audit log storage.
        """
        raise NotImplementedError("AuditRegistry.record_event will be implemented by Developer 6.")
