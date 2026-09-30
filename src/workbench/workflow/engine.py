"""
Workflow Engine.

Owned by: Developer 1 (System Architect)
Subsystem: workflow

Architectural Scope:
The Workflow Engine owns:
- execution state
- step scheduling
- dependency readiness
- sequential progression
- retry/failure handling
- validation against Planner-provided passing criteria

The Workflow Engine must NOT synthesize step results.
The Workflow Engine must NOT directly execute tools.
"""

from typing import Any, Dict, Optional
from uuid import uuid4

from workbench.core.context import RequestContext
from workbench.core.types import ResourceReference, ResourceType
from workbench.planner.schemas import ExecutionPlan
from workbench.workflow.state import (
    StepStatus,
    WorkflowState,
    WorkflowStatus,
)
from workbench.workflow.scheduler import StepScheduler
from workbench.models.interfaces import AgentRequest
from workbench.models.registry import ModelRegistry
from workbench.workflow.validation import StepValidator
from workbench.retrieval.retriever import (
    RetrievalRequest,
    RetrievalResult,
    Retriever,
)
from workbench.multimodal.schemas import (
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)
from workbench.multimodal.processor import MultimodalProcessor
from workbench.security.authorization import AuthorizationPolicy
from workbench.security.audit import AuditRecord, AuditRegistry


