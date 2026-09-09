"""
Core Artifact Schema.

Owned by: Developer 1 (System Architect)
Subsystem: core
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Supported artifact types within the workbench system."""
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    CODE = "CODE"
    DATASET = "DATASET"
    REPORT = "REPORT"
    OTHER = "OTHER"


class Artifact(BaseModel):
    """
    Representation of a generated or processed artifact file/data object.
    """
    artifact_id: str = Field(description="Unique identifier for the artifact")
    task_id: str = Field(description="Task identifier to which this artifact belongs")
    step_id: Optional[str] = Field(
        default=None, description="Optional workflow step identifier that produced the artifact"
    )
    type: ArtifactType = Field(description="Category or type of the artifact")
    name: str = Field(description="Human-readable filename or descriptive title")
    location: str = Field(description="Storage URI or filesystem path to artifact")
    mime_type: str = Field(description="MIME type classification of the content")
    created_by: str = Field(description="Subsystem or agent identifier that generated this artifact")
    source_information: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata regarding creation tool, model, or process"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional custom metadata tags and attributes"
    )
