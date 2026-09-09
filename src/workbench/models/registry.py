"""
Model Registry Interface.

Owned by: Developer 2 (Model Engineer)
Subsystem: models

Model selection is driven by capability and task requirements, not file extensions.
"""

from typing import List, Optional
from workbench.models.interfaces import AgentRequest


class ModelRegistry:
    """
    Registry for open-weight multimodal models and capability resolution.
    """

    def select_model(self, request: AgentRequest) -> str:
        """
        Selects an appropriate model based on required capabilities and task requirements.
        """
        raise NotImplementedError("ModelRegistry.select_model will be implemented by Developer 2.")
