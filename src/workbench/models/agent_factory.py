"""
Agent Factory Interface.

Owned by: Developer 2 (Model Engineer)
Subsystem: models
"""

from workbench.models.interfaces import AgentRequest, AgentResult


class AgentFactory:
    """
    Constructs and executes agent instances capable of handling AgentRequests.
    """

    def execute_agent(self, request: AgentRequest) -> AgentResult:
        """
        Instantiates agent with required tools and model access to process AgentRequest.
        """
        raise NotImplementedError("AgentFactory.execute_agent will be implemented by Developer 2.")
