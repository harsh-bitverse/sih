"""Unit tests for HybridSearchEngine and EntityAnchorDetector."""

from contracts import (
    LocationReference,
    Provenance,
    ResourceType,
    RetrievedResource,
)
from hybrid_search import EntityAnchorDetector, HybridSearchEngine


def test_entity_anchor_detector():
    """Verify that detector catches equipment tags, chemicals, and standards."""
    text = "Inspect E-204 and check for H2S leaks per API 610 and ASTM A193 requirements."
    entities = EntityAnchorDetector.extract_entities(text)

    assert "E-204" in entities
    assert "H2S" in entities
    assert "API610" in entities
    assert "ASTMA193" in entities


def test_hybrid_search_scoring():
    """Verify that BM25 + Vector + Entity scoring elevates relevant documents and drops noise."""
    res1 = RetrievedResource(
        evidence_id="ev-1",
        document_id="DOC-1",
        document_version="v1",
        resource_type=ResourceType.TEXT,
        content="Heat Exchanger E-204 bolt torque specification is 300 Nm",
        location=LocationReference(file_path="f1.pdf"),
        metadata={"equipment_id": "E-204"},
        relevance_score=1.0,
        provenance=Provenance(document_id="DOC-1", document_version="v1"),
    )

    res2 = RetrievedResource(
        evidence_id="ev-2",
        document_id="DOC-2",
        document_version="v1",
        resource_type=ResourceType.TEXT,
        content="Cafeteria lunch menu and office paper supply",
        location=LocationReference(file_path="f2.pdf"),
        metadata={},
        relevance_score=1.0,
        provenance=Provenance(document_id="DOC-2", document_version="v1"),
    )

    search_engine = HybridSearchEngine([res1, res2])
    scored = search_engine.score("E-204 bolt torque")

    # Score of res1 must be high (>0.60)
    score1 = [s for r, s in scored if r.evidence_id == "ev-1"][0]
    score2 = [s for r, s in scored if r.evidence_id == "ev-2"][0]

    assert score1 >= 0.60
    assert score2 < 0.10
