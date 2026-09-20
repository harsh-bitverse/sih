"""Data Retrieval & Knowledge Engine - Core Contracts.

Shared Pydantic data schemas implementing Person 3 specifications,
Slide 0 (RequestContext), Slide 11 (Artifact), and Slide 12 (Evidence).

All data exchanged between the Workflow/Planner, Retrieval Engine,
and the Multimodal Engine must conform to these schemas.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ResourceType(str, Enum):
    """Supported multimodal resource types from industrial documents."""
    TEXT = "text"
    PDF_PAGE = "pdf_page"
    IMAGE = "image"
    TABLE = "table"
    DOCUMENT = "document"
    FILE_REFERENCE = "file_reference"


class RetrievalStatus(str, Enum):
    """Execution status for retrieval operation."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NO_DATA = "NO_DATA"
    ERROR = "ERROR"


class RequestContext(BaseModel):
    """Common contract: RequestContext (Slide 0).
    
    Carries execution trace and component origin across all subsystem boundaries.
    """
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="Unique ID for this particular request")
    task_id: str = Field(..., description="Identifies the user's overall task")
    user_id: str = Field(..., description="Identifies authenticated user")
    parent_request_id: Optional[str] = Field(None, description="Links this request to the request that caused it")
    step_id: Optional[str] = Field(None, description="Identifies current execution step (e.g., 'step_2')")
    source_component: str = Field(..., description="Origin component (e.g., 'workflow_engine', 'retrieval_engine')")
    target_component: Optional[str] = Field(None, description="Intended receiver (e.g., 'multimodal_engine')")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )


class LocationReference(BaseModel):
    """Pinpoints the physical or logical coordinate within the source artifact."""
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Local relative path to file on disk")
    page_number: Optional[int] = Field(None, description="1-indexed page number if PDF/document")
    bounding_box: Optional[List[float]] = Field(
        None, 
        description="Normalized coordinates [ymin, xmin, ymax, xmax] if visual region"
    )
    sheet_name: Optional[str] = Field(None, description="Worksheet name if spreadsheet")
    row_range: Optional[List[int]] = Field(None, description="[start_row, end_row] if tabular data")
    section: Optional[str] = Field(None, description="Heading/section title if text document")


class Provenance(BaseModel):
    """Strict lineage certificate for industrial compliance & audit trails."""
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., description="Official document identifier (e.g., 'DOC-SOP-MECH-401')")
    document_version: str = Field(..., description="Version string (e.g., 'v3.2')")
    document_title: Optional[str] = Field(None, description="Document human-readable title")
    author_department: Optional[str] = Field(None, description="Authoring department/unit (e.g., 'Inspection Dept')")
    effective_date: Optional[str] = Field(None, description="Date version was approved/effective")
    classification: str = Field(
        default="CONFIDENTIAL_INTERNAL", 
        description="Security classification (e.g., 'CONFIDENTIAL_INTERNAL', 'RESTRICTED')"
    )


class RetrievedResource(BaseModel):
    """Standardized Evidence Unit (Slides 11 & 12).
    
    Represents high-precision filtered evidence with attached provenance
    ready for direct ingestion by the Multimodal Engine.
    """
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., description="Unique evidence ID (e.g., 'ev-98231')")
    document_id: str = Field(..., description="Document identifier")
    document_version: str = Field(..., description="Document version")
    resource_type: ResourceType = Field(..., description="Modality of the resource")
    content: str = Field(..., description="Extracted text excerpt, Markdown table, or visual summary")
    location: LocationReference = Field(..., description="Exact coordinates/reference in source file")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Refinery metadata: equipment_id, system, fluid, temp, pressure"
    )
    relevance_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Relevance confidence score (0.0 to 1.0). Low scores are filtered out."
    )
    provenance: Provenance = Field(..., description="Full provenance metadata")


class RetrievalRequest(BaseModel):
    """Input contract for Retrieval Engine (Person 3)."""
    model_config = ConfigDict(extra="forbid")

    request_context: RequestContext = Field(..., description="Trace context with origin and step ID")
    query: str = Field(..., description="User or agent natural language / technical query")
    source_scope: str = Field(
        default="MRPL refinery documentation", 
        description="Domain/scope (e.g., 'MRPL safety documentation')"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Key-value filters (e.g., {'equipment_id': 'E-204', 'department': 'Maintenance'})"
    )
    version_policy: str = Field(
        default="current_only", 
        description="Policy: 'current_only', 'all_versions', or exact version string"
    )
    modality_filter: Optional[List[ResourceType]] = Field(
        default=None, 
        description="List of allowed modalities (e.g., [ResourceType.PDF_PAGE, ResourceType.TABLE])"
    )
    max_results: int = Field(default=5, ge=1, le=50, description="Max number of high-quality results to return")
    required_information: Optional[str] = Field(
        default=None, 
        description="Explicit description of the specific information needed by the downstream agent"
    )


class RetrievalResult(BaseModel):
    """Output contract for Retrieval Engine (Person 3) handed directly to Multimodal Engine."""
    model_config = ConfigDict(extra="forbid")

    request_context: RequestContext = Field(
        ..., 
        description="Echoes the request context with updated source_component and target_component"
    )
    status: RetrievalStatus = Field(..., description="Execution status")
    results: List[RetrievedResource] = Field(
        default_factory=list, 
        description="List of verified, high-precision Evidence items"
    )
    errors: List[str] = Field(default_factory=list, description="Any operational or retrieval warnings/errors")
