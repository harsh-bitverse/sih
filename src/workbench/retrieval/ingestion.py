"""
Document Ingestion Interface.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

from workbench.core.types import ResourceReference


class DocumentIngestor:
    """
    Ingests, parses, and chunks documents for vector index construction.
    """

    def ingest_resource(self, resource: ResourceReference) -> bool:
        """
        Ingests a document or resource into the retrieval pipeline.
        """
        raise NotImplementedError("DocumentIngestor.ingest_resource will be implemented by Developer 3.")
