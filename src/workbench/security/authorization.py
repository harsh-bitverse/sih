"""
Security Authorization Interface.

Owned by: Developer 6 (Security/Audit Engineer)
Subsystem: security
"""

from workbench.core.context import RequestContext


class AuthorizationPolicy:
    """
    Interface for evaluating user and step authorization for system operations.
    """

    def authorize_action(self, context: RequestContext, action: str, resource_uri: str) -> bool:
        """
        Evaluates whether an action on a resource is permitted under current policy.
        """
        raise NotImplementedError("AuthorizationPolicy.authorize_action will be implemented by Developer 6.")
