"""
Smoke Test for Sovereign Workbench Repository Architecture.

Owned by: Developer 1 (System Architect)
Verifies importability of all subsystems, correctness of shared contracts,
and adherence to interface definitions.
"""

import pytest
from datetime import datetime, timezone

# 1. Core Imports
from workbench.core.context import RequestContext
from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.types import (
    Evidence,
    ResourceReference,
    ConfidenceSource,
    ResourceType,
)
from workbench.core.errors import (
    WorkbenchError,
    ContractValidationError,
    SecurityViolationError,
    SubsystemExecutionError,
)

# 2. Subsystem Imports
from workbench.workbench import TaskIntake, TaskValidator, WorkbenchAPI
from workbench.planner import TaskRequest, ExecutionStep, ExecutionPlan, Planner
from workbench.workflow import WorkflowState, StepStatus, WorkflowEngine, StepScheduler, StepValidator
from workbench.models import AgentRequest, AgentResult, AgentResultStatus, ModelRegistry, ModelRouter, AgentFactory
from workbench.retrieval import RetrievalRequest, RetrievalResult, Retriever, DocumentIngestor, VectorIndex
from workbench.multimodal import MultimodalRequest, MultimodalResult, MultimodalStatus, MultimodalProcessor, OCREngine
from workbench.tools import ToolRequest, ToolResult, ToolResultStatus, ToolRegistry, ToolExecutor, FilesystemTools
from workbench.security import AuthorizationPolicy, AuditRecord, AuditRegistry, SecurityPolicies, NetworkMonitor
from workbench.synthesis import FinalSynthesizer, ReportGenerator


def test_package_imports():
    """Verify that all subsystem modules import successfully."""
    assert RequestContext is not None
    assert TaskRequest is not None
    assert ExecutionPlan is not None
    assert WorkflowState is not None
    assert AgentRequest is not None
    assert RetrievalRequest is not None
    assert MultimodalRequest is not None
    assert ToolRequest is not None
    assert AuditRecord is not None
    assert FinalSynthesizer is not None


def test_core_contracts_instantiation():
    """Verify core shared type instantiation and serialization."""
    context = RequestContext(
        request_id="req-123",
        task_id="task-456",
        user_id="user-789",
        source_component="test_smoke",
    )
    assert context.request_id == "req-123"
    assert context.task_id == "task-456"
    assert context.timestamp is not None

    artifact = Artifact(
        artifact_id="art-001",
        task_id=context.task_id,
        type=ArtifactType.DOCUMENT,
        name="test_report.pdf",
        location="/storage/art-001.pdf",
        mime_type="application/pdf",
        created_by="document_generator",
    )
    assert artifact.artifact_id == "art-001"
    assert artifact.type == ArtifactType.DOCUMENT

    evidence = Evidence(
        evidence_id="ev-001",
        source_artifact=artifact.artifact_id,
        content="Sample extracted evidence content",
        location="page 1, line 12",
        evidence_type="text_snippet",
        confidence=0.95,
        confidence_source=ConfidenceSource.OCR_ENGINE,
    )
    assert evidence.confidence == 0.95
    assert evidence.confidence_source == ConfidenceSource.OCR_ENGINE

    resource = ResourceReference(
        resource_id="res-001",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="/data/input.pdf",
    )
    assert resource.resource_type == ResourceType.USER_PROVIDED


def test_cross_subsystem_contracts():
    """Verify major cross-subsystem contract schemas."""
    context = RequestContext(
        request_id="req-100",
        task_id="task-200",
        user_id="dev-1",
        source_component="planner",
    )

    resource = ResourceReference(
        resource_id="res-100",
        resource_type=ResourceType.USER_PROVIDED,
        uri_or_path="/data/manual.pdf",
    )

    # TaskRequest
    task_req = TaskRequest(
        request_context=context,
        user_input="Analyze confidential manual",
        resources=[resource],
    )
    assert task_req.user_input == "Analyze confidential manual"

    # ExecutionStep & ExecutionPlan
    step = ExecutionStep(
        step_id="step-1",
        objective="OCR document pages",
        resources=[resource],
        expected_output="Extracted text evidence",
        passing_criteria={"min_confidence": 0.8},
    )
    plan = ExecutionPlan(
        request_context=context,
        task_description=task_req.user_input,
        executable_steps=[step],
    )
    assert len(plan.executable_steps) == 1

    # WorkflowState
    state = WorkflowState(
        task_id=context.task_id,
        plan_id="plan-1",
        step_statuses={"step-1": StepStatus.PENDING},
    )
    assert state.step_statuses["step-1"] == StepStatus.PENDING

    # AgentRequest & AgentResult
    agent_req = AgentRequest(
        request_context=context,
        objective=step.objective,
        context_resources=[resource],
        expected_output=step.expected_output,
    )
    agent_res = AgentResult(
        request_context=context,
        status=AgentResultStatus.SUCCESS,
    )
    assert agent_res.status == AgentResultStatus.SUCCESS

    # MultimodalRequest & MultimodalResult
    mm_req = MultimodalRequest(
        request_context=context,
        resource=resource,
        modalities=["ocr"],
    )
    mm_res = MultimodalResult(
        request_context=context,
        status=MultimodalStatus.SUCCESS,
    )
    assert mm_res.status == MultimodalStatus.SUCCESS

    # ToolRequest & ToolResult
    tool_req = ToolRequest(
        request_context=context,
        tool_name="read_file",
        parameters={"path": "/data/input.txt"},
    )
    tool_res = ToolResult(
        request_context=context,
        status=ToolResultStatus.SUCCESS,
        output="File content string",
    )
    assert tool_res.status == ToolResultStatus.SUCCESS


def test_unimplemented_interfaces_raise_not_implemented():
    """Verify that un-implemented subsystem interfaces raise NotImplementedError explicitly."""
    planner = Planner()
    context = RequestContext(
        request_id="req-999", task_id="task-999", user_id="test", source_component="test"
    )
    task_req = TaskRequest(request_context=context, user_input="Test prompt")
    
    with pytest.raises(NotImplementedError):
        planner.create_plan(task_req)

    engine = WorkflowEngine()
    plan = ExecutionPlan(request_context=context, task_description="Test plan")
    with pytest.raises(NotImplementedError):
        engine.execute_plan(plan)

    synthesizer = FinalSynthesizer()
    state = WorkflowState(task_id="task-999", plan_id="plan-999")
    with pytest.raises(NotImplementedError):
        synthesizer.synthesize_deliverable(task_req, state)