class WorkflowEngine:
    """
    State machine and step progress engine for task execution plans.
    """

    TERMINAL_STATUSES = {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    }

    def __init__(
        self,
        model_registry: ModelRegistry,
        step_validator: StepValidator,
        retriever: Optional[Retriever] = None,
        multimodal_processor: Optional[MultimodalProcessor] = None,
        authorization_policy: Optional[AuthorizationPolicy] = None,
        audit_registry: Optional[AuditRegistry] = None,
    ) -> None:
        self.scheduler = StepScheduler()
        self.model_registry = model_registry
        self.step_validator = step_validator
        self.retriever = retriever
        self.multimodal_processor = multimodal_processor
        self.authorization_policy = authorization_policy
        self.audit_registry = audit_registry

    def _audit(
        self,
        event_type: str,
        component: str,
        context: RequestContext,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an audit event if an AuditRegistry is configured."""
        if self.audit_registry is not None:
            record = AuditRecord(
                event_id=f"audit-{uuid4()}",
                event_type=event_type,
                request_context=context,
                component=component,
                details=details or {},
            )
            self.audit_registry.record_event(record)

    def execute_plan(self, plan: ExecutionPlan) -> WorkflowState:
        """
        Initialize workflow execution state from an ExecutionPlan.

        Establishes the initial workflow state (RUNNING), initializes all steps
        to PENDING, resolves which steps are immediately READY, and sets initial
        lifecycle status.
        """

        state = WorkflowState(
            request_context=plan.request_context,
            task_id=plan.request_context.task_id,
            plan_id=self._create_plan_id(plan),
            status=WorkflowStatus.RUNNING,
        )

        for step in plan.executable_steps:
            state.step_statuses[step.step_id] = StepStatus.PENDING
            state.retry_counts[step.step_id] = 0

        self._update_ready_steps(plan, state)
        self._update_workflow_status(plan, state)

        self._audit(
            event_type="workflow_started",
            component="workflow_engine",
            context=plan.request_context,
            details={
                "task_id": plan.request_context.task_id,
                "plan_id": state.plan_id,
                "step_count": len(plan.executable_steps),
            },
        )

        return state

    def execute_next_step(
        self,
        plan: ExecutionPlan,
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute the next available step in the workflow."""
        if state.status in self.TERMINAL_STATUSES:
            return state

        ready_steps = self.scheduler.get_ready_steps(plan, state)

        if not ready_steps:
            return state

        step = ready_steps[0]

        if self.authorization_policy is not None:
            action = "execute_step"
            resource_uri = f"step:{step.step_id}"
            is_allowed = self.authorization_policy.authorize_action(
                state.request_context,
                action=action,
                resource_uri=resource_uri,
            )
            self._audit(
                event_type="authorization_check",
                component="security",
                context=state.request_context,
                details={
                    "action": action,
                    "resource_uri": resource_uri,
                    "step_id": step.step_id,
                    "allowed": is_allowed,
                },
            )
            if not is_allowed:
                state.step_statuses[step.step_id] = StepStatus.FAILED
                state.step_results[
                    step.step_id
                ] = f"Authorization denied for action '{action}' on step '{step.step_id}'"
                self._audit(
                    event_type="authorization_denied",
                    component="security",
                    context=state.request_context,
                    details={
                        "action": action,
                        "resource_uri": resource_uri,
                        "step_id": step.step_id,
                    },
                )
                self._update_ready_steps(plan, state)
                self._update_workflow_status(plan, state)
                return state

        state.step_statuses[step.step_id] = StepStatus.RUNNING
        self._audit(
            event_type="step_started",
            component="workflow_engine",
            context=state.request_context,
            details={"step_id": step.step_id, "objective": step.objective},
        )

        context_resources = list(step.resources)

        if self.retriever is not None:
            try:
                retrieval_req = RetrievalRequest(
                    request_context=state.request_context,
                    query=step.objective,
                    top_k=5,
                )
                retrieval_res = self.retriever.retrieve(retrieval_req)
                retrieved_resources = self._extract_resources_from_retrieval(
                    retrieval_res
                )
                context_resources.extend(retrieved_resources)
                self._audit(
                    event_type="retrieval_executed",
                    component="retrieval",
                    context=state.request_context,
                    details={
                        "step_id": step.step_id,
                        "query": step.objective,
                        "retrieved_count": len(retrieved_resources),
                    },
                )
            except Exception as exc:
                state.step_statuses[step.step_id] = StepStatus.FAILED
                state.step_results[step.step_id] = f"Retrieval failed: {exc}"
                self._audit(
                    event_type="retrieval_failed",
                    component="retrieval",
                    context=state.request_context,
                    details={"step_id": step.step_id, "error": str(exc)},
                )
                self._update_ready_steps(plan, state)
                self._update_workflow_status(plan, state)
                return state

        if self.multimodal_processor is not None:
            try:
                resources_to_process = list(context_resources)
                for res in resources_to_process:
                    mm_req = MultimodalRequest(
                        request_context=state.request_context,
                        resource=res,
                    )
                    mm_res = self.multimodal_processor.process(mm_req)

                    if mm_res.status == MultimodalStatus.FAILED:
                        state.step_statuses[step.step_id] = StepStatus.FAILED
                        state.step_results[
                            step.step_id
                        ] = f"Multimodal processing failed: {mm_res.errors}"
                        self._audit(
                            event_type="multimodal_failed",
                            component="multimodal",
                            context=state.request_context,
                            details={
                                "step_id": step.step_id,
                                "resource_id": res.resource_id,
                                "errors": mm_res.errors,
                            },
                        )
                        self._update_ready_steps(plan, state)
                        self._update_workflow_status(plan, state)
                        return state

                    mm_resources = self._extract_resources_from_multimodal(
                        mm_res
                    )
                    context_resources.extend(mm_resources)

                self._audit(
                    event_type="multimodal_executed",
                    component="multimodal",
                    context=state.request_context,
                    details={"step_id": step.step_id},
                )
            except Exception as exc:
                state.step_statuses[step.step_id] = StepStatus.FAILED
                state.step_results[
                    step.step_id
                ] = f"Multimodal processing failed: {exc}"
                self._audit(
                    event_type="multimodal_failed",
                    component="multimodal",
                    context=state.request_context,
                    details={"step_id": step.step_id, "error": str(exc)},
                )
                self._update_ready_steps(plan, state)
                self._update_workflow_status(plan, state)
                return state

        agent_request = AgentRequest(
            request_context=state.request_context,
            objective=step.objective,
            context_resources=context_resources,
            required_capabilities=[],
            expected_output=step.expected_output,
        )

        agent_result = self.model_registry.execute(agent_request)
        self._audit(
            event_type="model_executed",
            component="model_registry",
            context=state.request_context,
            details={
                "step_id": step.step_id,
                "status": str(agent_result.status),
            },
        )

        state.step_results[step.step_id] = agent_result
        state.step_artifacts[step.step_id] = agent_result.artifacts

        validation_result = self.step_validator.validate_step_result(
            step,
            agent_result,
        )

        if validation_result.passed:
            state.step_statuses[step.step_id] = StepStatus.PASSED
            self._audit(
                event_type="step_completed",
                component="workflow_engine",
                context=state.request_context,
                details={"step_id": step.step_id, "status": "PASSED"},
            )
        else:
            state.step_statuses[step.step_id] = StepStatus.FAILED
            self._audit(
                event_type="step_failed",
                component="workflow_engine",
                context=state.request_context,
                details={"step_id": step.step_id, "status": "FAILED"},
            )

        self._update_ready_steps(plan, state)
        self._update_workflow_status(plan, state)

        return state

    def _extract_resources_from_retrieval(
        self, retrieval_result: RetrievalResult
    ) -> list[ResourceReference]:
        """Convert retrieved Evidence items to ResourceReference objects."""
        resources: list[ResourceReference] = []

        for item in retrieval_result.results:
            if isinstance(item.content, ResourceReference):
                resources.append(item.content)
            elif isinstance(item, ResourceReference):
                resources.append(item)
            else:
                uri = item.location or (
                    item.source_artifact
                    if item.source_artifact
                    else f"retrieved://{item.evidence_id}"
                )
                res = ResourceReference(
                    resource_id=item.evidence_id,
                    resource_type=ResourceType.RETRIEVED,
                    uri_or_path=uri,
                    provenance=item.provenance or {},
                    metadata={"evidence_type": item.evidence_type},
                )
                resources.append(res)

        return resources

    def _extract_resources_from_multimodal(
        self, multimodal_result: MultimodalResult
    ) -> list[ResourceReference]:
        """Convert MultimodalResult Evidence and Artifact items to ResourceReference objects."""
        resources: list[ResourceReference] = []

        for item in multimodal_result.evidence:
            if isinstance(item.content, ResourceReference):
                resources.append(item.content)
            elif isinstance(item, ResourceReference):
                resources.append(item)
            else:
                uri = item.location or (
                    item.source_artifact
                    if item.source_artifact
                    else f"multimodal://{item.evidence_id}"
                )
                res = ResourceReference(
                    resource_id=item.evidence_id,
                    resource_type=ResourceType.CONTROLLED_LOCAL,
                    uri_or_path=uri,
                    provenance=item.provenance or {},
                    metadata={"evidence_type": item.evidence_type},
                )
                resources.append(res)

        for art in multimodal_result.artifacts:
            res = ResourceReference(
                resource_id=art.artifact_id,
                resource_type=ResourceType.GENERATED_ARTIFACT,
                uri_or_path=art.location,
                provenance=art.source_information or {},
                metadata=art.metadata or {},
            )
            resources.append(res)

        return resources

    def _create_plan_id(self, plan: ExecutionPlan) -> str:
        """
        Return the identifier used by WorkflowState for this plan.

        Plan identifiers are not yet part of the ExecutionPlan contract.
        Until that contract is finalized, use the task identifier as a
        stable temporary plan identifier.
        """
        return f"plan-{plan.request_context.task_id}"

    def _update_ready_steps(
        self,
        plan: ExecutionPlan,
        state: WorkflowState,
    ) -> None:
        ready_steps = self.scheduler.get_ready_steps(plan, state)

        for step in ready_steps:
            if state.step_statuses[step.step_id] == StepStatus.PENDING:
                state.step_statuses[step.step_id] = StepStatus.READY

    def _update_workflow_status(
        self,
        plan: ExecutionPlan,
        state: WorkflowState,
    ) -> None:
        """
        Update overall workflow lifecycle status based on actual step states.

        - If any executable step has FAILED, workflow status becomes FAILED.
        - If every executable step has PASSED, workflow status becomes COMPLETED.
        - Otherwise, workflow status remains RUNNING.
        """
        if not plan.executable_steps:
            return

        previous_status = state.status

        statuses = [
            state.step_statuses.get(step.step_id) for step in plan.executable_steps
        ]

        if any(status == StepStatus.FAILED for status in statuses):
            state.status = WorkflowStatus.FAILED
        elif all(status == StepStatus.PASSED for status in statuses):
            state.status = WorkflowStatus.COMPLETED

        if previous_status != state.status:
            if state.status == WorkflowStatus.FAILED:
                self._audit(
                    event_type="workflow_failed",
                    component="workflow_engine",
                    context=state.request_context,
                    details={"task_id": state.task_id, "plan_id": state.plan_id},
                )
            elif state.status == WorkflowStatus.COMPLETED:
                self._audit(
                    event_type="workflow_completed",
                    component="workflow_engine",
                    context=state.request_context,
                    details={"task_id": state.task_id, "plan_id": state.plan_id},
                )