"""
First Mocked End-to-End Integration Tests for SIH Sovereign AI Workbench.

Owned by: Developer 1 (System Architect)

Verifies the integrated execution flow across:
    Planner -> ExecutionPlan -> WorkflowEngine -> MockModelRegistry -> AgentResult -> StepValidator -> WorkflowState
    with optional MockRetriever, MockMultimodalProcessor, and MockToolExecutor integrations.
"""

from typing import Optional, Set
import pytest

from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.types import (
    ConfidenceSource,
    Evidence,
    ResourceReference,
    ResourceType,
)
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.planner.planner import Planner
from workbench.planner.schemas import TaskRequest
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowStatus
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
from workbench.tools.schemas import ToolRequest, ToolResult, ToolResultStatus
from workbench.tools.executor import ToolExecutor
from workbench.security.authorization import AuthorizationPolicy
from workbench.security.audit import AuditRecord, AuditRegistry
from workbench.synthesis.synthesizer import FinalSynthesizer
from workbench.synthesis.reporting import ReportGenerator
from workbench.core.errors import SecurityViolationError, SubsystemExecutionError
from workbench.approval.schemas import ApprovalRequest, ApprovalStatus
from workbench.approval.manager import ApprovalManager


class MockToolExecutor(ToolExecutor):
    """
    Mock implementation of ToolExecutor for integration testing.

    Captures incoming ToolRequests and returns deterministic ToolResults
    (including generated Artifacts and Evidence).
    """

    def __init__(
        self,
        default_status: ToolResultStatus = ToolResultStatus.SUCCESS,
        generated_artifacts: Optional[list[Artifact]] = None,
        generated_evidence: Optional[list[Evidence]] = None,
        should_fail: bool = False,
        fail_tools: Optional[Set[str]] = None,
        authorization_policy: Optional[AuthorizationPolicy] = None,
        audit_registry: Optional[AuditRegistry] = None,
    ) -> None:
        self.default_status = default_status
        self.generated_artifacts = generated_artifacts or []
        self.generated_evidence = generated_evidence or []
        self.should_fail = should_fail
        self.fail_tools = fail_tools or set()
        self.authorization_policy = authorization_policy
        self.audit_registry = audit_registry
        self.received_requests: list[ToolRequest] = []

    def execute_tool(self, request: ToolRequest) -> ToolResult:
        self.received_requests.append(request)

        if self.authorization_policy is not None:
            is_allowed = self.authorization_policy.authorize_action(
                request.request_context,
                action="execute_tool",
                resource_uri=f"tool:{request.tool_name}",
            )
            if self.audit_registry is not None:
                self.audit_registry.record_event(
                    AuditRecord(
                        event_id=f"audit-tool-auth-{request.tool_name}",
                        event_type="authorization_check",
                        request_context=request.request_context,
                        component="security",
                        details={
                            "action": "execute_tool",
                            "resource_uri": f"tool:{request.tool_name}",
                            "allowed": is_allowed,
                        },
                    )
                )
            if not is_allowed:
                return ToolResult(
                    request_context=request.request_context,
                    status=ToolResultStatus.FAILED,
                    output=None,
                    evidence=[],
                    artifacts=[],
                    error=f"Tool execution unauthorized for tool: {request.tool_name}",
                )

        if self.should_fail or request.tool_name in self.fail_tools:
            return ToolResult(
                request_context=request.request_context,
                status=ToolResultStatus.FAILED,
                output=None,
                evidence=[],
                artifacts=[],
                error=f"Tool execution failed for tool: {request.tool_name}",
            )

        artifacts = list(self.generated_artifacts)
        if not artifacts and request.tool_name in {
            "document_generation",
            "spreadsheet_generation",
            "write_file",
        }:
            artifacts = [
                Artifact(
                    artifact_id=f"art-{request.tool_name}-001",
                    task_id=request.request_context.task_id,
                    step_id=request.request_context.step_id,
                    type=ArtifactType.REPORT,
                    name=f"generated_{request.tool_name}.pdf",
                    location=f"outputs/generated_{request.tool_name}.pdf",
                    mime_type="application/pdf",
                    created_by="mock_tool_executor",
                )
            ]

        evidence = list(self.generated_evidence)
        if not evidence:
            evidence = [
                Evidence(
                    evidence_id=f"ev-{request.tool_name}-001",
                    content=f"Tool output payload from {request.tool_name}",
                    location=f"tool_output://{request.tool_name}",
                    evidence_type="tool_execution_output",
                    provenance={"tool_name": request.tool_name},
                    confidence=1.0,
                    confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
                )
            ]

        if self.audit_registry is not None:
            self.audit_registry.record_event(
                AuditRecord(
                    event_id=f"audit-tool-exec-{request.tool_name}",
                    event_type="tool_executed",
                    request_context=request.request_context,
                    component="tools",
                    details={"tool_name": request.tool_name},
                )
            )

        return ToolResult(
            request_context=request.request_context,
            status=self.default_status,
            output={"result": f"Execution successful for {request.tool_name}"},
            evidence=evidence,
            artifacts=artifacts,
            error=None,
        )


class MockModelRegistry(ModelRegistry):
    """
    Mock implementation of ModelRegistry for integration testing.

    Captures all incoming AgentRequests and returns deterministic AgentResults.
    If equipped with a tool_executor, invokes tool execution as part of agent processing.
    """

    def __init__(
        self,
        default_status: AgentResultStatus = AgentResultStatus.SUCCESS,
        failed_objectives: Optional[Set[str]] = None,
        tool_executor: Optional[ToolExecutor] = None,
        tool_to_invoke: Optional[str] = None,
    ) -> None:
        self.default_status = default_status
        self.failed_objectives = failed_objectives or set()
        self.tool_executor = tool_executor
        self.tool_to_invoke = tool_to_invoke
        self.received_requests: list[AgentRequest] = []

    def execute(self, request: AgentRequest) -> AgentResult:
        self.received_requests.append(request)

        status = self.default_status
        if (
            request.objective in self.failed_objectives
            or request.expected_output in self.failed_objectives
        ):
            status = AgentResultStatus.FAILED

        tool_artifacts: list[Artifact] = []
        tool_evidence: list[Evidence] = []
        errors = (
            ["Step execution failed in mock model registry"]
            if status == AgentResultStatus.FAILED
            else []
        )

        if self.tool_executor is not None and status != AgentResultStatus.FAILED:
            tool_req = ToolRequest(
                request_context=request.request_context,
                tool_name=self.tool_to_invoke or "document_generation",
                parameters={"objective": request.objective},
            )
            tool_res = self.tool_executor.execute_tool(tool_req)

            if tool_res.status == ToolResultStatus.FAILED:
                return AgentResult(
                    request_context=request.request_context,
                    status=AgentResultStatus.FAILED,
                    result_evidence=tool_res.evidence,
                    artifacts=tool_res.artifacts,
                    errors=[tool_res.error or "Tool execution failed"],
                    metadata={"mock_execution": True, "tool_status": "FAILED"},
                )

            tool_artifacts = tool_res.artifacts
            tool_evidence = tool_res.evidence

        return AgentResult(
            request_context=request.request_context,
            status=status,
            result_evidence=tool_evidence,
            artifacts=tool_artifacts,
            errors=errors,
            metadata={
                "mock_execution": True,
                "objective": request.objective,
            },
        )


