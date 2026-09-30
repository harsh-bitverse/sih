"""
Human Approval Manager Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: approval
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Dict as DictType
from uuid import uuid4

from workbench.approval.schemas import ApprovalDecision, ApprovalRequest, ApprovalStatus
from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext
from workbench.core.errors import SecurityViolationError
from workbench.security.audit import AuditRecord, AuditRegistry


class ApprovalManager:
    """
    Manages the human approval lifecycle for proposed task deliverables.
    Enforces terminal safety state transitions, security boundary checks, and audit logging.
    """

    def __init__(self, audit_registry: Optional[AuditRegistry] = None) -> None:
        self.audit_registry = audit_registry
        self._requests: DictType[str, ApprovalRequest] = {}

    def create_approval_request(
        self, deliverable: Artifact, request_context: RequestContext
    ) -> ApprovalRequest:
        """
        Registers a proposed deliverable artifact for human approval.
        Initially placed in PROPOSED status.
        """
        approval_id = f"appr-{uuid4()}"
        req = ApprovalRequest(
            approval_id=approval_id,
            request_context=request_context,
            deliverable=deliverable,
            status=ApprovalStatus.PROPOSED,
        )
        self._requests[approval_id] = req

        self._audit(
            event_type="approval_requested",
            component="approval",
            context=request_context,
            details={
                "approval_id": approval_id,
                "deliverable_id": deliverable.artifact_id,
                "status": ApprovalStatus.PROPOSED.value,
            },
        )

        return req

    def approve_deliverable(
        self, approval_id: str, reviewer_id: str, comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Explicitly approves a proposed deliverable request.
        """
        req = self._get_and_validate_pending_request(approval_id)

        req.status = ApprovalStatus.APPROVED
        req.reviewer_id = reviewer_id
        req.decided_at = datetime.now(timezone.utc)
        req.comment = comment

        self._audit(
            event_type="approval_granted",
            component="approval",
            context=req.request_context,
            details={
                "approval_id": approval_id,
                "reviewer_id": reviewer_id,
                "deliverable_id": req.deliverable.artifact_id,
                "comment": comment,
            },
        )

        return req

    def reject_deliverable(
        self, approval_id: str, reviewer_id: str, comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Explicitly rejects a proposed deliverable request.
        """
        req = self._get_and_validate_pending_request(approval_id)

        req.status = ApprovalStatus.REJECTED
        req.reviewer_id = reviewer_id
        req.decided_at = datetime.now(timezone.utc)
        req.comment = comment

        self._audit(
            event_type="approval_rejected",
            component="approval",
            context=req.request_context,
            details={
                "approval_id": approval_id,
                "reviewer_id": reviewer_id,
                "deliverable_id": req.deliverable.artifact_id,
                "comment": comment,
            },
        )

        return req

    def get_approval_request(self, approval_id: str) -> ApprovalRequest:
        """
        Retrieves an approval request by approval_id.
        """
        if approval_id not in self._requests:
            raise KeyError(f"Approval request '{approval_id}' not found.")
        return self._requests[approval_id]

    def execute_consequential_action(
        self, approval_id: str, action_name: str
    ) -> Dict[str, Any]:
        """
        Enforces consequential action execution boundary.
        Actions are strictly BLOCKED unless the deliverable approval status is APPROVED.
        """
        req = self.get_approval_request(approval_id)
        if req.status != ApprovalStatus.APPROVED:
            raise SecurityViolationError(
                f"Consequential action '{action_name}' blocked: Deliverable approval status is '{req.status.value}'. "
                f"Action execution requires status '{ApprovalStatus.APPROVED.value}'."
            )
        return {
            "status": "EXECUTED",
            "action_name": action_name,
            "approval_id": approval_id,
            "deliverable_id": req.deliverable.artifact_id,
        }

    def _get_and_validate_pending_request(self, approval_id: str) -> ApprovalRequest:
        req = self.get_approval_request(approval_id)
        if req.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError(
                f"Approval request '{approval_id}' has already been decided with status '{req.status.value}'. "
                "Decided approval requests cannot be modified."
            )
        return req

    def _audit(
        self,
        event_type: str,
        component: str,
        context: RequestContext,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.audit_registry is not None:
            record = AuditRecord(
                event_id=f"audit-{uuid4()}",
                event_type=event_type,
                request_context=context,
                component=component,
                details=details or {},
            )
            self.audit_registry.record_event(record)
