"""
Retrieval Subsystem Interface & Contracts.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from workbench.core.context import RequestContext
from workbench.core.types import Evidence


class RetrievalRequest(BaseModel):
    """
    Contract requesting vector/hybrid retrieval over indexed data.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    query: str = Field(description="Search query string")
    top_k: int = Field(default=5, description="Maximum number of results to return")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata filtering criteria"
    )


class RetrievalResult(BaseModel):
    """
    Contract returning retrieved evidence items with provenance.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    results: List[Evidence] = Field(
        default_factory=list, description="Retrieved evidence items with provenance"
    )
    query: str = Field(description="Original query string executed")
    total_hits: int = Field(default=0, description="Total matching documents found")


class Retriever:
    """
    Primary interface for document retrieval operations.
    """

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """
        Performs retrieval and returns structured Evidence results.
        """
        raise NotImplementedError("Retriever.retrieve will be implemented by Developer 3.")