class MockRetriever(Retriever):
    """
    Mock implementation of Retriever for integration testing.

    Captures incoming RetrievalRequests and returns deterministic Evidence/ResourceReferences
    or raises errors when configured to simulate retrieval failure.
    """

    def __init__(
        self,
        retrieved_resources: Optional[list[ResourceReference]] = None,
        should_fail: bool = False,
        fail_queries: Optional[Set[str]] = None,
    ) -> None:
        self.retrieved_resources = retrieved_resources or []
        self.should_fail = should_fail
        self.fail_queries = fail_queries or set()
        self.received_requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.received_requests.append(request)

        if self.should_fail or request.query in self.fail_queries:
            raise RuntimeError(f"Mock retrieval error for query: '{request.query}'")

        evidence_list: list[Evidence] = []
        for i, res in enumerate(self.retrieved_resources):
            evidence_list.append(
                Evidence(
                    evidence_id=f"retrieved-ev-{i+1}",
                    content=res,
                    location=res.uri_or_path,
                    evidence_type="retrieved_document",
                    provenance=res.provenance,
                    confidence=0.9,
                    confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
                )
            )

        return RetrievalResult(
            request_context=request.request_context,
            results=evidence_list,
            query=request.query,
            total_hits=len(evidence_list),
        )


class MockMultimodalProcessor(MultimodalProcessor):
    """
    Mock implementation of MultimodalProcessor for integration testing.

    Captures incoming MultimodalRequests and returns deterministic MultimodalResults.
    """

    def __init__(
        self,
        default_status: MultimodalStatus = MultimodalStatus.SUCCESS,
        extracted_evidence: Optional[list[Evidence]] = None,
        should_fail: bool = False,
        fail_resource_ids: Optional[Set[str]] = None,
    ) -> None:
        self.default_status = default_status
        self.extracted_evidence = extracted_evidence or []
        self.should_fail = should_fail
        self.fail_resource_ids = fail_resource_ids or set()
        self.received_requests: list[MultimodalRequest] = []

    def process(self, request: MultimodalRequest) -> MultimodalResult:
        self.received_requests.append(request)

        if self.should_fail or request.resource.resource_id in self.fail_resource_ids:
            return MultimodalResult(
                request_context=request.request_context,
                status=MultimodalStatus.FAILED,
                evidence=[],
                artifacts=[],
                errors=[
                    f"Multimodal processing failed for resource: {request.resource.resource_id}"
                ],
            )

        evidence_list = list(self.extracted_evidence)
        if not evidence_list:
            evidence_list = [
                Evidence(
                    evidence_id=f"mm-ev-{request.resource.resource_id}",
                    content=f"Multimodal parsed content for {request.resource.resource_id}",
                    location="page 1",
                    evidence_type="ocr_text",
                    provenance={"processor": "mock_multimodal"},
                    confidence=0.95,
                    confidence_source=ConfidenceSource.OCR_ENGINE,
                )
            ]

        return MultimodalResult(
            request_context=request.request_context,
            status=self.default_status,
            evidence=evidence_list,
            artifacts=[],
            errors=[],
            metadata={"mock": True},
        )


def create_context(task_id: str = "task-e2e-001") -> RequestContext:
    return RequestContext(
        request_id="req-e2e-001",
        task_id=task_id,
        user_id="arch-user",
        source_component="integration_test",
    )


def create_generic_task_request() -> TaskRequest:
    context = create_context("task-generic")
    resource = ResourceReference(
        resource_id="res-pipeline-data",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/sample/pipeline_specs.json",
        provenance={"source": "user_upload"},
    )
    return TaskRequest(
        request_context=context,
        user_input="Calculate the pressure drop across the pipeline.",
        resources=[resource],
        requested_output_info={
            "format": "json",
            "description": "Pressure drop calculation results.",
        },
    )


def create_inspection_task_request() -> TaskRequest:
    context = create_context("task-inspection")
    resource = ResourceReference(
        resource_id="res-inspection-doc",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="data/demo/inspection_report.pdf",
        provenance={"source": "user_upload"},
    )
    return TaskRequest(
        request_context=context,
        user_input=(
            "Analyze the inspection report, identify safety findings, "
            "determine applicable SOP requirements, review previous incidents, "
            "recommend corrective actions, and prepare an approval proposal."
        ),
        resources=[resource],
        requested_output_info={
            "format": "docx",
            "description": "Corrective-action proposal for approval.",
        },
    )


def test_generic_task_single_step_end_to_end():
    """
    TEST 1:
    Generic TaskRequest -> Planner -> single-step ExecutionPlan -> WorkflowEngine
    -> MockModelRegistry -> step PASSED.
    """
    planner = Planner()
    mock_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    assert len(plan.executable_steps) == 1
    step_1_id = plan.executable_steps[0].step_id

    state = engine.execute_plan(plan)
    assert state.status == WorkflowStatus.RUNNING
    assert state.step_statuses[step_1_id] == StepStatus.READY

    state = engine.execute_next_step(plan, state)
    assert state.step_statuses[step_1_id] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED
    assert step_1_id in state.step_results
    assert state.step_results[step_1_id].status == AgentResultStatus.SUCCESS
    assert len(mock_registry.received_requests) == 1


def test_inspection_task_dag_all_steps_pass():
    """
    TEST 2:
    Inspection TaskRequest -> Planner -> six-step DAG -> WorkflowEngine
    -> repeated execution of ready steps -> all executable steps eventually PASSED.
    """
    planner = Planner()
    mock_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    assert len(plan.executable_steps) == 6

    state = engine.execute_plan(plan)
    assert state.status == WorkflowStatus.RUNNING

    executions = 0
    max_executions = 20
    while executions < max_executions:
        ready_steps = [
            s_id for s_id, status in state.step_statuses.items()
            if status == StepStatus.READY
        ]
        if not ready_steps:
            break
        state = engine.execute_next_step(plan, state)
        executions += 1

    assert len(mock_registry.received_requests) == 6
    assert state.status == WorkflowStatus.COMPLETED
    for step in plan.executable_steps:
        assert state.step_statuses[step.step_id] == StepStatus.PASSED
        assert step.step_id in state.step_results


