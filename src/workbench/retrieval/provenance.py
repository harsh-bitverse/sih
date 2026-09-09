"""
Retrieval Provenance Tracker.

Owned by: Developer 3 (Retrieval Engineer)
Subsystem: retrieval
"""

from typing import Any, Dict
from pydantic import BaseModel, Field


class RetrievalProvenance(BaseModel):
    """
    Tracking object for document retrieval lineage and source verification.
    """
    source_uri: str = Field(description="URI or path of the original source document")
    hash: str = Field(description="Cryptographic hash of source document chunk")
    extraction_method: str = Field(description="Method used to extract text/content")
    extra_details: Dict[str, Any] = Field(default_factory=dict)
