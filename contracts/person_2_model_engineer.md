# PERSON 2 — MODEL ENGINEER

## Final-system ownership

Own:

- Model Registry
- Model Router
- model serving
- model metadata
- capability registry
- health monitoring
- model selection
- benchmarking
- resource-aware routing
- model lifecycle

## MVP subsystem

```text
Model Infrastructure
├── Local model serving
├── Model registry
├── Capability metadata
├── Router
└── Agent factory
```

## Actually build now

Minimum:

```text
2 local models
      ↓
common inference interface
      ↓
basic capability-based router
      ↓
agent preparation
```

For example:

```text
general reasoning model
+
multimodal model
```

Potentially a third coding-capable model if the demo benefits.

Don't waste the hackathon building sophisticated GPU scheduling.

## 1. Model Registry / Agent Factory

This is Person 2's most important boundary.

The core system should **not tell the Model Registry which model to use.**

It says:

> "This is the work I need performed. Prepare the most suitable local agent for it."

### Input: `AgentRequest`

```text
AgentRequest
├── request_context
├── objective
├── instructions?
├── context
├── resources[]
├── required_capabilities[]
├── expected_output
├── output_schema?
├── constraints[]
├── available_tools[]
└── execution_requirements
```

### Important fields

`objective`

What needs to be accomplished.

Example:

```text
"Analyze the attached inspection report and identify
safety findings relevant to equipment E-204."
```

`context`

Information necessary to understand the task.

```text
original task
previous relevant step results
user-provided context
retrieved evidence
```

`resources`

References to things the agent may need:

```text
files
images
documents
tables
artifacts
```

`required_capabilities`

Not a model name.

For example:

```text
[
    "reasoning",
    "document_analysis",
    "multimodal"
]
```

`expected_output`

Human/semantic description:

```text
"Structured list of safety findings with evidence."
```

`output_schema`

Optional machine-readable schema.

This is extremely useful.

## 2. Model Registry → Agent Result

We need to distinguish the **prepared agent** from its final result.

For MVP, Person 2's subsystem can expose one high-level operation:

```text
AgentRequest
      ↓
Model Registry / Agent Factory
      ↓
Agent
      ↓
execution
      ↓
AgentResult
```

### `AgentResult`

```text
AgentResult
├── request_context
├── status
├── output
├── structured_output?
├── artifacts[]
├── evidence[]
├── model_used
├── execution_metadata
└── errors[]
```

Example:

```text
status: SUCCESS

model_used:
local_multimodal_model_v1

structured_output:
  {
    "findings": [...]
  }

evidence:
  [...]
```

## What the Model subsystem does internally

```text
AgentRequest
     |
     ▼
Understand requested capability
     |
     ▼
Inspect available local models
     |
     ▼
Select suitable model
     |
     ▼
Check model availability/resources
     |
     ▼
Construct agent configuration
     |
     ├── model
     ├── system instructions
     ├── task objective
     ├── context
     ├── resources
     ├── output requirements
     └── available tools
     |
     ▼
Execute agent
     |
     ├── model inference
     |
     └── tool requests
     |
     ▼
AgentResult
```

The Model Engineer can implement this however they want.

**The rest of our system only sees the contract.**
