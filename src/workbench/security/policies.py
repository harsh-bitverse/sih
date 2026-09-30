"""
Security Policies & Mock Implementation Definitions.

Owned by: Developer 6 (Security/Audit Engineer)
Subsystem: security
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from workbench.core.context import RequestContext
from workbench.security.audit import AuditRecord, AuditRegistry
from workbench.security.authorization import AuthorizationPolicy


class SecurityPolicies(BaseModel):
    """
    Configuration model for security policy enforcement.
    """

    allow_external_network: bool = Field(
        default=False, description="Zero-egress constraint flag"
    )
    enforce_strict_audit: bool = Field(
        default=True, description="Strict audit logging flag"
    )
    max_execution_timeout_seconds: int = Field(
        default=300, description="Max execution window"
    )


class MockAuthorizationPolicy(AuthorizationPolicy):
    """
    Mock implementation of AuthorizationPolicy for testing and demo composition.
    """

    def __init__(
        self,
        default_allow: bool = True,
        denied_actions: Optional[Set[str]] = None,
        denied_resources: Optional[Set[str]] = None,
    ) -> None:
        self.default_allow = default_allow
        self.denied_actions = denied_actions or set()
        self.denied_resources = denied_resources or set()
        self.checks: List[Dict[str, str]] = []

    def authorize_action(
        self, context: RequestContext, action: str, resource_uri: str
    ) -> bool:
        self.checks.append(
            {
                "action": action,
                "resource_uri": resource_uri,
                "task_id": context.task_id,
            }
        )
        if action in self.denied_actions or resource_uri in self.denied_resources:
            return False
        return self.default_allow


class MockAuditRegistry(AuditRegistry):
    """
    Mock implementation of AuditRegistry for testing and demo composition.
    """

    def __init__(self) -> None:
        self.recorded_events: List[AuditRecord] = []

    def record_event(self, record: AuditRecord) -> None:
        self.recorded_events.append(record)
