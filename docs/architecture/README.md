# Workbench Architecture & Design Guidelines

This document outlines the architecture, principles, execution flow, subsystem ownership, and dependency boundaries for the Sovereign Agentic AI Workbench.

---

## 1. Architectural Overview & Principles

The MVP architecture follows a structured, deterministic flow:

```
User
  ↓
Workbench / Task Intake
  ↓
Planner
  ↓
Execution Plan
  ↓
Workflow Engine
  ↓
Model Registry / Agent Factory
  ↓
Agent Execution
  ↙       ↓        ↘
Retrieval Multimodal Tools
  ↓
Workflow Validation / State
  ↓
Final Synthesis / Reporting
  ↓
Human Approval
```

### Key Architectural Constraints
1. **No Separate Orchestrator**: The Planner directly decomposes a `TaskRequest` into meaningful executable `ExecutionStep`s.
2. **Workflow Engine Boundaries**:
   - Owns execution state (`WorkflowState`), step scheduling (`StepScheduler`), dependency readiness, sequential progression, retry/failure handling, and validation against passing criteria.
   - Does **NOT** execute tools directly (tools are executed via Agent requests).
   - Does **NOT** synthesize step results.
3. **Final Synthesis**: After all required steps pass validation, `FinalSynthesizer` combines original task context with relevant step results, evidence, and artifacts to produce the final deliverable.
4. **Tools Flow**: `Agent -> ToolRequest -> Tool Registry/Executor -> ToolResult -> Agent -> AgentResult -> Workflow Engine`.
5. **Model Registry**: Accepts `AgentRequest` and yields `AgentResult`. Model selection is driven by task requirements and capabilities, not file extensions.
6. **Cross-Cutting Security/Audit**: Security (authorization, audit recording, policy enforcement, zero-egress network monitoring) applies across all subsystems. Audit logs record security/execution-relevant events, distinct from network isolation monitors.

---

## 2. Subsystem Ownership Matrix

| Subsystem | Folder Path | Primary Owner | Description |
| :--- | :--- | :--- | :--- |
| **Core** | `src/workbench/core/` | Dev 1 (System Architect) | Shared types (`RequestContext`, `Artifact`, `Evidence`, `ResourceReference`), domain exceptions. |
| **Workbench** | `src/workbench/workbench/` | Dev 1 (System Architect) | Task intake API, initial request validation, user facing entry points. |
| **Planner** | `src/workbench/planner/` | Dev 1 (System Architect) | Task decomposition into executable `ExecutionPlan` and `ExecutionStep`s. |
| **Workflow** | `src/workbench/workflow/` | Dev 1 (System Architect) | Execution state machine, step scheduler, dependency readiness, criteria validation. |
| **Models** | `src/workbench/models/` | Dev 2 (Model Engineer) | Model registry, capability router, agent factory, model serving wrappers. |
| **Retrieval** | `src/workbench/retrieval/` | Dev 3 (Retrieval Engineer) | Document ingestion, vector index, retriever interface, provenance tracking. |
| **Multimodal** | `src/workbench/multimodal/` | Dev 4 (Multimodal Engineer) | Multimodal processor, OCR engine, vision models, document parsing schemas. |
| **Tools** | `src/workbench/tools/` | Dev 5 (Tool/Sandbox Engineer) | Tool registry, execution engine, filesystem tools, python sandbox, document generation. |
| **Security** | `src/workbench/security/` | Dev 6 (Security/Audit Engineer) | Authorization policy, audit registry, security policies, zero-egress network monitor. |
| **Synthesis** | `src/workbench/synthesis/` | Dev 1 (System Architect) | Deliverable synthesis, final report generation. |
| **UI** | `src/workbench/ui/` | Dev 1 (System Architect) | User interface adapters and presentation handlers. |

---

## 3. Dependency & Boundary Rules

1. **Shared Core Contracts Only**: Subsystems may import from `workbench.core` and explicitly defined contract schemas.
2. **Interface Encapsulation**: Subsystems must interact with other subsystems through public contract interfaces rather than reaching into internal implementations.
3. **No Direct Inter-Subsystem Coupling**: For example, `workflow` must not directly call `tools` code; `agent` calls `tools`, and reports `AgentResult` back to `workflow`.
4. **Standard Library & Approved Dependencies**: Keep dependencies minimal (`pydantic`, `pytest`). Do not introduce heavy third-party frameworks without architect approval.
