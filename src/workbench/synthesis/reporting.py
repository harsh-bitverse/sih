"""
Report Generation Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: synthesis
"""

from typing import Any, Dict, Optional

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.errors import SubsystemExecutionError


class ReportGenerator:
    """
    Generates structured human-readable reports and summary documentation.
    """

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def generate_report(self, synthesized_content: Dict[str, Any]) -> Artifact:
        """
        Formats synthesized deliverable into final report artifact.
        """
        if self.should_fail:
            raise SubsystemExecutionError("Report generation failed due to configured generator error.")

        if synthesized_content.get("status") == "FAILED":
            errors = synthesized_content.get("errors", ["Unknown synthesis failure"])
            raise SubsystemExecutionError(f"Cannot generate report from failed synthesis: {errors}")

        ctx: Optional[RequestContext] = synthesized_content.get("request_context")
        task_id = synthesized_content.get(
            "task_id", getattr(ctx, "task_id", "unknown-task")
        )
        requested_output_info = synthesized_content.get("requested_output_info", {})
        fmt = requested_output_info.get("format", "pdf")

        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "json": "application/json",
            "markdown": "text/markdown",
            "txt": "text/plain",
        }
        mime_type = mime_map.get(fmt.lower(), "application/pdf")

        art_id = f"art-final-report-{task_id}"
        name = f"final_deliverable_{task_id}.{fmt}"
        location = f"outputs/final_deliverable_{task_id}.{fmt}"

        metadata = {
            "request_id": getattr(ctx, "request_id", None),
            "user_id": getattr(ctx, "user_id", None),
            "step_results_count": synthesized_content.get("step_results_count", 0),
            "context_resources_count": synthesized_content.get("context_resources_count", 0),
        }

        return Artifact(
            artifact_id=art_id,
            task_id=task_id,
            step_id=None,
            type=ArtifactType.REPORT,
            name=name,
            location=location,
            mime_type=mime_type,
            created_by="synthesis_reporting",
            source_information={
                "synthesized_text": synthesized_content.get("synthesized_text"),
                "user_input": synthesized_content.get("user_input"),
                "requested_output_info": requested_output_info,
            },
            metadata=metadata,
        )
