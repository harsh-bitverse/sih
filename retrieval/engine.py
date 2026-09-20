"""Precision Knowledge Retrieval Engine for Sovereign On-Premise Industrial Workbench.

Implements Person 3 responsibilities using:
- Hybrid Search Engine (BM25Okapi + TF-IDF Vector Cosine Similarity + Entity Anchors)
- Strict Document Version Policies (rejects obsolete versions)
- Modality Filters (text, table, image, pdf)
- Precision Scoring & Noise Elimination Barrier
- Standardized RetrievalResult for direct consumption by Multimodal Engine
"""

from typing import List, Optional
import uuid

try:
    from .contracts import (
        RequestContext,
        ResourceType,
        RetrievalRequest,
        RetrievalResult,
        RetrievalStatus,
        RetrievedResource,
    )
    from .database import SimulatedMRPLDatabase
    from .hybrid_search import HybridSearchEngine
except ImportError:
    from contracts import (
        RequestContext,
        ResourceType,
        RetrievalRequest,
        RetrievalResult,
        RetrievalStatus,
        RetrievedResource,
    )
    from database import SimulatedMRPLDatabase
    from hybrid_search import HybridSearchEngine


# Minimum confidence threshold: below this, matching items are rejected as noise
MIN_RELEVANCE_THRESHOLD = 0.35


class KnowledgeRetrievalEngine:
    """Core Retrieval Engine decoupling search algorithms from calling subsystems."""

    def __init__(self, database: Optional[SimulatedMRPLDatabase] = None):
        """Initializes the engine with dependency injection for the knowledge store."""
        self.db = database or SimulatedMRPLDatabase()

    def execute_retrieval(self, request: RetrievalRequest) -> RetrievalResult:
        """Executes a precision retrieval request adhering to the integration contract."""
        try:
            # 1. Prepare RequestContext envelope for the outgoing response
            result_context = RequestContext(
                request_id=request.request_context.request_id,
                task_id=request.request_context.task_id,
                user_id=request.request_context.user_id,
                parent_request_id=request.request_context.request_id,
                step_id=request.request_context.step_id,
                source_component="retrieval_engine",      # Stamped: originated from us
                target_component="multimodal_engine",     # Stamped: destination is multimodal
            )

            all_resources = self.db.list_all_resources()
            candidates: List[RetrievedResource] = []

            # -------------------------------------------------------------
            # PRE-FILTER GATES: Version Policy, Modality, and Explicit Metadata
            # -------------------------------------------------------------
            for resource in all_resources:
                # GATE 1: Version Policy Filtering
                if request.version_policy == "current_only":
                    doc_status = self.db.get_document_status(
                        resource.document_id, resource.document_version
                    )
                    if doc_status == "SUPERSEDED":
                        continue
                elif request.version_policy not in ("all_versions", "current_only"):
                    if resource.document_version != request.version_policy:
                        continue

                # GATE 2: Modality Filter
                if request.modality_filter and resource.resource_type not in request.modality_filter:
                    continue

                # GATE 3: Explicit Metadata Key-Value Filters
                if request.filters:
                    matches_filters = True
                    for key, val in request.filters.items():
                        if resource.metadata.get(key) != val:
                            matches_filters = False
                            break
                    if not matches_filters:
                        continue

                candidates.append(resource)

            if not candidates:
                return RetrievalResult(
                    request_context=result_context,
                    status=RetrievalStatus.NO_DATA,
                    results=[],
                    errors=[],
                )

            # -------------------------------------------------------------
            # GATE 4: Hybrid Search & Precision Scoring (BM25 + Vectors + Entities)
            # -------------------------------------------------------------
            search_engine = HybridSearchEngine(candidates)
            scored_candidates = search_engine.score(request.query)

            # Strict noise barrier: Drop weak / superficial matches
            filtered_results: List[RetrievedResource] = []
            for res, score in scored_candidates:
                if score >= MIN_RELEVANCE_THRESHOLD:
                    scored_res = res.model_copy(update={"relevance_score": score})
                    filtered_results.append(scored_res)

            # Sort by relevance score descending
            filtered_results.sort(key=lambda r: r.relevance_score, reverse=True)
            top_results = filtered_results[: request.max_results]

            # Determine status
            status = RetrievalStatus.SUCCESS if len(top_results) > 0 else RetrievalStatus.NO_DATA

            return RetrievalResult(
                request_context=result_context,
                status=status,
                results=top_results,
                errors=[],
            )

        except Exception as exc:
            error_context = RequestContext(
                request_id=request.request_context.request_id,
                task_id=request.request_context.task_id,
                user_id=request.request_context.user_id,
                step_id=request.request_context.step_id,
                source_component="retrieval_engine",
                target_component="multimodal_engine",
            )
            return RetrievalResult(
                request_context=error_context,
                status=RetrievalStatus.ERROR,
                results=[],
                errors=[f"Retrieval engine execution error: {str(exc)}"],
            )

    def search(
        self,
        query: str,
        version_policy: str = "current_only",
        modality_filter: Optional[List[ResourceType]] = None,
        max_results: int = 5,
        user_id: str = "plant-operator",
        task_id: str = "interactive-query",
    ) -> RetrievalResult:
        """Convenience helper allowing teammates to query in 1 line without assembling Pydantic envelopes."""
        request = RetrievalRequest(
            request_context=RequestContext(
                request_id=f"req-{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                user_id=user_id,
                step_id="step_2",
                source_component="workflow_engine",
                target_component="retrieval_engine",
            ),
            query=query,
            source_scope="MRPL refinery documentation",
            version_policy=version_policy,
            modality_filter=modality_filter,
            max_results=max_results,
            required_information=query,
        )
        return self.execute_retrieval(request)

