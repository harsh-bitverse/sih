"""
Retrieval Metadata Schemas.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

from pydantic import BaseModel, Field


class DocumentChunkMetadata(BaseModel):
    """
    Metadata associated with an indexed document chunk.
    """
    document_id: str = Field(description="Parent document identifier")
    chunk_index: int = Field(description="Sequence index of the chunk")
    page_number: int = Field(default=1, description="Page number if derived from paged document")
    author: str = Field(default="unknown", description="Author or creator of source document")
