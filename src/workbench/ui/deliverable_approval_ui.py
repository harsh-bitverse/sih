"""
Workbench Final Deliverable & Human Approval UI Component.

Owned by: Developer 1 (System Architect)
Subsystem: ui

Provides the user-facing presentation and interaction boundary for reviewing generated
final deliverable Artifacts and rendering explicit human approval decisions (APPROVE/REJECT).
Delegates all state transitions directly to the backend ApprovalManager.
Does NOT mutate ApprovalRequest objects directly.
"""

from typing import Any, Dict, Optional

from workbench.approval.manager import ApprovalManager
from workbench.approval.schemas import ApprovalRequest, ApprovalStatus
from workbench.core.artifacts import Artifact
from workbench.ui.projection import ApprovalProjection, DeliverableProjection


class DeliverableApprovalUI:
    """
    UI component for rendering deliverable views and interacting with ApprovalManager.
    """

    def __init__(self, approval_manager: Optional[ApprovalManager] = None) -> None:
        self.approval_manager = approval_manager or ApprovalManager()

    def render_deliverable_view(self, deliverable: Artifact) -> Dict[str, Any]:
        """
        Renders read-only final deliverable view dictionary.
        Does NOT regenerate report or call backend execution services.
        """
        proj = DeliverableProjection.from_artifact(deliverable)
        return {
            "title": f"Final Deliverable - {proj.name}",
            "artifact_id": proj.artifact_id,
            "task_id": proj.task_id,
            "name": proj.name,
            "type": proj.type,
            "location": proj.location,
            "mime_type": proj.mime_type,
            "created_by": proj.created_by,
            "source_information": proj.source_information,
            "metadata": proj.metadata,
        }

    def render_approval_view(self, request: ApprovalRequest) -> Dict[str, Any]:
        """
        Renders approval request view dictionary including available action controls.
        Active APPROVE / REJECT controls are rendered ONLY when status is PROPOSED.
        """
        proj = ApprovalProjection.from_request(request)

        available_actions = []
        if proj.can_decide:
            available_actions = [
                {"action": "APPROVE", "label": "Approve Deliverable"},
                {"action": "REJECT", "label": "Reject Deliverable"},
            ]

        return {
            "title": f"Human Approval Review - {proj.approval_id}",
            "approval_id": proj.approval_id,
            "deliverable_id": proj.deliverable_id,
            "deliverable_name": proj.deliverable_name,
            "task_id": proj.task_id,
            "status": proj.status,
            "reviewer_id": proj.reviewer_id,
            "decided_at": proj.decided_at,
            "comment": proj.comment,
            "can_decide": proj.can_decide,
            "available_actions": available_actions,
            "consequential_action_boundary_message": proj.consequential_action_boundary_message,
        }

    def render_full_view(
        self, request: ApprovalRequest, deliverable: Optional[Artifact] = None
    ) -> Dict[str, Any]:
        """
        Renders complete view combining deliverable view and approval review view.
        """
        deliv = deliverable or request.deliverable
        deliv_view = self.render_deliverable_view(deliv)
        appr_view = self.render_approval_view(request)

        return {
            "deliverable_view": deliv_view,
            "approval_view": appr_view,
        }

    def handle_approve_action(
        self, approval_id: str, reviewer_id: str, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handles user APPROVE button click by delegating to ApprovalManager.approve_deliverable.
        Returns the re-rendered updated view.
        """
        updated_request = self.approval_manager.approve_deliverable(
            approval_id=approval_id, reviewer_id=reviewer_id, comment=comment
        )
        return self.render_full_view(updated_request)

    def handle_reject_action(
        self, approval_id: str, reviewer_id: str, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handles user REJECT button click by delegating to ApprovalManager.reject_deliverable.
        Returns the re-rendered updated view.
        """
        updated_request = self.approval_manager.reject_deliverable(
            approval_id=approval_id, reviewer_id=reviewer_id, comment=comment
        )
        return self.render_full_view(updated_request)