def test_dependency_step_readiness_transitions():
    """
    TEST 3:
    Dependency behavior:
    - step-1 and step-2 initially READY
    - step-3 initially PENDING
    - after step-1 and step-2 pass, step-3 becomes READY
    - continue until final step passes
    """
    planner = Planner()
    mock_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    # Initially step-1, step-2, step-4 are READY (0 dependencies)
    # step-3 depends on step-1 and step-2, so it must be PENDING
    assert state.step_statuses["step-1"] == StepStatus.READY
    assert state.step_statuses["step-2"] == StepStatus.READY
    assert state.step_statuses["step-3"] == StepStatus.PENDING
    assert state.step_statuses["step-4"] == StepStatus.READY

    # Execute step-1
    state = engine.execute_next_step(plan, state)
    assert state.step_statuses["step-1"] == StepStatus.PASSED
    assert state.step_statuses["step-2"] == StepStatus.READY
    assert state.step_statuses["step-3"] == StepStatus.PENDING  # Still waiting for step-2

    # Execute step-2
    state = engine.execute_next_step(plan, state)
    assert state.step_statuses["step-2"] == StepStatus.PASSED
    # Now that step-1 AND step-2 passed, step-3 becomes READY!
    assert state.step_statuses["step-3"] == StepStatus.READY

    # Continue execution until all steps pass
    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED
    for step in plan.executable_steps:
        assert state.step_statuses[step.step_id] == StepStatus.PASSED


def test_failure_behavior_blocks_dependent_steps():
    """
    TEST 4:
    Failure behavior:
    - MockModelRegistry returns FAILED for a selected step (e.g. step-3)
    - Workflow Engine records FAILED
    - dependent steps do NOT become READY
    """
    planner = Planner()
    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    step_3 = next(s for s in plan.executable_steps if s.step_id == "step-3")

    mock_registry = MockModelRegistry(
        failed_objectives={step_3.objective}
    )
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)

    # Execute step-1 (passes)
    state = engine.execute_next_step(plan, state)
    assert state.step_statuses["step-1"] == StepStatus.PASSED

    # Execute step-2 (passes, step-3 becomes READY)
    state = engine.execute_next_step(plan, state)
    assert state.step_statuses["step-2"] == StepStatus.PASSED
    assert state.step_statuses["step-3"] == StepStatus.READY

    # Execute step-3 (fails!)
    state = engine.execute_next_step(plan, state)
    assert state.step_statuses["step-3"] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED

    # Dependent step-5 (depends on step-3 and step-4) must remain PENDING
    assert state.step_statuses["step-5"] == StepStatus.PENDING
    assert state.step_statuses["step-6"] == StepStatus.PENDING

    # Attempting to execute next step on FAILED workflow does nothing (terminal state safety)
    requests_before = len(mock_registry.received_requests)
    state = engine.execute_next_step(plan, state)
    assert len(mock_registry.received_requests) == requests_before
    assert state.status == WorkflowStatus.FAILED
    assert state.step_statuses["step-5"] == StepStatus.PENDING
    assert state.step_statuses["step-6"] == StepStatus.PENDING


def test_contract_propagation():
    """
    TEST 5:
    Contract propagation:
    Capture AgentRequests received by MockModelRegistry and verify:
    - request_context matches expected context
    - objective matches ExecutionStep.objective
    - resources match ExecutionStep.resources
    - expected_output matches ExecutionStep.expected_output
    """
    planner = Planner()
    mock_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_registry,
        step_validator=StepValidator(),
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    # Execute all steps
    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert len(mock_registry.received_requests) == len(plan.executable_steps)
    assert state.status == WorkflowStatus.COMPLETED

    for agent_req in mock_registry.received_requests:
        matched_step = next(
            s for s in plan.executable_steps if s.objective == agent_req.objective
        )
        assert agent_req.request_context == plan.request_context
        assert agent_req.objective == matched_step.objective
        assert agent_req.context_resources == matched_step.resources
        assert agent_req.expected_output == matched_step.expected_output


# ---------------------------------------------------------------------------
# Retrieval Integration Tests
# ---------------------------------------------------------------------------

def test_retrieval_success_integration():
    """
    TEST 1: RETRIEVAL SUCCESS
    Given a task requiring company knowledge:
    TaskRequest -> Planner -> WorkflowEngine -> MockRetrieval
    MockRetrieval returns two ResourceReferences.
    Verify:
    - retrieval is invoked
    - returned resources reach AgentRequest.context_resources
    - ModelRegistry receives the AgentRequest
    - step passes
    - workflow eventually completes
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()

    res_1 = ResourceReference(
        resource_id="kb-sop-101",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_101.pdf",
        provenance={"source": "vector_db"},
    )
    res_2 = ResourceReference(
        resource_id="kb-incident-402",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/incident_402.pdf",
        provenance={"source": "vector_db"},
    )
    mock_retriever = MockRetriever(retrieved_resources=[res_1, res_2])

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    # Verify retrieval was invoked
    assert len(mock_retriever.received_requests) == 1
    assert mock_retriever.received_requests[0].query == plan.executable_steps[0].objective

    # Verify returned resources reach AgentRequest.context_resources
    assert len(mock_model_registry.received_requests) == 1
    agent_req = mock_model_registry.received_requests[0]
    resource_ids = [r.resource_id for r in agent_req.context_resources]
    assert "kb-sop-101" in resource_ids
    assert "kb-incident-402" in resource_ids

    # Verify step passes & workflow completes
    assert state.step_statuses[plan.executable_steps[0].step_id] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED


def test_retrieval_resource_merging_integration():
    """
    TEST 2: RESOURCE MERGING
    If a step already has resources supplied by the TaskRequest and Retrieval returns additional resources:
    Verify:
    - original resources remain
    - retrieved resources are added
    - no resources are silently overwritten
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-retrieved-001",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/kb_doc.pdf",
        provenance={"source": "vector_index"},
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)
    original_resource_id = request.resources[0].resource_id

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    agent_req = mock_model_registry.received_requests[0]
    context_resource_ids = [r.resource_id for r in agent_req.context_resources]

    # Verify original resource is still present
    assert original_resource_id in context_resource_ids
    # Verify retrieved resource is added
    assert "kb-retrieved-001" in context_resource_ids
    # Total count = 1 original + 1 retrieved = 2
    assert len(agent_req.context_resources) == 2


def test_retrieval_failure_integration():
    """
    TEST 3: RETRIEVAL FAILURE
    MockRetrieval simulates failure.
    Verify:
    - step status is FAILED
    - workflow status is FAILED
    - workflow does not silently proceed as though retrieval succeeded
    - ModelRegistry is NOT invoked for the failed step
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_retriever = MockRetriever(should_fail=True)

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    step_id = plan.executable_steps[0].step_id

    assert state.step_statuses[step_id] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED
    assert len(mock_model_registry.received_requests) == 0


def test_retrieval_context_propagation_integration():
    """
    TEST 4: CONTEXT PROPAGATION
    Verify:
    - RequestContext remains unchanged through retrieval and model execution
    - task_id, request_id, user_id remain unchanged
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_retriever = MockRetriever()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    retrieval_req = mock_retriever.received_requests[0]
    agent_req = mock_model_registry.received_requests[0]

    assert retrieval_req.request_context.task_id == request.request_context.task_id
    assert retrieval_req.request_context.request_id == request.request_context.request_id
    assert retrieval_req.request_context.user_id == request.request_context.user_id

    assert agent_req.request_context.task_id == request.request_context.task_id
    assert agent_req.request_context.request_id == request.request_context.request_id
    assert agent_req.request_context.user_id == request.request_context.user_id


