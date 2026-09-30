"""Hybrid Search Engine combining BM25Plus, TF-IDF Cosine Vector Search,
and Domain Entity Anchor Detection.

Implements state-of-the-art information retrieval:
1. Sparse Lexical Search: rank_bm25.BM25Plus (guarantees positive IDF and length norm b=0.75)
2. Dense N-Gram Vector Search: scikit-learn TfidfVectorizer + cosine_similarity
3. Domain Entity Anchors: High-entropy plant tags (equipment, hazardous gases, standards)
"""

import re
from typing import List, Set, Tuple
import numpy as np
from rank_bm25 import BM25Plus
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from .contracts import RetrievedResource
except ImportError:
    from contracts import RetrievedResource


# Stop words that carry zero technical value
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "of", "for", "in", "on", "at", "to", "with",
    "by", "from", "is", "are", "was", "were", "what", "which", "how", "requirements",
    "relevant", "current", "sop", "please", "find", "show", "give", "report"
}

# Critical plant entity regex patterns (Equipment tags, standards, chemicals)
ENTITY_PATTERNS = [
    re.compile(r"\b[A-Z0-9]{1,4}-[A-Z0-9]{2,6}\b"),                    # Equipment: E-204, P-101A, F-104, CDU-COL-01
    re.compile(r"\b(H2S|LEL|LPG|BENZENE|SOUR GAS)\b", re.IGNORECASE),  # Hazardous Chemicals
    re.compile(r"\b(API\s*[0-9A-Z]+|ASTM\s*[A-Z0-9]+|ASME\s*[A-Z0-9]+)\b", re.IGNORECASE),  # Standards
]


class EntityAnchorDetector:
    """Detects mission-critical high-entropy industrial tokens."""

    @staticmethod
    def extract_entities(text: str) -> Set[str]:
        """Extracts equipment tags, chemicals, and standards from text."""
        entities = set()
        text_upper = text.upper()
        for pattern in ENTITY_PATTERNS:
            for match in pattern.finditer(text_upper):
                clean_tag = re.sub(r"\s+", "", match.group(0).upper())
                entities.add(clean_tag)
        return entities


class HybridSearchEngine:
    """Hybrid Search combining BM25Plus, Vector Cosine Similarity, and Entity Anchors."""

    def __init__(self, resources: List[RetrievedResource]):
        self.resources = resources
        self.corpus_raw = [self._prepare_doc_text(r) for r in resources]
        self.tokenized_corpus = [self._tokenize(doc) for doc in self.corpus_raw]

        # 1. Initialize BM25Plus index (robust across small and large corpora)
        if self.tokenized_corpus:
            self.bm25 = BM25Plus(self.tokenized_corpus)
        else:
            self.bm25 = None

        # 2. Initialize Vectorizer for Dense Lexical/Semantic N-Gram Vector Space
        self.vectorizer = TfidfVectorizer(
            token_pattern=r"(?u)\b[\w-]+\b",
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
        )
        if self.corpus_raw:
            self.doc_vectors = self.vectorizer.fit_transform(self.corpus_raw)
        else:
            self.doc_vectors = None

    def _prepare_doc_text(self, resource: RetrievedResource) -> str:
        """Combines title, section, content, and metadata for comprehensive indexing."""
        parts = [
            resource.provenance.document_title or "",
            resource.location.section or "",
            resource.content,
            str(resource.metadata.get("equipment_id", "")),
        ]
        return " ".join(parts)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizes text for BM25 preserving hyphenated technical codes."""
        words = re.findall(r"\b[\w-]+\b", text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) > 1]

    def score(self, query: str) -> List[Tuple[RetrievedResource, float]]:
        """Computes combined hybrid relevance scores for all resources."""
        if not self.resources:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [(r, 0.0) for r in self.resources]

        # 1. BM25Plus Scores
        raw_bm25 = self.bm25.get_scores(query_tokens)
        max_bm25 = float(np.max(raw_bm25)) if np.max(raw_bm25) > 0 else 1.0
        min_bm25 = float(np.min(raw_bm25))
        range_bm25 = max_bm25 - min_bm25
        norm_bm25 = (raw_bm25 - min_bm25) / range_bm25 if range_bm25 > 0 else np.ones_like(raw_bm25) * 0.5

        # 2. Dense Vector Cosine Similarity Scores
        query_vec = self.vectorizer.transform([query.lower()])
        cos_scores = cosine_similarity(query_vec, self.doc_vectors).flatten()

        # 3. Entity Anchor Extraction
        query_entities = EntityAnchorDetector.extract_entities(query)

        scored_results: List[Tuple[RetrievedResource, float]] = []

        for idx, resource in enumerate(self.resources):
            bm25_score = float(norm_bm25[idx])
            vector_score = float(cos_scores[idx])

            # Check Entity Anchor match
            entity_boost = 0.0
            resource_entities = EntityAnchorDetector.extract_entities(self.corpus_raw[idx])
            common_entities = query_entities.intersection(resource_entities)
            if query_entities:
                if common_entities:
                    entity_boost = 0.40  # Strong boost for exact entity match
                else:
                    # Penalize if the user requested a specific piece of equipment (e.g., P-101A)
                    # and this document belongs to another piece of equipment (e.g., E-204)
                    res_eq = resource.metadata.get("equipment_id")
                    if res_eq and res_eq.upper() not in query_entities:
                        entity_boost = -0.30

            # Base relevance from BM25 and vector similarity
            base_relevance = (0.45 * bm25_score) + (0.45 * vector_score)

            # If no entity queried, base relevance stands; if entity queried, apply boost/penalty
            final_score = base_relevance + entity_boost

            # Bound score between 0.0 and 1.0
            final_score = max(0.0, min(1.0, final_score))
            scored_results.append((resource, round(final_score, 2)))

        return scored_results
