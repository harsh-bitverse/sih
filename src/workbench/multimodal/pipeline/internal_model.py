"""
Internal, strongly-typed extraction model.

Owned by: Developer 4 (Multimodal Engineer)

WHY THIS EXISTS when core.Evidence already exists:

core.Evidence is deliberately loose - `location` is a free string and
`provenance` is an untyped dict - because it must carry evidence from every
subsystem. Inside this subsystem we can be stricter, and strictness catches
real bugs: a Region whose corners are reversed, or a region that refers to no
stored image, is rejected at construction instead of reaching a consumer.

mapping.py converts these into core.Evidence at the boundary. Nothing outside
this subsystem should import this module.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from workbench.core.types import ConfidenceSource

INTERNAL_MODEL_VERSION = "0.3.0"


class FragmentKind(str, Enum):
    """Maps to core Evidence.evidence_type."""
    TEXT_LINE = "text_line"
    # slice 2: VISUAL_OBSERVATION; slice 3: TABLE_CELL, DRAWING_LABEL


class ErrorStage(str, Enum):
    RESOLUTION = "resolution"
    RENDERING = "rendering"
    EXTRACTION = "extraction"
    VALIDATION = "validation"


class Region(BaseModel):
    """A rectangle on a page image.

    Normalised 0.0-1.0, origin TOP-LEFT, so it stays valid when the page is
    re-rendered at a different DPI. Pixel coordinates silently would not.
    """
    x0: float = Field(ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "Region":
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("Region corners out of order: need x0<=x1, y0<=y1")
        return self

    def as_location(self) -> str:
        return (
            f"bbox=({self.x0:.4f},{self.y0:.4f})-({self.x1:.4f},{self.y1:.4f})"
        )


class Confidence(BaseModel):
    """A confidence value that always declares where it came from.

    Never store a bare float internally. The source is what tells a consumer
    whether this is a measurement (OCR decoder) or a model's self-report,
    which are not comparable and must never be averaged together.
    """
    value: float = Field(ge=0.0, le=1.0)
    source: ConfidenceSource
    interpretation: Optional[str] = None


class PageProvenance(BaseModel):
    """Where a fragment sits, and in which stored image."""
    resource_id: str
    document_hash: str
    page_index: int = Field(ge=0)
    artifact_id: str = Field(
        description="The stored page image the region refers to"
    )
    render_dpi: Optional[int] = Field(default=None, gt=0)


class ExtractedFragment(BaseModel):
    """One unit of extracted evidence, independently traceable."""
    fragment_id: str
    kind: FragmentKind
    content: str = Field(description="UNTRUSTED text lifted from a user document")
    provenance: PageProvenance
    region: Optional[Region] = None
    confidence: Optional[Confidence] = None
    extractor: str


class ProcessingIssue(BaseModel):
    """A non-fatal problem. Drives SUCCESS vs PARTIAL."""
    stage: ErrorStage
    message: str
    resource_id: Optional[str] = None
    page_index: Optional[int] = Field(default=None, ge=0)

    def as_text(self) -> str:
        where = f" [resource={self.resource_id}]" if self.resource_id else ""
        page = f" [page={self.page_index}]" if self.page_index is not None else ""
        return f"{self.stage.value}{where}{page}: {self.message}"


class PageArtifact(BaseModel):
    """A rendered page image this subsystem produced and stored."""
    artifact_id: str
    resource_id: str
    page_index: int = Field(ge=0)
    media_type: str = "image/png"
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    render_dpi: Optional[int] = Field(default=None, gt=0)
    content_hash: str
    source_filename: Optional[str] = None


class ExtractionOutcome(BaseModel):
    """Everything one extraction produced, before mapping to the contract."""
    model_version: str = INTERNAL_MODEL_VERSION
    resource_id: str
    document_hash: Optional[str] = None
    fragments: List[ExtractedFragment] = []
    page_artifacts: List[PageArtifact] = []
    issues: List[ProcessingIssue] = []
    page_count: int = 0
    extractor: Optional[str] = None
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def succeeded(self) -> bool:
        return bool(self.fragments)
