"""
SIH Sovereign On-Premise Agentic AI Workbench - Runnable Demo Script.

Demonstrates the complete end-to-end execution of the industrial MRPL equipment E-204 scenario:
Task Intake -> Planner -> WorkflowEngine (with Retrieval, Multimodal, Model, Tools, Security/Audit)
-> WorkflowState(COMPLETED) -> Final Synthesis -> Reporting -> DeliverableApprovalUI
-> Explicit Human APPROVE / REJECT -> Consequential Action Boundary.
"""

import sys
from pathlib import Path

# Add src/ directory to sys.path if needed
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from workbench.demo.composition import DemoComposition
from workbench.workflow.state import StepStatus


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def run_demo() -> int:
    print_banner("SIH Sovereign Agentic AI Workbench - Industrial MRPL Demo")
    print("Scenario: Industrial Inspection & Corrective Action Analysis for Equipment E-204\n")

    comp = DemoComposition()

    # ---------------------------------------------------------
    # STAGE 1: Task Intake
    # ---------------------------------------------------------
    print_banner("Stage 1: Task Intake & Validation")
    task_req = comp.create_e204_task_request()
    print(f"  [Intake UI] Title: Equipment E-204 Inspection Analysis")
    print(f"  [Intake UI] User ID: {task_req.request_context.user_id}")
    print(f"  [Intake UI] Task Prompt: '{task_req.user_input[:80]}...'")
    print(f"  [Intake UI] Attached Resources ({len(task_req.resources)}):")
    for r in task_req.resources:
        print(f"    - [{r.resource_type.value}] {r.resource_id} -> {r.uri_or_path}")

    # ---------------------------------------------------------
    # STAGE 2: Planning
    # ---------------------------------------------------------
    print_banner("Stage 2: Planner Plan Generation")
    plan = comp.planner.create_plan(task_req)
    print(f"  [Planner] Generated Plan Task ID: {plan.request_context.task_id}")
    print(f"  [Planner] Total Executable Steps: {len(plan.executable_steps)}")
    for i, step in enumerate(plan.executable_steps, 1):
        deps = f" (Depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
        print(f"    Step {i} ({step.step_id}): {step.objective[:70]}...{deps}")

    # ---------------------------------------------------------
    # STAGE 3: Workflow Engine Execution
    # ---------------------------------------------------------
    print_banner("Stage 3: Workflow Engine Multi-Subsystem Execution")
    state = comp.engine.execute_plan(plan)

    step_counter = 0
    while True:
        ready = [s for s, st in state.step_statuses.items() if st == StepStatus.READY]
        if not ready:
            break
        step_id = ready[0]
        step_counter += 1
        print(f"\n  --> Executing {step_id}...")
        state = comp.engine.execute_next_step(plan, state)
        res = state.step_results.get(step_id)
        ev_count = len(res.result_evidence) if res and hasattr(res, 'result_evidence') else 0
        art_count = len(state.step_artifacts.get(step_id, []))
        print(f"      [Step {step_id}] Status: {state.step_statuses.get(step_id).value} | Evidence Items: {ev_count} | Generated Artifacts: {art_count}")

    print(f"\n  [WorkflowEngine] Workflow Execution Status: {state.status.value}")

    # ---------------------------------------------------------
    # STAGE 4: Final Synthesis & Reporting
    # ---------------------------------------------------------
    print_banner("Stage 4: Final Synthesis & Report Deliverable Generation")
    synthesized = comp.synthesizer.synthesize_deliverable(task_req, state)
    deliverable = comp.reporter.generate_report(synthesized)
    synth_text = str(synthesized.get("synthesized_text") or "")
    print(f"  [FinalSynthesizer] Synthesized Text Preview: '{synth_text[:90]}...'")
    print(f"  [ReportGenerator] Deliverable Artifact ID: {deliverable.artifact_id}")
    print(f"  [ReportGenerator] Deliverable File Name: {deliverable.name}")
    print(f"  [ReportGenerator] File Location: {deliverable.location}")
    print(f"  [ReportGenerator] MIME Type: {deliverable.mime_type}")

    # ---------------------------------------------------------
    # STAGE 5: Read-Only Dashboard & Evidence Viewer
    # ---------------------------------------------------------
    print_banner("Stage 5: Workbench Dashboard & Evidence Viewer Projections")
    dash = comp.execution_dashboard.render(state, plan, task_req)
    print(f"  [Dashboard] Total Steps: {dash['summary']['total_steps']} | Completed: {dash['summary']['completed_steps']}")
    print(f"  [Dashboard] Total Artifacts: {dash['summary']['total_artifacts']} | Terminal: {dash['summary']['is_terminal']}")

    evidence_view = comp.evidence_artifact_viewer.render_full_viewer(state, plan)
    print(f"  [Evidence Viewer] Total Evidence Projections: {evidence_view['summary']['total_evidence_items']}")
    print(f"  [Evidence Viewer] Total Artifact Projections: {evidence_view['summary']['total_artifacts']}")

    # ---------------------------------------------------------
    # STAGE 6: Human Approval Review Boundary (PROPOSED)
    # ---------------------------------------------------------
    print_banner("Stage 6: Human Approval Boundary (PROPOSED)")
    appr_req = comp.approval_manager.create_approval_request(
        deliverable=deliverable, request_context=task_req.request_context
    )
    print(f"  [ApprovalManager] Approval Request ID: {appr_req.approval_id}")
    print(f"  [ApprovalManager] Current Approval Status: {appr_req.status.value}")

    # Verify consequential action blocked before approval
    try:
        comp.approval_manager.execute_consequential_action(appr_req.approval_id, "dispatch_work_order")
        print("  [ERROR] Consequential action executed unexpectedly!")
    except Exception as ex:
        print(f"  [SECURITY GUARANTEE] Consequential action BEFORE approval safely BLOCKED:\n    -> {ex}")

    # ---------------------------------------------------------
    # STAGE 7A: Human Approval Path (APPROVE)
    # ---------------------------------------------------------
    print_banner("Stage 7A: Human Decision - EXPLICIT APPROVAL")
    approved_view = comp.deliverable_approval_ui.handle_approve_action(
        approval_id=appr_req.approval_id,
        reviewer_id="chief_plant_engineer_01",
        comment="Verified E-204 vibration non-conformity and approved 3-stage corrective action plan.",
    )
    print(f"  [DeliverableApprovalUI] Reviewer: {approved_view['approval_view']['reviewer_id']}")
    print(f"  [DeliverableApprovalUI] New Status: {approved_view['approval_view']['status']}")
    print(f"  [DeliverableApprovalUI] Comment: {approved_view['approval_view']['comment']}")

    action_res = comp.approval_manager.execute_consequential_action(
        appr_req.approval_id, "dispatch_work_order"
    )
    print(f"  [Consequential Action] Status: {action_res['status']}")
    print(f"  [Consequential Action] Action Name: {action_res['action_name']}")
    print(f"  [Consequential Action] Deliverable ID: {action_res['deliverable_id']}")

    # ---------------------------------------------------------
    # STAGE 7B: Human Rejection Path (REJECT)
    # ---------------------------------------------------------
    print_banner("Stage 7B: Alternative Flow - EXPLICIT REJECTION")
    rejection_result = comp.run_full_pipeline_rejection_path(
        reviewer_id="safety_auditor_02",
        comment="Root cause analysis requires additional ultrasonic testing data.",
    )
    rej_req = rejection_result["approval_request"]
    print(f"  [DeliverableApprovalUI] Reviewer: {rej_req.reviewer_id}")
    print(f"  [DeliverableApprovalUI] New Status: {rej_req.status.value}")
    print(f"  [DeliverableApprovalUI] Comment: {rej_req.comment}")
    print(f"  [SECURITY GUARANTEE] Consequential action AFTER rejection safely BLOCKED: {rejection_result['blocked_after_rejection']}")

    # ---------------------------------------------------------
    # AUDIT TRAIL SUMMARY
    # ---------------------------------------------------------
    print_banner("Audit Trail Summary")
    records = comp.audit_registry.recorded_events
    print(f"  [AuditRegistry] Total Recorded Audit Events: {len(records)}")
    event_types = set(r.event_type for r in records)
    for et in sorted(event_types):
        count = sum(1 for r in records if r.event_type == et)
        print(f"    - Event '{et}': {count} occurrences")

    print_banner("Demo Complete - All Scenarios & Security Boundaries Verified!")
    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