def test_retrieval_multi_step_dag_integration():
    """
    TEST 5: MULTI-STEP BEHAVIOR
    For the inspection six-step plan, verify that retrieval provides resources
    for each step and that those resources reach the Model Registry without breaking dependency scheduling.
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()

    sop_res = ResourceReference(
        resource_id="kb-sop-standard",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_standard.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[sop_res])

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert len(mock_retriever.received_requests) == 6
    assert len(mock_model_registry.received_requests) == 6
    assert state.status == WorkflowStatus.COMPLETED

    for agent_req in mock_model_registry.received_requests:
        res_ids = [r.resource_id for r in agent_req.context_resources]
        assert "kb-sop-standard" in res_ids


# ---------------------------------------------------------------------------
# Multimodal Integration Tests
# ---------------------------------------------------------------------------

def test_multimodal_success_integration():
    """
    TEST 1: MULTIMODAL SUCCESS
    Given a step with a multimodal resource:
    WorkflowEngine -> MockMultimodal -> structured evidence -> MockModelRegistry
    Verify:
    - Multimodal is invoked
    - result is returned and reaches model execution context
    - AgentRequest is correctly constructed
    - step passes & workflow completes
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_multimodal = MockMultimodalProcessor()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        multimodal_processor=mock_multimodal,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    # Verify multimodal was invoked
    assert len(mock_multimodal.received_requests) == 1
    assert (
        mock_multimodal.received_requests[0].resource.resource_id
        == request.resources[0].resource_id
    )

    # Verify multimodal result reaches AgentRequest.context_resources
    assert len(mock_model_registry.received_requests) == 1
    agent_req = mock_model_registry.received_requests[0]
    res_ids = [r.resource_id for r in agent_req.context_resources]
    assert f"mm-ev-{request.resources[0].resource_id}" in res_ids

    # Verify step passes & workflow completes
    step_id = plan.executable_steps[0].step_id
    assert state.step_statuses[step_id] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED


def test_multimodal_and_retrieval_combined_integration():
    """
    TEST 2: MULTIMODAL + RETRIEVAL
    A step has:
    - original resource
    - retrieved resource
    - multimodal resource/result
    Verify all relevant context reaches the model without overwriting one another.
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-retrieved-999",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/kb_doc.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    agent_req = mock_model_registry.received_requests[0]
    res_ids = [r.resource_id for r in agent_req.context_resources]

    # Verify original resource is present
    assert request.resources[0].resource_id in res_ids
    # Verify retrieved resource is present
    assert "kb-retrieved-999" in res_ids
    # Verify multimodal evidence for resources is present
    assert f"mm-ev-{request.resources[0].resource_id}" in res_ids
    assert "mm-ev-kb-retrieved-999" in res_ids
    # Verify no resources were overwritten
    assert len(agent_req.context_resources) == 4


def test_multimodal_failure_integration():
    """
    TEST 3: MULTIMODAL FAILURE
    MockMultimodal simulates failure.
    Verify:
    - failure is not silently ignored
    - step status becomes FAILED
    - workflow status becomes FAILED
    - Model Registry is not called
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_multimodal = MockMultimodalProcessor(should_fail=True)

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        multimodal_processor=mock_multimodal,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    step_id = plan.executable_steps[0].step_id

    assert state.step_statuses[step_id] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED
    assert len(mock_model_registry.received_requests) == 0


def test_multimodal_context_propagation_integration():
    """
    TEST 4: CONTEXT PROPAGATION
    Verify RequestContext remains unchanged through WorkflowEngine -> Multimodal -> ModelRegistry
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_multimodal = MockMultimodalProcessor()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        multimodal_processor=mock_multimodal,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    mm_req = mock_multimodal.received_requests[0]
    agent_req = mock_model_registry.received_requests[0]

    assert mm_req.request_context.task_id == request.request_context.task_id
    assert mm_req.request_context.request_id == request.request_context.request_id
    assert mm_req.request_context.user_id == request.request_context.user_id

    assert agent_req.request_context.task_id == request.request_context.task_id
    assert agent_req.request_context.request_id == request.request_context.request_id
    assert agent_req.request_context.user_id == request.request_context.user_id


def test_multimodal_multi_step_dag_integration():
    """
    TEST 5: MULTI-STEP / DAG
    For the inspection workflow, verify multimodal processing occurs for a step without breaking dependency scheduling.
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_multimodal = MockMultimodalProcessor()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        multimodal_processor=mock_multimodal,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert len(mock_multimodal.received_requests) >= 6
    assert len(mock_model_registry.received_requests) == 6
    assert state.status == WorkflowStatus.COMPLETED

    for step in plan.executable_steps:
        assert state.step_statuses[step.step_id] == StepStatus.PASSED


# ---------------------------------------------------------------------------
# Tool Subsystem Integration Tests
# ---------------------------------------------------------------------------

def test_tool_success_integration():
    """
    TEST 1: TOOL SUCCESS
    A mock agent/model requests a deterministic mock tool.
    Verify:
    - Tool System receives the request through established boundary
    - Tool executes successfully and ToolResult is returned
    - Generated artifact/evidence is preserved
    - Workflow step completes successfully
    """
    planner = Planner()
    mock_tool_executor = MockToolExecutor()
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    step_id = plan.executable_steps[0].step_id

    # Verify Tool System received the request
    assert len(mock_tool_executor.received_requests) == 1
    assert mock_tool_executor.received_requests[0].tool_name == "document_generation"

    # Verify step passes & workflow completes
    assert state.step_statuses[step_id] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED

    # Verify artifact & evidence preserved in step results/artifacts
    assert step_id in state.step_artifacts
    assert len(state.step_artifacts[step_id]) == 1
    assert state.step_artifacts[step_id][0].artifact_id == "art-document_generation-001"


def test_tool_failure_integration():
    """
    TEST 2: TOOL FAILURE
    Mock Tool System returns a failure.
    Verify:
    - Failure is not silently ignored
    - Agent/workflow receives the failure
    - Step does not falsely become successful
    - Workflow transitions to FAILED state
    """
    planner = Planner()
    mock_tool_executor = MockToolExecutor(should_fail=True)
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    step_id = plan.executable_steps[0].step_id

    # Verify tool execution occurred and failed
    assert len(mock_tool_executor.received_requests) == 1
    assert state.step_statuses[step_id] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED


