"""
Unit Tests for SovereignRetrieverAdapter.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

import pytest

from workbench.core.context import RequestContext
from workbench.core.types import ConfidenceSource, Evidence
from workbench.retrieval.retriever import (
    RetrievalRequest,
    RetrievalResult,
    SovereignRetrieverAdapter,
)


def create_context() -> RequestContext:
    return RequestContext(
        request_id="req-adapter-001",
        task_id="task-adapter-001",
        user_id="test_user",
        source_component="test_suite",
    )


def test_adapter_initialization():
    adapter = SovereignRetrieverAdapter()
    assert adapter.engine is not None


def test_adapter_retrieve_query_e204():
    adapter = SovereignRetrieverAdapter()
    context = create_context()
    request = RetrievalRequest(
        request_context=context,
        query="E-204 vibration threshold SOP requirement",
        top_k=5,
    )

    result = adapter.retrieve(request)

    assert isinstance(result, RetrievalResult)
    assert result.request_context == context
    assert result.query == "E-204 vibration threshold SOP requirement"
    assert len(result.results) > 0

    for ev in result.results:
        assert isinstance(ev, Evidence)
        assert ev.evidence_id.startswith("ev-")
        assert ev.content is not None
        assert ev.location is not None
        assert ev.provenance.get("document_id") is not None
        assert ev.confidence is not None
        assert ev.confidence_source == ConfidenceSource.SYSTEM_ASSESSMENT
