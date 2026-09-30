"""
Retrieval Subsystem Interface, Contracts & Sovereign Retriever Adapter.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from workbench.core.context import RequestContext
from workbench.core.types import ConfidenceSource, Evidence, ResourceReference, ResourceType as CoreResourceType
from workbench.retrieval.impl.engine import KnowledgeRetrievalEngine
from workbench.retrieval.impl.contracts import (
    RequestContext as ImplRequestContext,
    RetrievalRequest as ImplRetrievalRequest,
)


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
        raise NotImplementedError("Retriever.retrieve must be implemented by concrete classes.")


class SovereignRetrieverAdapter(Retriever):
    """
    Compatibility Adapter wrapping KnowledgeRetrievalEngine (Person 3 implementation).
    Implements the authoritative Retriever contract on main.
    Translates internal RetrievedResource objects into workbench.core.types.Evidence objects.
    """

    def __init__(self, engine: Optional[KnowledgeRetrievalEngine] = None) -> None:
        self.engine = engine or KnowledgeRetrievalEngine()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """
        Translates core RetrievalRequest to implementation RetrievalRequest,
        executes retrieval via KnowledgeRetrievalEngine, and maps results to core Evidence items.
        """
        impl_ctx = ImplRequestContext(
            request_id=request.request_context.request_id,
            task_id=request.request_context.task_id,
            user_id=request.request_context.user_id,
            step_id=request.request_context.step_id,
            source_component=request.request_context.source_component or "workflow_engine",
            target_component="retrieval_engine",
        )

        impl_req = ImplRetrievalRequest(
            request_context=impl_ctx,
            query=request.query,
            filters=request.filters or None,
            max_results=request.top_k,
        )

        impl_res = self.engine.execute_retrieval(impl_req)

        converted_evidence: List[Evidence] = []
        for item in impl_res.results:
            file_path = item.location.file_path
            if file_path.startswith("simulated_mrpl/"):
                file_path = f"src/workbench/retrieval/impl/{file_path}"

            loc_str = file_path

            provenance_dict = {
                "page_number": item.location.page_number,
                "document_id": item.document_id,
                "document_version": item.document_version,
                "document_title": getattr(item.provenance, "document_title", None),
                "author_department": getattr(item.provenance, "author_department", None),
                "effective_date": getattr(item.provenance, "effective_date", None),
                "classification": getattr(item.provenance, "classification", "CONFIDENTIAL_INTERNAL"),
                "relevance_score": item.relevance_score,
                **(item.metadata or {}),
            }

            conf_score = min(1.0, max(0.0, float(item.relevance_score)))

            ev = Evidence(
                evidence_id=item.evidence_id,
                source_artifact=None,
                content=item.content,
                location=loc_str,
                evidence_type=f"retrieved_{item.resource_type.value}",
                provenance=provenance_dict,
                confidence=conf_score,
                confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
            )
            converted_evidence.append(ev)

        return RetrievalResult(
            request_context=request.request_context,
            results=converted_evidence,
            query=request.query,
            total_hits=len(converted_evidence),
        )