def test_tool_artifact_propagation_integration():
    """
    TEST 3: ARTIFACT PROPAGATION
    If the tool generates an Artifact:
    Verify:
    - Artifact is preserved in WorkflowState.step_artifacts
    - task_id and step_id match correctly
    - Artifact metadata, location, type are not silently lost
    """
    planner = Planner()
    custom_artifact = Artifact(
        artifact_id="art-custom-report-999",
        task_id="task-generic",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="custom_report.pdf",
        location="outputs/custom_report.pdf",
        mime_type="application/pdf",
        created_by="mock_tool_executor",
        source_information={"tool": "document_generation"},
        metadata={"author": "test_engineer"},
    )
    mock_tool_executor = MockToolExecutor(generated_artifacts=[custom_artifact])
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    step_id = plan.executable_steps[0].step_id
    artifacts = state.step_artifacts[step_id]

    assert len(artifacts) == 1
    art = artifacts[0]
    assert art.artifact_id == "art-custom-report-999"
    assert art.task_id == "task-generic"
    assert art.type == ArtifactType.REPORT
    assert art.location == "outputs/custom_report.pdf"
    assert art.metadata == {"author": "test_engineer"}


def test_tool_context_propagation_integration():
    """
    TEST 4: CONTEXT PROPAGATION
    Verify RequestContext remains correctly associated across:
    WorkflowEngine -> Agent execution -> Tool System -> ToolResult -> AgentResult -> WorkflowState
    """
    planner = Planner()
    mock_tool_executor = MockToolExecutor()
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    tool_req = mock_tool_executor.received_requests[0]
    agent_req = mock_model_registry.received_requests[0]

    assert tool_req.request_context.task_id == request.request_context.task_id
    assert tool_req.request_context.request_id == request.request_context.request_id
    assert tool_req.request_context.user_id == request.request_context.user_id

    assert agent_req.request_context.task_id == request.request_context.task_id
    assert agent_req.request_context.request_id == request.request_context.request_id
    assert agent_req.request_context.user_id == request.request_context.user_id


