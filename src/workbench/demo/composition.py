"""
Demo Composition Root for SIH Sovereign Agentic AI Workbench.

Owned by: Developer 1 (System Architect)
Subsystem: demo

Wired Composition Root that connects real Retrieval (SovereignRetrieverAdapter),
real Multimodal (DefaultMultimodalProcessor), Demo Model Registry, Tools,
Security/Audit, and Workbench UI into a unified, executable pipeline for the E-204 scenario.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Set

from workbench.approval.manager import ApprovalManager
from workbench.approval.schemas import ApprovalRequest, ApprovalStatus
from workbench.core.artifacts import Artifact, ArtifactType
from workbench.core.context import RequestContext
from workbench.core.errors import SecurityViolationError, SubsystemExecutionError
from workbench.core.types import ConfidenceSource, Evidence, ResourceReference
from workbench.demo.data import create_mrpl_e204_task_request
from workbench.models.interfaces import AgentRequest, AgentResult, AgentResultStatus
from workbench.models.registry import ModelRegistry
from workbench.multimodal.adapters.local_artifact_store import LocalArtifactStore
from workbench.multimodal.adapters.path_resource_resolver import PathResourceResolver
from workbench.multimodal.adapters.tesseract_backend import SovereignOcrBackend, TesseractOcrBackend
from workbench.multimodal.processor import DefaultMultimodalProcessor, MultimodalProcessor
from workbench.multimodal.schemas import MultimodalRequest, MultimodalResult, MultimodalStatus
from workbench.planner.planner import Planner
from workbench.planner.schemas import ExecutionPlan, TaskRequest
from workbench.retrieval.retriever import RetrievalRequest, RetrievalResult, Retriever, SovereignRetrieverAdapter
from workbench.security.audit import AuditRecord, AuditRegistry
from workbench.security.authorization import AuthorizationPolicy
from workbench.security.policies import MockAuditRegistry, MockAuthorizationPolicy
from workbench.synthesis.reporting import ReportGenerator
from workbench.synthesis.synthesizer import FinalSynthesizer
from workbench.tools.executor import ToolExecutor
from workbench.tools.schemas import ToolRequest, ToolResult, ToolResultStatus
from workbench.ui.deliverable_approval_ui import DeliverableApprovalUI
from workbench.ui.evidence_artifact_viewer import EvidenceArtifactViewer
from workbench.ui.execution_dashboard import ExecutionDashboard
from workbench.ui.task_intake_ui import TaskIntakeUI
from workbench.workbench.api import WorkbenchAPI
from workbench.workflow.engine import WorkflowEngine
from workbench.workflow.state import StepStatus, WorkflowState, WorkflowStatus
from workbench.workflow.validation import StepValidator


class DemoToolExecutor(ToolExecutor):
    """
    Demo ToolExecutor producing generated artifacts and tool outputs.
    """

    def __init__(
        self,
        authorization_policy: Optional[AuthorizationPolicy] = None,
        audit_registry: Optional[AuditRegistry] = None,
    ) -> None:
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

        art = Artifact(
            artifact_id=f"art-{request.tool_name}-{request.request_context.step_id or '001'}",
            task_id=request.request_context.task_id,
            step_id=request.request_context.step_id,
            type=ArtifactType.REPORT,
            name=f"e204_corrective_action_{request.tool_name}.pdf",
            location=f"outputs/e204_corrective_action_{request.tool_name}.pdf",
            mime_type="application/pdf",
            created_by="demo_tool_executor",
            metadata={"equipment_id": "E-204", "tool_name": request.tool_name},
        )

        evidence = Evidence(
            evidence_id=f"ev-tool-{request.tool_name}-{request.request_context.step_id or '001'}",
            content=f"Tool output payload from {request.tool_name} for Equipment E-204 step execution.",
            location=f"tool_output://{request.tool_name}",
            evidence_type="tool_execution_output",
            provenance={"tool_name": request.tool_name},
            confidence=1.0,
            confidence_source=ConfidenceSource.SYSTEM_ASSESSMENT,
        )

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
            status=ToolResultStatus.SUCCESS,
            output={"result": f"Execution successful for {request.tool_name}"},
            evidence=[evidence],
            artifacts=[art],
            error=None,
        )


class DemoModelRegistry(ModelRegistry):
    """
    Demo Model Registry providing step-specific domain answers for E-204.
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None) -> None:
        self.tool_executor = tool_executor
        self.received_requests: list[AgentRequest] = []

    def execute(self, request: AgentRequest) -> AgentResult:
        self.received_requests.append(request)

        obj = request.objective.lower()
        tool_artifacts: list[Artifact] = []
        tool_evidence: list[Evidence] = []

        if "step-1" in obj or "findings" in obj:
            content = (
                "Inspection Findings Summary: E-204 drive-end bearing vibration 3.8 mm/s RMS (exceeding 2.5 limit); "
                "housing temperature 92°C (exceeding 85 limit); primary seal leakage detected."
            )
        elif "step-2" in obj or "sop" in obj:
            content = (
                "SOP Requirements: SOP-ENG-204 section 4.2 specifies max vibration threshold of 2.5 mm/s RMS "
                "and maximum seal flange temperature of 85°C."
            )
        elif "step-3" in obj or "compare" in obj:
            content = (
                "Gap Analysis: E-204 exceeds SOP vibration threshold by +1.3 mm/s (+52%) and seal temperature "
                "by +7.0°C (+8.2%). Non-conformity verified."
            )
        elif "step-4" in obj or "historical" in obj or "incident" in obj:
            content = (
                "Historical Incident Match: Incident #17 (2023) exhibited identical vibration escalation prior to "
                "catastrophic seal failure. Precursor pattern confirmed."
            )
        elif "step-5" in obj or "corrective" in obj or "formulate" in obj:
            content = (
                "Proposed Corrective Actions: 1) Schedule immediate controlled shutdown of E-204; 2) Replace drive-end "
                "bearing assembly; 3) Flush mechanical seal lines and replace elastomer seals."
            )
        else:
            content = (
                "Final Corrective Action Proposal: Comprehensive package synthesized containing inspection findings, "
                "SOP non-conformities, Incident #17 historical correlation, and 3-stage corrective action plan."
            )

        step_ev = Evidence(
            evidence_id=f"ev-agent-{request.request_context.step_id or 'syn'}",
            content=content,
            location="agent_reasoning_output",
            evidence_type="agent_analysis",
            provenance={"agent_model": "Qwen2.5-72B-Instruct-Sovereign"},
            confidence=0.97,
            confidence_source=ConfidenceSource.OTHER_MODEL,
        )
        tool_evidence.append(step_ev)

        if self.tool_executor is not None:
            tool_req = ToolRequest(
                request_context=request.request_context,
                tool_name="document_generation",
                parameters={"objective": request.objective},
            )
            tool_res = self.tool_executor.execute_tool(tool_req)
            if tool_res.status == ToolResultStatus.SUCCESS:
                tool_artifacts.extend(tool_res.artifacts)
                tool_evidence.extend(tool_res.evidence)

        return AgentResult(
            request_context=request.request_context,
            status=AgentResultStatus.SUCCESS,
            result_evidence=tool_evidence,
            artifacts=tool_artifacts,
            errors=[],
            metadata={"mock_execution": True, "objective": request.objective},
        )


