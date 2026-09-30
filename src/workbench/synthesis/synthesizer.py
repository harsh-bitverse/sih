"""
Final Deliverable Synthesis Implementation.

Owned by: Developer 1 (System Architect)
Subsystem: synthesis

After all required steps pass, Final Synthesis combines the original task
with relevant step results, evidence, and artifacts to produce the requested final deliverable.
"""

from typing import Any, Dict, List, Optional

from workbench.core.types import ResourceReference, ResourceType
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.planner.schemas import TaskRequest
from workbench.workflow.state import WorkflowState, WorkflowStatus


class FinalSynthesizer:
    """
    Synthesizes final task deliverable from task inputs and validated step execution evidence.
    """

    def __init__(self, model_registry: Optional[ModelRegistry] = None) -> None:
        self.model_registry = model_registry

    def synthesize_deliverable(
        self, original_task: TaskRequest, final_workflow_state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Combines original task requirements with workflow evidence to produce final deliverable.
        """
        if self.model_registry is None:
            raise NotImplementedError("FinalSynthesizer requires a ModelRegistry instance.")
        if final_workflow_state.status != WorkflowStatus.COMPLETED:
            raise ValueError(
                f"Cannot synthesize deliverable for workflow with status '{final_workflow_state.status.value}'. "
                f"Workflow status must be '{WorkflowStatus.COMPLETED.value}'."
            )

        context_resources: List[ResourceReference] = list(original_task.resources)

        for step_id, artifacts in final_workflow_state.step_artifacts.items():
            for art in artifacts:
                res = ResourceReference(
                    resource_id=art.artifact_id,
                    resource_type=ResourceType.GENERATED_ARTIFACT,
                    uri_or_path=art.location,
                    provenance={"step_id": step_id, "created_by": art.created_by},
                    metadata=art.metadata or {},
                )
                context_resources.append(res)

        for step_id, step_res in final_workflow_state.step_results.items():
            if isinstance(step_res, AgentResult):
                for ev in step_res.result_evidence:
                    if isinstance(ev.content, ResourceReference):
                        context_resources.append(ev.content)
                    else:
                        uri = ev.location or f"evidence://{ev.evidence_id}"
                        res = ResourceReference(
                            resource_id=ev.evidence_id,
                            resource_type=ResourceType.RETRIEVED,
                            uri_or_path=uri,
                            provenance=ev.provenance or {"step_id": step_id},
                            metadata={"evidence_type": ev.evidence_type},
                        )
                        context_resources.append(res)

        objective_desc = (
            f"Synthesize final deliverable for task: '{original_task.user_input}'. "
            f"Requested format/info: {original_task.requested_output_info}"
        )
        expected_out = str(
            original_task.requested_output_info.get(
                "description", "Final synthesized deliverable document"
            )
        )

        agent_request = AgentRequest(
            request_context=original_task.request_context,
            objective=objective_desc,
            context_resources=context_resources,
            required_capabilities=["synthesis"],
            expected_output=expected_out,
        )

        agent_result = self.model_registry.execute(agent_request)

        if agent_result.status == AgentResultStatus.FAILED or agent_result.errors:
            return {
                "status": "FAILED",
                "request_context": original_task.request_context,
                "task_id": original_task.request_context.task_id,
                "user_input": original_task.user_input,
                "errors": agent_result.errors or ["Final synthesis model execution failed."],
                "synthesized_text": None,
                "artifacts": agent_result.artifacts,
                "result_evidence": agent_result.result_evidence,
                "requested_output_info": original_task.requested_output_info,
            }

        return {
            "status": "SUCCESS",
            "request_context": original_task.request_context,
            "task_id": original_task.request_context.task_id,
            "user_input": original_task.user_input,
            "synthesized_text": f"Synthesized final deliverable output for task: {original_task.user_input}",
            "artifacts": agent_result.artifacts,
            "result_evidence": agent_result.result_evidence,
            "requested_output_info": original_task.requested_output_info,
            "step_results_count": len(final_workflow_state.step_results),
            "context_resources_count": len(context_resources),
        }
