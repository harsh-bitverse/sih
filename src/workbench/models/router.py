"""
Model Router Interface.

Owned by: Developer 2 (Model Engineer)
Subsystem: models
"""

from workbench.models.interfaces import AgentRequest, AgentResult


class ModelRouter:
    """
    Routes AgentRequests to designated model endpoints or local serving instances.
    """

    def route_request(self, request: AgentRequest) -> AgentResult:
        """
        Routes and dispatches request to the selected model serving infrastructure.
        """
        raise NotImplementedError("ModelRouter.route_request will be implemented by Developer 2.")