class DemoComposition:
    """
    Wired Composition Root for the SIH Sovereign Agentic AI Workbench E-204 Demo.
    Uses real Retrieval (SovereignRetrieverAdapter), real Multimodal (DefaultMultimodalProcessor),
    and Demo Model Registry.
    """

    def __init__(
        self,
        authorization_policy: Optional[AuthorizationPolicy] = None,
        audit_registry: Optional[AuditRegistry] = None,
    ) -> None:
        self.auth_policy = authorization_policy or MockAuthorizationPolicy(default_allow=True)
        self.audit_registry = audit_registry or MockAuditRegistry()

        self.setup_environment()

    def setup_environment(self) -> None:
        """
        Instantiates and wires real Retrieval, real Multimodal, Demo Model Registry, Tools, and UI.
        """
        # 1. Real Retrieval via SovereignRetrieverAdapter
        self.retriever: Retriever = SovereignRetrieverAdapter()

        # 2. Real Multimodal via DefaultMultimodalProcessor
        root_dir = Path(".").resolve()
        resolver = PathResourceResolver(allowed_roots=[root_dir])
        artifact_store = LocalArtifactStore(root=root_dir / "outputs" / "artifacts")
        ocr_backend = SovereignOcrBackend()

        self.multimodal: MultimodalProcessor = DefaultMultimodalProcessor(
            backend=ocr_backend,
            resolver=resolver,
            artifact_store=artifact_store,
            dpi=200,
        )

        # 3. Demo Model Registry
        self.tool_executor = DemoToolExecutor(
            authorization_policy=self.auth_policy,
            audit_registry=self.audit_registry,
        )
        self.model_registry = DemoModelRegistry(tool_executor=self.tool_executor)

        # 4. Workflow Engine & Core Lifecycle
        self.planner = Planner()
        self.engine = WorkflowEngine(
            model_registry=self.model_registry,
            step_validator=StepValidator(),
            retriever=self.retriever,
            multimodal_processor=self.multimodal,
            authorization_policy=self.auth_policy,
            audit_registry=self.audit_registry,
        )

        # 5. Synthesis, Reporting, Approval
        self.synthesizer = FinalSynthesizer(model_registry=self.model_registry)
        self.reporter = ReportGenerator()
        self.approval_manager = ApprovalManager(audit_registry=self.audit_registry)

        # 6. UI Components
        self.workbench_api = WorkbenchAPI()
        self.task_intake_ui = TaskIntakeUI(api=self.workbench_api)
        self.execution_dashboard = ExecutionDashboard()
        self.evidence_artifact_viewer = EvidenceArtifactViewer()
        self.deliverable_approval_ui = DeliverableApprovalUI(
            approval_manager=self.approval_manager
        )

    def create_e204_task_request(self) -> TaskRequest:
        """
        Creates the equipment E-204 TaskRequest.
        """
        return create_mrpl_e204_task_request()

    def run_full_pipeline_approval_path(
        self, reviewer_id: str = "plant_chief_engineer", comment: str = "Approved for implementation."
    ) -> Dict[str, Any]:
        """
        Runs the complete end-to-end pipeline through explicit HUMAN APPROVAL
        and consequential action execution.
        """
        task_req = self.create_e204_task_request()
        plan = self.planner.create_plan(task_req)
        state = self.engine.execute_plan(plan)

        while True:
            ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
            if not ready:
                break
            state = self.engine.execute_next_step(plan, state)

        synthesized = self.synthesizer.synthesize_deliverable(task_req, state)
        deliverable = self.reporter.generate_report(synthesized)

        appr_req = self.approval_manager.create_approval_request(
            deliverable=deliverable, request_context=task_req.request_context
        )

        # Verify consequential action is blocked before approval
        blocked_before = False
        try:
            self.approval_manager.execute_consequential_action(appr_req.approval_id, "dispatch_work_order")
        except SecurityViolationError:
            blocked_before = True

        # Explicit Human Approval via UI
        updated_view = self.deliverable_approval_ui.handle_approve_action(
            approval_id=appr_req.approval_id, reviewer_id=reviewer_id, comment=comment
        )

        # Consequential action execution
        action_res = self.approval_manager.execute_consequential_action(
            appr_req.approval_id, "dispatch_work_order"
        )

        # Projections
        dashboard_view = self.execution_dashboard.render(state, plan, task_req)
        evidence_view = self.evidence_artifact_viewer.render_full_viewer(state, plan)

        return {
            "task_request": task_req,
            "plan": plan,
            "state": state,
            "deliverable": deliverable,
            "approval_request": self.approval_manager.get_approval_request(appr_req.approval_id),
            "blocked_before_approval": blocked_before,
            "action_result": action_res,
            "dashboard_view": dashboard_view,
            "evidence_view": evidence_view,
            "approval_ui_view": updated_view,
        }

    def run_full_pipeline_rejection_path(
        self, reviewer_id: str = "safety_inspector_lead", comment: str = "Root cause analysis incomplete."
    ) -> Dict[str, Any]:
        """
        Runs the complete end-to-end pipeline through explicit HUMAN REJECTION
        and verifies consequential action is BLOCKED.
        """
        task_req = self.create_e204_task_request()
        plan = self.planner.create_plan(task_req)
        state = self.engine.execute_plan(plan)

        while True:
            ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
            if not ready:
                break
            state = self.engine.execute_next_step(plan, state)

        synthesized = self.synthesizer.synthesize_deliverable(task_req, state)
        deliverable = self.reporter.generate_report(synthesized)

        appr_req = self.approval_manager.create_approval_request(
            deliverable=deliverable, request_context=task_req.request_context
        )

        # Explicit Human Rejection via UI
        updated_view = self.deliverable_approval_ui.handle_reject_action(
            approval_id=appr_req.approval_id, reviewer_id=reviewer_id, comment=comment
        )

        # Verify consequential action is BLOCKED after rejection
        blocked_after = False
        try:
            self.approval_manager.execute_consequential_action(appr_req.approval_id, "dispatch_work_order")
        except SecurityViolationError:
            blocked_after = True

        dashboard_view = self.execution_dashboard.render(state, plan, task_req)
        evidence_view = self.evidence_artifact_viewer.render_full_viewer(state, plan)

        return {
            "task_request": task_req,
            "plan": plan,
            "state": state,
            "deliverable": deliverable,
            "approval_request": self.approval_manager.get_approval_request(appr_req.approval_id),
            "blocked_after_rejection": blocked_after,
            "dashboard_view": dashboard_view,
            "evidence_view": evidence_view,
            "approval_ui_view": updated_view,
        }
