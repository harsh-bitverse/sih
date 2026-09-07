# PERSON 1 — YOU

## Final-system ownership

### System Architect / Core Workflow / Workbench

Owns:

- overall architecture
- system contracts
- Task Intake
- Planner
- Workflow Engine
- execution state
- final verification
- final synthesis/report generation
- approval workflow
- main UI
- integration of all subsystems
- system-level testing
- architectural consistency

You are basically the **spine of the system**.

## MVP subsystem

```text
Core
├── Workbench
├── Task Intake
├── Planner
├── Workflow Engine
├── Execution State
├── Final Synthesis
└── Approval UI
```

## Actually build now

Build:

- task submission
- file attachment handling
- TaskRequest
- Planner
- ExecutionPlan
- executable step generation
- passing criteria generation
- Workflow Engine
- sequential step execution
- dependency handling
- step validation
- retry
- execution state
- final synthesis
- final output
- approval UI
- basic workflow visualization

```text
Planner
   |
   ├── Retrieval
   |
   └── Model Router


Workflow
   |
   └── Agent Request
           |
           ▼
       Model Registry
           |
           ▼
          Agent
         /     \
      Model    Tools
         |
      Multimodal
         |
      Retrieval
```

## Example end-to-end workflow

```text
USER

"Analyze this inspection package for E-204,
identify safety findings, compare them with
current SOP requirements and previous incidents,
recommend corrective actions, and prepare an
approval document."

        ↓

WORKBENCH

authenticate user
accept files
create TaskRequest

        ↓

PLANNER

reason over:
- task
- uploaded files
- retrieved context

        ↓

ExecutionPlan

Step 1:
Analyze inspection package
Passing criteria: all relevant findings extracted

Step 2:
Determine applicable SOP requirements
Passing criteria: every finding mapped to relevant requirement

Step 3:
Compare with previous incidents
Passing criteria: relevant historical similarities identified

Step 4:
Recommend corrective actions
Passing criteria: every major finding has justified action

        ↓

WORKFLOW ENGINE

Step 1
        ↓
MODEL REGISTRY
        ↓
appropriate agent
        ↓
tools / multimodal / retrieval
        ↓
result
        ↓
PASS?

Step 2
        ↓
...

        ↓

ALL STEPS PASSED

        ↓

FINAL SYNTHESIS

        ↓

Approval Document (.docx)

        ↓

HUMAN

Approve / Reject

        ↓

if approved

Controlled Action
