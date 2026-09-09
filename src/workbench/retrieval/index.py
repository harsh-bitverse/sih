"""
Vector Index Interface.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""


class VectorIndex:
    """
    Abstractions for local vector database index operations.
    """

    def search(self, query_vector: list, top_k: int = 5) -> list:
        """
        Executes vector similarity search against the index.
        """
        raise NotImplementedError("VectorIndex.search will be implemented by Developer 3.")
