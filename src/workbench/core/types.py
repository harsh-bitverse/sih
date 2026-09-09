"""
Shared Core Types & Placeholders.

Owned by: Developer 1 (System Architect)
Subsystem: core
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ConfidenceSource(str, Enum):
    """Sources providing confidence estimates for evidence."""
    OCR_ENGINE = "OCR_ENGINE"
    VISION_MODEL = "VISION_MODEL"
    OTHER_MODEL = "OTHER_MODEL"
    SYSTEM_ASSESSMENT = "SYSTEM_ASSESSMENT"


class ResourceType(str, Enum):
    """Categories of resources accessible within the system."""
    USER_PROVIDED = "USER_PROVIDED"
    RETRIEVED = "RETRIEVED"
    GENERATED_ARTIFACT = "GENERATED_ARTIFACT"
    CONTROLLED_LOCAL = "CONTROLLED_LOCAL"


class Evidence(BaseModel):
    """
    Structured evidence item generated during tool execution or model analysis.
    
    Each evidence item independently references its source, provenance, and location.
    Confidence values are never averaged across incompatible sources.
    """
    evidence_id: str = Field(description="Unique identifier for this evidence item")
    source_artifact: Optional[str] = Field(
        default=None, description="Optional ID of the artifact from which this evidence was extracted"
    )
    content: Any = Field(description="Raw or structured content payload of the evidence")
    location: Optional[str] = Field(
        default=None, description="Detailed location reference (page number, bounding box, line, URI)"
    )
    evidence_type: str = Field(description="Categorical type of evidence (e.g. text_snippet, table, visual_feature)")
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed origin and extraction chain details"
    )
    confidence: Optional[float] = Field(
        default=None, description="Optional numerical confidence score between 0.0 and 1.0"
    )
    confidence_source: Optional[ConfidenceSource] = Field(
        default=None, description="Source system or model that calculated the confidence score"
    )


class ResourceReference(BaseModel):
    """
    Controlled representation of input resources.
    
    Refers to external inputs, retrieved content, generated artifacts, or local files
    without granting unrestricted external access.
    """
    resource_id: str = Field(description="Unique resource identifier")
    resource_type: ResourceType = Field(description="Classification of resource source")
    uri_or_path: str = Field(description="Internal controlled URI or file path")
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Origin tracking information for security & audit"
    )
    access_policy: Optional[str] = Field(
        default=None, description="Optional access policy name or scope constraint"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom resource metadata properties"
    )
