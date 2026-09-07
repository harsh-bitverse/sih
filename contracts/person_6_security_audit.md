# 8. Security + Audit subsystem

I would actually give Person 6 two interfaces.

One for security authorization.

One for audit events.

Because those are conceptually different operations.

---

## Input: `AuthorizationRequest`

```text
AuthorizationRequest
├── request_context
├── user_id
├── action
├── resource?
├── requested_permissions
└── context
```

Example:

```text
user:
    employee_001

action:
    execute_python

resource:
    sandbox_001
```

## Output: `AuthorizationResult`

```text
AuthorizationResult
├── request_context
├── allowed
├── granted_permissions[]
├── restrictions[]
└── reason
```

For MVP this can be extremely simple:

```text
valid employee → allowed
invalid user → rejected
```

But the interface supports future sophistication.

# 9. Audit interface

Every subsystem emits:

`AuditEvent`

```text
AuditEvent
├── request_context
├── event_id
├── event_type
├── actor
├── component
├── action
├── status
├── metadata
└── timestamp
```

For example:

```text
event_type:
    MODEL_REQUEST

component:
    model_registry

action:
    select_and_execute_model

status:
    SUCCESS

metadata:
    {
        "selected_model": "...",
        "capabilities": [...],
        "latency": ...
    }
```

Or:

```text
event_type:
    TOOL_CALL

component:
    tool_system

action:
    python_execute

status:
    SUCCESS

metadata:
    {
        "network_enabled": false,
        "sandbox": true
    }
```

# 10. And the network sovereignty proof

This should not be treated merely as an application audit event.

Application logs can say:

```text
external_call = false
```

but that's not proof.

Person 6 should therefore have a separate MVP mechanism:

```text
Application audit
       +
network monitoring
       +
network isolation
```

The UI can show:

```text
┌───────────────────────────────┐
│        SOVEREIGNTY STATUS     │
├───────────────────────────────┤
│ External network calls:    0  │
│ Blocked egress attempts:   0  │
│ External endpoints:        0  │
│ Data leaving system:       0  │
└───────────────────────────────┘
```

That's the kind of thing judges will understand immediately.