def test_combined_all_subsystems_integration():
    """
    TEST 5: TOOL + RETRIEVAL + MULTIMODAL COMBINED
    Combines:
    Task -> Planner -> WorkflowEngine -> Retrieval -> Multimodal -> Agent execution -> Tool System -> AgentResult -> WorkflowState
    Verify that all subsystem outputs coexist as execution context/artifacts.
    """
    planner = Planner()

    retrieved_res = ResourceReference(
        resource_id="kb-sop-inspection",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_inspection.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()

    tool_artifact = Artifact(
        artifact_id="art-inspection-summary-001",
        task_id="task-inspection",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="inspection_summary.pdf",
        location="outputs/inspection_summary.pdf",
        mime_type="application/pdf",
        created_by="tool_system",
    )
    mock_tool_executor = MockToolExecutor(generated_artifacts=[tool_artifact])
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    # Verify retrieval, multimodal, tool executor, and model registry were all invoked for each step
    assert len(mock_retriever.received_requests) == 6
    assert len(mock_multimodal.received_requests) >= 6
    assert len(mock_tool_executor.received_requests) == 6
    assert len(mock_model_registry.received_requests) == 6

    # Verify workflow completed
    assert state.status == WorkflowStatus.COMPLETED

    # Verify artifacts generated by tool execution are captured in workflow state
    assert len(state.step_artifacts["step-1"]) >= 1
    assert state.step_artifacts["step-1"][0].artifact_id == "art-inspection-summary-001"


# ---------------------------------------------------------------------------
# Security & Audit Integration Tests
# ---------------------------------------------------------------------------

class MockAuthorizationPolicy(AuthorizationPolicy):
    """
    Mock implementation of AuthorizationPolicy for integration testing.
    """

    def __init__(
        self,
        default_allow: bool = True,
        denied_actions: Optional[Set[str]] = None,
        denied_resources: Optional[Set[str]] = None,
    ) -> None:
        self.default_allow = default_allow
        self.denied_actions = denied_actions or set()
        self.denied_resources = denied_resources or set()
        self.checks: list[dict[str, str]] = []

    def authorize_action(
        self, context: RequestContext, action: str, resource_uri: str
    ) -> bool:
        self.checks.append(
            {"action": action, "resource_uri": resource_uri, "task_id": context.task_id}
        )
        if action in self.denied_actions or resource_uri in self.denied_resources:
            return False
        return self.default_allow


class MockAuditRegistry(AuditRegistry):
    """
    Mock implementation of AuditRegistry for integration testing.
    """

    def __init__(self) -> None:
        self.recorded_events: list[AuditRecord] = []

    def record_event(self, record: AuditRecord) -> None:
        self.recorded_events.append(record)


def test_authorized_execution_integration():
    """
    TEST 1: AUTHORIZED EXECUTION & AUDIT
    Workflow execution with MockAuthorizationPolicy (ALLOW) and MockAuditRegistry.
    Verify:
    - Step executes successfully
    - Authorization check is performed
    - Audit records are generated for key events (workflow_started, authorization_check, step_started, model_executed, step_completed, workflow_completed)
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_auth = MockAuthorizationPolicy(default_allow=True)
    mock_audit = MockAuditRegistry()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    # Verify authorization check occurred
    assert len(mock_auth.checks) == 1
    assert mock_auth.checks[0]["action"] == "execute_step"
    assert mock_auth.checks[0]["resource_uri"] == f"step:{plan.executable_steps[0].step_id}"

    # Verify step passes & workflow completes
    assert state.step_statuses[plan.executable_steps[0].step_id] == StepStatus.PASSED
    assert state.status == WorkflowStatus.COMPLETED

    # Verify audit records capture key events
    event_types = [rec.event_type for rec in mock_audit.recorded_events]
    assert "workflow_started" in event_types
    assert "authorization_check" in event_types
    assert "step_started" in event_types
    assert "model_executed" in event_types
    assert "step_completed" in event_types
    assert "workflow_completed" in event_types


def test_authorization_denial_integration():
    """
    TEST 2: AUTHORIZATION DENIAL
    MockAuthorizationPolicy configured to DENY step execution.
    Verify:
    - Authorization check yields DENY
    - Step transitions to FAILED
    - Workflow transitions to FAILED
    - ModelRegistry is NOT invoked
    - Audit records capture authorization_denied and workflow_failed
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    request = create_generic_task_request()
    plan = planner.create_plan(request)
    step_id = plan.executable_steps[0].step_id

    mock_auth = MockAuthorizationPolicy(
        denied_resources={f"step:{step_id}"}
    )
    mock_audit = MockAuditRegistry()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    # Verify step and workflow failed
    assert state.step_statuses[step_id] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED

    # Verify ModelRegistry was never called
    assert len(mock_model_registry.received_requests) == 0

    # Verify audit records contain denial and failure
    event_types = [rec.event_type for rec in mock_audit.recorded_events]
    assert "authorization_check" in event_types
    assert "authorization_denied" in event_types
    assert "workflow_failed" in event_types


def test_audit_successful_workflow_integration():
    """
    TEST 3: AUDIT RECORDING ON SUCCESSFUL MULTI-STEP WORKFLOW
    Execute a multi-step inspection plan with MockAuditRegistry.
    Verify:
    - Every step records step_started, model_executed, step_completed
    - Workflow start and completion events are recorded
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_audit = MockAuditRegistry()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        audit_registry=mock_audit,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    event_types = [rec.event_type for rec in mock_audit.recorded_events]
    assert event_types[0] == "workflow_started"
    assert event_types[-1] == "workflow_completed"
    assert event_types.count("step_started") == 6
    assert event_types.count("model_executed") == 6
    assert event_types.count("step_completed") == 6


def test_audit_failed_workflow_integration():
    """
    TEST 4: AUDIT RECORDING ON FAILED WORKFLOW
    When step execution fails in ModelRegistry, verify audit records capture step_failed and workflow_failed.
    """
    planner = Planner()
    request = create_generic_task_request()
    plan = planner.create_plan(request)

    mock_model_registry = MockModelRegistry(
        failed_objectives={plan.executable_steps[0].objective}
    )
    mock_audit = MockAuditRegistry()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        audit_registry=mock_audit,
    )

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.FAILED

    event_types = [rec.event_type for rec in mock_audit.recorded_events]
    assert "step_failed" in event_types
    assert "workflow_failed" in event_types


def test_request_task_step_correlation_integration():
    """
    TEST 5: CONTEXT CORRELATION IN AUDIT RECORDS
    Verify that all recorded audit events carry the matching task_id and request_id from RequestContext.
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    mock_auth = MockAuthorizationPolicy()
    mock_audit = MockAuditRegistry()

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    for rec in mock_audit.recorded_events:
        assert rec.request_context.task_id == request.request_context.task_id
        assert rec.request_context.request_id == request.request_context.request_id
        assert rec.request_context.user_id == request.request_context.user_id


def test_tool_authorization_integration():
    """
    TEST 6: TOOL LEVEL AUTHORIZATION
    ToolExecutor checks AuthorizationPolicy before running a tool. If denied, tool fails cleanly, model execution fails, step fails.
    """
    planner = Planner()
    mock_auth = MockAuthorizationPolicy(
        denied_resources={"tool:document_generation"}
    )
    mock_audit = MockAuditRegistry()

    mock_tool_executor = MockToolExecutor(
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.step_statuses[plan.executable_steps[0].step_id] == StepStatus.FAILED
    assert state.status == WorkflowStatus.FAILED

    # Check tool auth denial recorded in audit registry
    audit_denials = [
        rec for rec in mock_audit.recorded_events
        if rec.event_type == "authorization_check" and rec.details.get("resource_uri") == "tool:document_generation"
    ]
    assert len(audit_denials) == 1
    assert audit_denials[0].details["allowed"] is False


def test_full_multi_subsystem_authorized_pipeline():
    """
    TEST 7: FULL PIPELINE WITH ALL SUBSYSTEMS + SECURITY & AUDIT
    Pipeline: Task -> Planner -> WorkflowEngine (Retriever, Multimodal, ModelRegistry, ToolExecutor, AuthorizationPolicy, AuditRegistry).
    Verify all audit events generated across all subsystems co-exist correctly in the AuditRegistry.
    """
    planner = Planner()

    mock_auth = MockAuthorizationPolicy(default_allow=True)
    mock_audit = MockAuditRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-sop-full",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_full.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()

    tool_artifact = Artifact(
        artifact_id="art-full-001",
        task_id="task-inspection",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="full_report.pdf",
        location="outputs/full_report.pdf",
        mime_type="application/pdf",
        created_by="tool_system",
    )
    mock_tool_executor = MockToolExecutor(
        generated_artifacts=[tool_artifact],
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    event_types = set(rec.event_type for rec in mock_audit.recorded_events)
    assert "workflow_started" in event_types
    assert "authorization_check" in event_types
    assert "step_started" in event_types
    assert "retrieval_executed" in event_types
    assert "multimodal_executed" in event_types
    assert "model_executed" in event_types
    assert "tool_executed" in event_types
    assert "step_completed" in event_types
    assert "workflow_completed" in event_types


def test_denied_full_pipeline_integration():
    """
    TEST 8: FULL PIPELINE EARLY DENIAL SAFETY
    If step execution is denied by AuthorizationPolicy in full pipeline:
    Verify that retrieval, multimodal, model execution, and tool execution do NOT run.
    """
    planner = Planner()

    mock_auth = MockAuthorizationPolicy(
        denied_resources={"step:step-1"}
    )
    mock_audit = MockAuditRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-sop-full",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_full.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()
    mock_tool_executor = MockToolExecutor(
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.FAILED
    assert state.step_statuses["step-1"] == StepStatus.FAILED

    # Verify no downstream component was invoked for step-1
    assert len(mock_retriever.received_requests) == 0
    assert len(mock_multimodal.received_requests) == 0
    assert len(mock_model_registry.received_requests) == 0
    assert len(mock_tool_executor.received_requests) == 0


# ---------------------------------------------------------------------------
# Final Synthesis & Reporting Integration Tests
# ---------------------------------------------------------------------------

def test_successful_final_synthesis_and_reporting_integration():
    """
    PART E (1) & PART F: SUCCESSFUL SYNTHESIS & REPORTING
    Given a completed workflow:
    - FinalSynthesizer invokes ModelRegistry boundary
    - ReportGenerator produces final Artifact deliverable
    - RequestContext and artifact metadata are preserved
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)
    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    synthesizer = FinalSynthesizer(model_registry=mock_model_registry)
    synthesized_content = synthesizer.synthesize_deliverable(request, state)

    assert synthesized_content["status"] == "SUCCESS"
    assert synthesized_content["task_id"] == request.request_context.task_id
    assert "synthesized_text" in synthesized_content

    reporter = ReportGenerator()
    report_artifact = reporter.generate_report(synthesized_content)

    assert isinstance(report_artifact, Artifact)
    assert report_artifact.artifact_id == f"art-final-report-{request.request_context.task_id}"
    assert report_artifact.task_id == request.request_context.task_id
    assert report_artifact.type == ArtifactType.REPORT
    assert report_artifact.created_by == "synthesis_reporting"
    assert report_artifact.metadata["request_id"] == request.request_context.request_id
    assert report_artifact.metadata["user_id"] == request.request_context.user_id


def test_synthesis_failure_handling_integration():
    """
    PART E (2): SYNTHESIS FAILURE
    ModelRegistry returns FAILED during synthesis request.
    - FinalSynthesizer returns a FAILED synthesis dict
    - ReportGenerator raises SubsystemExecutionError
    - No successful deliverable artifact is claimed
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)
    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    # Configure mock registry to fail synthesis objective
    synthesis_objective = (
        f"Synthesize final deliverable for task: '{request.user_input}'. "
        f"Requested format/info: {request.requested_output_info}"
    )
    failing_model_registry = MockModelRegistry(
        failed_objectives={synthesis_objective}
    )

    synthesizer = FinalSynthesizer(model_registry=failing_model_registry)
    synthesized_content = synthesizer.synthesize_deliverable(request, state)

    assert synthesized_content["status"] == "FAILED"
    assert len(synthesized_content["errors"]) > 0

    reporter = ReportGenerator()
    with pytest.raises(SubsystemExecutionError) as exc_info:
        reporter.generate_report(synthesized_content)

    assert "Cannot generate report from failed synthesis" in str(exc_info.value)


def test_reporting_failure_handling_integration():
    """
    PART E (3): REPORTING FAILURE
    Synthesis succeeds, but ReportGenerator encounters an internal failure.
    - SubsystemExecutionError is raised
    - No successful deliverable claimed
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_generic_task_request()
    plan = planner.create_plan(request)
    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    synthesizer = FinalSynthesizer(model_registry=mock_model_registry)
    synthesized_content = synthesizer.synthesize_deliverable(request, state)

    failing_reporter = ReportGenerator(should_fail=True)
    with pytest.raises(SubsystemExecutionError) as exc_info:
        failing_reporter.generate_report(synthesized_content)

    assert "Report generation failed" in str(exc_info.value)


def test_synthesis_blocked_on_running_workflow():
    """
    PART E (4) & PART D: INCOMPLETE WORKFLOW
    Workflow is still RUNNING.
    - FinalSynthesizer raises ValueError
    - Final synthesis must not run on incomplete workflow
    """
    planner = Planner()
    mock_model_registry = MockModelRegistry()
    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)
    state = engine.execute_plan(plan)

    assert state.status == WorkflowStatus.RUNNING

    synthesizer = FinalSynthesizer(model_registry=mock_model_registry)
    with pytest.raises(ValueError) as exc_info:
        synthesizer.synthesize_deliverable(request, state)

    assert "Cannot synthesize deliverable for workflow with status 'RUNNING'" in str(exc_info.value)


def test_synthesis_blocked_on_failed_workflow():
    """
    PART E (5) & PART D: FAILED WORKFLOW
    Workflow has status FAILED.
    - FinalSynthesizer raises ValueError
    - Final synthesis must not run on failed workflow
    """
    planner = Planner()
    request = create_generic_task_request()
    plan = planner.create_plan(request)

    step_1 = plan.executable_steps[0]
    failing_registry = MockModelRegistry(failed_objectives={step_1.objective})
    engine = WorkflowEngine(
        model_registry=failing_registry,
        step_validator=StepValidator(),
    )

    state = engine.execute_plan(plan)
    state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.FAILED

    synthesizer = FinalSynthesizer(model_registry=failing_registry)
    with pytest.raises(ValueError) as exc_info:
        synthesizer.synthesize_deliverable(request, state)

    assert "Cannot synthesize deliverable for workflow with status 'FAILED'" in str(exc_info.value)


def test_full_pipeline_to_final_deliverable_integration():
    """
    PART G: FULL END-TO-END PIPELINE INTEGRATION
    TaskRequest
    → Planner
    → ExecutionPlan
    → WorkflowEngine
    → Retrieval
    → Multimodal
    → ModelRegistry
    → Tools
    → AgentResult
    → WorkflowState(COMPLETED)
    → FinalSynthesizer
    → ModelRegistry
    → ReportGenerator
    → Final Deliverable Artifact
    """
    planner = Planner()
    mock_auth = MockAuthorizationPolicy(default_allow=True)
    mock_audit = MockAuditRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-sop-inspection-final",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_inspection_final.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()

    tool_artifact = Artifact(
        artifact_id="art-inspection-summary-final",
        task_id="task-inspection",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="inspection_summary_final.pdf",
        location="outputs/inspection_summary_final.pdf",
        mime_type="application/pdf",
        created_by="tool_system",
    )
    mock_tool_executor = MockToolExecutor(
        generated_artifacts=[tool_artifact],
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    synthesizer = FinalSynthesizer(model_registry=mock_model_registry)
    synthesized_content = synthesizer.synthesize_deliverable(request, state)

    assert synthesized_content["status"] == "SUCCESS"
    assert synthesized_content["step_results_count"] == 6
    assert synthesized_content["context_resources_count"] > 0

    reporter = ReportGenerator()
    final_deliverable = reporter.generate_report(synthesized_content)

    assert isinstance(final_deliverable, Artifact)
    assert final_deliverable.task_id == request.request_context.task_id
    assert final_deliverable.artifact_id == f"art-final-report-{request.request_context.task_id}"
    assert final_deliverable.type == ArtifactType.REPORT
    assert final_deliverable.created_by == "synthesis_reporting"
    assert final_deliverable.metadata["request_id"] == request.request_context.request_id
    assert final_deliverable.metadata["user_id"] == request.request_context.user_id
    assert final_deliverable.metadata["step_results_count"] == 6


# ---------------------------------------------------------------------------
# Human Approval Integration Tests
# ---------------------------------------------------------------------------

def test_deliverable_creates_approval_request():
    """
    PART G (1): Deliverable creates an approval request.
    """
    context = create_context("task-appr-001a")
    artifact = Artifact(
        artifact_id="art-deliverable-001a",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)

    assert isinstance(req, ApprovalRequest)
    assert req.deliverable.artifact_id == "art-deliverable-001a"
    assert req.request_context.task_id == context.task_id


def test_approval_request_starts_undecided():
    """
    PART G (2): Approval request starts undecided (PROPOSED).
    """
    context = create_context("task-appr-001b")
    artifact = Artifact(
        artifact_id="art-deliverable-001b",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)

    assert req.status == ApprovalStatus.PROPOSED
    assert req.reviewer_id is None
    assert req.decided_at is None


def test_explicit_approval_changes_status():
    """
    PART G (3): Explicit approval changes decision to APPROVED.
    """
    context = create_context("task-appr-002")
    artifact = Artifact(
        artifact_id="art-deliverable-002",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)

    updated_req = manager.approve_deliverable(
        approval_id=req.approval_id,
        reviewer_id="lead-engineer-01",
        comment="Approved for release.",
    )

    assert updated_req.status == ApprovalStatus.APPROVED
    assert updated_req.reviewer_id == "lead-engineer-01"
    assert updated_req.decided_at is not None
    assert updated_req.comment == "Approved for release."


def test_explicit_rejection_changes_status():
    """
    PART G (4): Explicit rejection changes decision to REJECTED.
    """
    context = create_context("task-appr-003")
    artifact = Artifact(
        artifact_id="art-deliverable-003",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)

    updated_req = manager.reject_deliverable(
        approval_id=req.approval_id,
        reviewer_id="safety-inspector-02",
        comment="Safety findings incomplete.",
    )

    assert updated_req.status == ApprovalStatus.REJECTED
    assert updated_req.reviewer_id == "safety-inspector-02"
    assert updated_req.decided_at is not None
    assert updated_req.comment == "Safety findings incomplete."


def test_approval_cannot_happen_twice():
    """
    PART G (5): Double approval attempt raises ValueError (terminal safety).
    """
    context = create_context("task-appr-004")
    artifact = Artifact(
        artifact_id="art-deliverable-004",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)
    manager.approve_deliverable(req.approval_id, reviewer_id="user-1")

    with pytest.raises(ValueError) as exc_info:
        manager.approve_deliverable(req.approval_id, reviewer_id="user-2")

    assert "already been decided" in str(exc_info.value)


def test_rejection_cannot_happen_twice_or_switch():
    """
    PART G (6): Rejection cannot happen twice and APPROVED cannot become REJECTED.
    """
    context = create_context("task-appr-005")
    artifact = Artifact(
        artifact_id="art-deliverable-005",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)
    manager.reject_deliverable(req.approval_id, reviewer_id="user-1")

    with pytest.raises(ValueError) as exc_info:
        manager.approve_deliverable(req.approval_id, reviewer_id="user-2")

    assert "already been decided" in str(exc_info.value)


def test_approved_deliverable_allows_consequential_action():
    """
    PART G (7): Approved deliverable permits consequential action execution.
    """
    context = create_context("task-appr-006")
    artifact = Artifact(
        artifact_id="art-deliverable-006",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)
    manager.approve_deliverable(req.approval_id, reviewer_id="user-1")

    result = manager.execute_consequential_action(req.approval_id, "publish_report")
    assert result["status"] == "EXECUTED"
    assert result["action_name"] == "publish_report"


def test_unapproved_deliverable_blocks_consequential_action():
    """
    PART G (8): Unapproved (PROPOSED) deliverable blocks consequential action.
    """
    context = create_context("task-appr-007")
    artifact = Artifact(
        artifact_id="art-deliverable-007",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)

    with pytest.raises(SecurityViolationError) as exc_info:
        manager.execute_consequential_action(req.approval_id, "publish_report")

    assert "blocked: Deliverable approval status is 'PROPOSED'" in str(exc_info.value)


def test_rejected_deliverable_blocks_consequential_action():
    """
    PART G (9): REJECTED deliverable blocks consequential action.
    """
    context = create_context("task-appr-008")
    artifact = Artifact(
        artifact_id="art-deliverable-008",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )
    manager = ApprovalManager()
    req = manager.create_approval_request(artifact, context)
    manager.reject_deliverable(req.approval_id, reviewer_id="user-1")

    with pytest.raises(SecurityViolationError) as exc_info:
        manager.execute_consequential_action(req.approval_id, "publish_report")

    assert "blocked: Deliverable approval status is 'REJECTED'" in str(exc_info.value)


def test_approval_rejection_audited():
    """
    PART G (10): Approval request, approval, and rejection generate audit records.
    """
    mock_audit = MockAuditRegistry()
    manager = ApprovalManager(audit_registry=mock_audit)
    context = create_context("task-appr-009")
    artifact = Artifact(
        artifact_id="art-deliverable-009",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )

    req = manager.create_approval_request(artifact, context)
    manager.approve_deliverable(req.approval_id, reviewer_id="lead-rev")

    events = [r.event_type for r in mock_audit.recorded_events]
    assert "approval_requested" in events
    assert "approval_granted" in events


def test_context_correlation_in_approval_audit():
    """
    PART G (11): RequestContext correlation preserved in approval audit events.
    """
    mock_audit = MockAuditRegistry()
    manager = ApprovalManager(audit_registry=mock_audit)
    context = create_context("task-appr-010")
    artifact = Artifact(
        artifact_id="art-deliverable-010",
        task_id=context.task_id,
        type=ArtifactType.REPORT,
        name="deliverable.pdf",
        location="outputs/deliverable.pdf",
        mime_type="application/pdf",
        created_by="synthesis_reporting",
    )

    req = manager.create_approval_request(artifact, context)
    manager.reject_deliverable(req.approval_id, reviewer_id="lead-rev", comment="Needs fix.")

    for record in mock_audit.recorded_events:
        assert record.request_context.task_id == context.task_id
        assert record.request_context.request_id == context.request_id
        assert record.request_context.user_id == context.user_id


def test_full_pipeline_with_approval_boundary():
    """
    PART G (12): Full Pipeline to Human Approval & Consequential Action Boundary.
    Task -> Planner -> Workflow -> Retrieval -> Multimodal -> Model -> Tools
    -> WorkflowState(COMPLETED) -> Synthesis -> Reporting -> Approval Request
    -> Explicit Approval -> Consequential Action.
    """
    planner = Planner()
    mock_auth = MockAuthorizationPolicy(default_allow=True)
    mock_audit = MockAuditRegistry()

    retrieved_res = ResourceReference(
        resource_id="kb-sop-inspection-approval",
        resource_type=ResourceType.RETRIEVED,
        uri_or_path="data/sample/sop_inspection_appr.pdf",
    )
    mock_retriever = MockRetriever(retrieved_resources=[retrieved_res])
    mock_multimodal = MockMultimodalProcessor()

    tool_artifact = Artifact(
        artifact_id="art-inspection-summary-appr",
        task_id="task-inspection",
        step_id="step-1",
        type=ArtifactType.REPORT,
        name="inspection_summary_appr.pdf",
        location="outputs/inspection_summary_appr.pdf",
        mime_type="application/pdf",
        created_by="tool_system",
    )
    mock_tool_executor = MockToolExecutor(
        generated_artifacts=[tool_artifact],
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )
    mock_model_registry = MockModelRegistry(
        tool_executor=mock_tool_executor,
        tool_to_invoke="document_generation",
    )

    engine = WorkflowEngine(
        model_registry=mock_model_registry,
        step_validator=StepValidator(),
        retriever=mock_retriever,
        multimodal_processor=mock_multimodal,
        authorization_policy=mock_auth,
        audit_registry=mock_audit,
    )

    request = create_inspection_task_request()
    plan = planner.create_plan(request)

    state = engine.execute_plan(plan)

    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        state = engine.execute_next_step(plan, state)

    assert state.status == WorkflowStatus.COMPLETED

    # 1. Final Synthesis
    synthesizer = FinalSynthesizer(model_registry=mock_model_registry)
    synthesized_content = synthesizer.synthesize_deliverable(request, state)

    # 2. Reporting
    reporter = ReportGenerator()
    proposed_deliverable = reporter.generate_report(synthesized_content)

    # 3. Create Approval Request
    approval_manager = ApprovalManager(audit_registry=mock_audit)
    appr_req = approval_manager.create_approval_request(
        deliverable=proposed_deliverable,
        request_context=request.request_context,
    )
    assert appr_req.status == ApprovalStatus.PROPOSED

    # Consequential action blocked prior to explicit approval
    with pytest.raises(SecurityViolationError):
        approval_manager.execute_consequential_action(appr_req.approval_id, "dispatch_action")

    # 4. Explicit Human Approval
    approved_req = approval_manager.approve_deliverable(
        approval_id=appr_req.approval_id,
        reviewer_id="chief-plant-engineer",
        comment="Full inspection findings and proposal verified.",
    )
    assert approved_req.status == ApprovalStatus.APPROVED

    # 5. Consequential Action permitted after approval
    action_res = approval_manager.execute_consequential_action(
        appr_req.approval_id, "dispatch_action"
    )
    assert action_res["status"] == "EXECUTED"
    assert action_res["action_name"] == "dispatch_action"



