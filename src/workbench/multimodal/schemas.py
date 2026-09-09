"""
Multimodal Contract Schemas & Semantics.

Owned by: Developer 4 (Multimodal Engineer)
Subsystem: multimodal
"""

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from workbench.core.artifacts import Artifact
from workbench.core.context import RequestContext
from workbench.core.types import Evidence, ResourceReference


class MultimodalStatus(str, Enum):
    """
    Multimodal processing status.
    
    PARTIAL indicates that useful evidence was extracted even though some steps/pages failed.
    """
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class Modality(str, Enum):
    """Recognised values for MultimodalRequest.modalities.

    Strings remain accepted for forward compatibility; unknown values are
    reported in metadata rather than rejected, so a caller asking for a
    modality we have not built yet gets a clear answer instead of a crash.
    """
    OCR = "ocr"
    LAYOUT = "layout"
    VISION = "vision"
    TABLE = "table"


SUPPORTED_MODALITIES = frozenset({Modality.OCR.value})


class MultimodalRequest(BaseModel):
    """
    Contract requesting multimodal analysis (OCR, vision parsing, document processing).
    """
    request_context: RequestContext = Field(description="Propagated request context")
    resource: ResourceReference = Field(description="Target document, image, or multimodal resource")
    modalities: List[str] = Field(
        default_factory=list, description="Requested processing modalities (e.g. ocr, layout, vision)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Processing parameters. Recognised: dpi (int), lang (str), "
            "max_pages (int), min_line_confidence (float 0-1)."
        ),
    )


class MultimodalResult(BaseModel):
    """
    Contract returning multimodal processing results and structured evidence.
    
    Evidence items directly contain their own source provenance and location information.
    Confidence values are source-attributed and never averaged across incompatible sources.
    """
    request_context: RequestContext = Field(description="Propagated request context")
    status: MultimodalStatus = Field(description="Processing status (SUCCESS, PARTIAL, FAILED)")
    evidence: List[Evidence] = Field(
        default_factory=list, description="Structured evidence extracted during processing"
    )
    artifacts: List[Artifact] = Field(
        default_factory=list, description="Artifacts generated (e.g. cropped region images, text files)"
    )
    errors: List[str] = Field(
        default_factory=list, description="Errors encountered during processing (populated on PARTIAL/FAILED)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata (processing engine, page count, latency)"
    )
