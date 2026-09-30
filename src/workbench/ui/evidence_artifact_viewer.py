"""
Read-Only Evidence and Artifact Viewer Component.

Owned by: Developer 1 (System Architect)
Subsystem: ui

Provides read-only presentation projections and step-level inspection views for Evidence
and Artifact objects stored in WorkflowState.
Does NOT mutate backend objects or execute backend services.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.types import ConfidenceSource, Evidence
from workbench.models.interfaces import AgentResult
from workbench.planner.schemas import ExecutionPlan
from workbench.workflow.state import StepStatus, WorkflowState


class EvidenceProjection(BaseModel):
    """
    Read-only presentation projection of an Evidence item.
    """
    evidence_id: str = Field(description="Unique evidence identifier")
    source_artifact: Optional[str] = Field(default=None, description="Optional source artifact ID")
    content_preview: str = Field(description="String preview/payload of evidence content")
    location: Optional[str] = Field(default=None, description="Detailed location reference")
    evidence_type: str = Field(description="Categorical evidence type")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Origin tracking details")
    confidence: Optional[float] = Field(default=None, description="Optional confidence score 0.0-1.0")
    confidence_source: Optional[str] = Field(default=None, description="Confidence source model/system")
    has_confidence: bool = Field(default=False, description="Whether confidence score is present")
    has_provenance: bool = Field(default=False, description="Whether provenance details exist")

    @classmethod
    def from_evidence(cls, ev: Evidence) -> "EvidenceProjection":
        conf_src_str = (
            ev.confidence_source.value
            if isinstance(ev.confidence_source, ConfidenceSource)
            else ev.confidence_source
        )

        content_str = str(ev.content)
        if len(content_str) > 300:
            content_str = content_str[:297] + "..."

        return cls(
            evidence_id=ev.evidence_id,
            source_artifact=ev.source_artifact,
            content_preview=content_str,
            location=ev.location,
            evidence_type=ev.evidence_type,
            provenance=dict(ev.provenance or {}),
            confidence=ev.confidence,
            confidence_source=conf_src_str,
            has_confidence=ev.confidence is not None,
            has_provenance=bool(ev.provenance),
        )


class ArtifactProjection(BaseModel):
    """
    Read-only presentation projection of an Artifact item.
    """
    artifact_id: str = Field(description="Unique artifact identifier")
    task_id: str = Field(description="Task identifier")
    step_id: Optional[str] = Field(default=None, description="Step identifier")
    type: str = Field(description="Artifact category type")
    name: str = Field(description="Human-readable filename/title")
    location: str = Field(description="Storage URI or file path")
    mime_type: str = Field(description="MIME type classification")
    created_by: str = Field(description="Creator subsystem/agent")
    source_information: Dict[str, Any] = Field(default_factory=dict, description="Creation process metadata")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")
    has_metadata: bool = Field(default=False, description="Whether custom metadata exists")
    has_source_info: bool = Field(default=False, description="Whether source information exists")

    @classmethod
    def from_artifact(cls, art: Artifact) -> "ArtifactProjection":
        type_str = art.type.value if isinstance(art.type, ArtifactType) else str(art.type)
        return cls(
            artifact_id=art.artifact_id,
            task_id=art.task_id,
            step_id=art.step_id,
            type=type_str,
            name=art.name,
            location=art.location,
            mime_type=art.mime_type,
            created_by=art.created_by,
            source_information=dict(art.source_information or {}),
            metadata=dict(art.metadata or {}),
            has_metadata=bool(art.metadata),
            has_source_info=bool(art.source_information),
        )


class StepEvidenceArtifactProjection(BaseModel):
    """
    Read-only presentation projection of Evidence and Artifacts associated with a workflow step.
    """
    step_id: str = Field(description="Step identifier")
    evidence_list: List[EvidenceProjection] = Field(default_factory=list, description="Step evidence projections")
    artifacts_list: List[ArtifactProjection] = Field(default_factory=list, description="Step artifact projections")
    evidence_count: int = Field(default=0, description="Total evidence count")
    artifact_count: int = Field(default=0, description="Total artifact count")
    step_status: Optional[str] = Field(default=None, description="Step execution status")
    is_failed: bool = Field(default=False, description="Whether step execution failed")


class EvidenceArtifactViewer:
    """
    UI Viewer Component for read-only inspection of Evidence and Artifact objects.
    """

    def project_step(
        self, state: WorkflowState, step_id: str
    ) -> StepEvidenceArtifactProjection:
        """
        Projects evidence and artifacts for a specific step_id in WorkflowState.
        """
        st = state.step_statuses.get(step_id)
        st_str = st.value if isinstance(st, StepStatus) else str(st) if st else None

        artifacts_raw = state.step_artifacts.get(step_id, [])
        art_projections = [ArtifactProjection.from_artifact(art) for art in artifacts_raw]

        evidence_projections: List[EvidenceProjection] = []
        step_res = state.step_results.get(step_id)

        if isinstance(step_res, AgentResult):
            for ev in step_res.result_evidence:
                evidence_projections.append(EvidenceProjection.from_evidence(ev))
        elif isinstance(step_res, list):
            for item in step_res:
                if isinstance(item, Evidence):
                    evidence_projections.append(EvidenceProjection.from_evidence(item))
        elif isinstance(step_res, Evidence):
            evidence_projections.append(EvidenceProjection.from_evidence(step_res))

        is_failed = st == StepStatus.FAILED or (
            isinstance(step_res, AgentResult) and step_res.status.value == "FAILED"
        )

        return StepEvidenceArtifactProjection(
            step_id=step_id,
            evidence_list=evidence_projections,
            artifacts_list=art_projections,
            evidence_count=len(evidence_projections),
            artifact_count=len(art_projections),
            step_status=st_str,
            is_failed=is_failed,
        )

    def render_step_inspection(
        self, state: WorkflowState, step_id: str
    ) -> Dict[str, Any]:
        """
        Renders a step-level inspection dictionary for UI display.
        Does NOT mutate state.
        """
        proj = self.project_step(state, step_id)
        return proj.model_dump()

    def render_full_viewer(
        self, state: WorkflowState, plan: Optional[ExecutionPlan] = None
    ) -> Dict[str, Any]:
        """
        Renders step-by-step evidence and artifact inspection cards for the entire workflow.
        Does NOT mutate state.
        """
        step_ids = list(state.step_statuses.keys())
        if plan:
            plan_step_ids = [s.step_id for s in plan.executable_steps]
            for s_id in plan_step_ids:
                if s_id not in step_ids:
                    step_ids.append(s_id)

        step_inspections = []
        total_ev_count = 0
        total_art_count = 0

        for s_id in step_ids:
            proj = self.project_step(state, s_id)
            total_ev_count += proj.evidence_count
            total_art_count += proj.artifact_count
            step_inspections.append(proj.model_dump())

        return {
            "title": f"Evidence & Artifact Viewer - {state.task_id}",
            "task_id": state.task_id,
            "workflow_status": state.status.value,
            "summary": {
                "total_evidence_items": total_ev_count,
                "total_artifacts": total_art_count,
                "inspected_steps_count": len(step_inspections),
            },
            "step_inspections": step_inspections,
        }
