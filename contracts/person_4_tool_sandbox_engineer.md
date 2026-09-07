# PERSON 4 — TOOL / SANDBOX ENGINEER

## Final-system ownership

Own:

- Tool Registry
- tool execution
- tool schemas
- filesystem boundaries
- sandboxing
- resource limits
- network restrictions
- artifact generation
- safe execution

## MVP subsystem

Build only:

```text
Tool Registry
    |
    ├── read_file
    ├── write_file
    ├── python_execute
    ├── spreadsheet operations
    └── document generation
```

And:

```text
Python execution
        ↓
sandbox
        ↓
network disabled
        ↓
timeout/resource limit
```

This person is **not responsible for deciding which tool an agent needs.**

The agent/model decides.

This person makes sure:

> If the agent asks for a tool, the tool can execute safely.

## 3. Tool / Sandbox subsystem

Person 4's boundary is different.

The agent doesn't ask:

> "Give me a Python agent."

It asks:

> "Execute this tool."

### Input: `ToolRequest`

```text
ToolRequest
├── request_context
├── tool_id
├── arguments
├── requested_permissions
├── input_resources[]
└── constraints[]
```

Example:

```text
tool_id:
    python_execute

arguments:
    {
        "code": "..."
    }

requested_permissions:
    {
        "filesystem": "workspace_only",
        "network": false
    }
```

### Output: `ToolResult`

```text
ToolResult
├── request_context
├── tool_id
├── status
├── output
├── artifacts[]
├── execution_metadata
└── errors[]
```

## What Tool/Sandbox system does

```text
ToolRequest
     |
     ▼
Identify tool
     |
     ▼
Validate arguments
     |
     ▼
Check permissions
     |
     ▼
Create controlled execution environment
     |
     ▼
Execute tool
     |
     ├── filesystem isolation
     ├── resource limits
     ├── timeout
     └── network restriction
     |
     ▼
Capture output
     |
     ▼
ToolResult
```

## MVP tools

Keep it small:

```text
read_file
write_file
python_execute
generate_docx
generate_xlsx
```

Maybe a basic spreadsheet read/write capability.

That's enough to demonstrate the PS.

`ToolResult` is returned to the requesting agent/execution context, not directly to Workflow Engine.

Because the workflow is:

```text
Agent
  ↓
ToolRequest
  ↓
Tool
  ↓
ToolResult
  ↓
Agent continues
  ↓
AgentResult
  ↓
Workflow
```

Not:

```text
Tool
  ↓
Workflow
```

That distinction matters.
