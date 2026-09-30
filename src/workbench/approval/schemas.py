"""
Human Approval Schemas.

Owned by: Developer 1 (System Architect)
Subsystem: approval
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext


class ApprovalStatus(str, Enum):
    """
    Lifecycle status of a human approval request.
    """
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalRequest(BaseModel):
    """
    Contract representing a human approval request for a proposed deliverable.
    """
    approval_id: str = Field(description="Unique identifier for the approval request")
    request_context: RequestContext = Field(description="Propagated request context")
    deliverable: Artifact = Field(description="The proposed deliverable artifact under review")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PROPOSED, description="Current decision status"
    )
    reviewer_id: Optional[str] = Field(
        default=None, description="User/reviewer identity making the approval decision"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of approval request creation",
    )
    decided_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp when approval decision was rendered"
    )
    comment: Optional[str] = Field(
        default=None, description="Optional reviewer feedback, rationale, or rejection reason"
    )


class ApprovalDecision(BaseModel):
    """
    Contract representing an incoming approval or rejection decision.
    """
    approval_id: str = Field(description="Identifier of the approval request being decided")
    status: ApprovalStatus = Field(description="Decision outcome (APPROVED or REJECTED)")
    reviewer_id: str = Field(description="Identity of the reviewer submitting the decision")
    comment: Optional[str] = Field(
        default=None, description="Optional reviewer feedback or explanation"
    )
