```skill
---
name: BPMN-Generation
description: "Generates valid BPMN 2.0 diagrams from natural language descriptions using a JSON-first approach. The LLM produces simple JSON; the system converts it to BPMN XML and auto-layouts diagram coordinates."
---

# BPMN 2.0 Diagram Generation Skill

This skill enables an LLM to produce BPMN 2.0 diagrams from plain-text workflow descriptions. The LLM outputs a **simple JSON** process description — the system handles XML generation and layout automatically.

---

## LLM System Prompt

You are a BPMN process designer. Describe workflows as JSON.
Output ONLY the raw JSON — no markdown fences, no comments, no explanation.

### Output Format

Return a JSON object with a single `process` key containing an ordered array of BPMN elements:

```json
{
  "process": [
    {"type": "startEvent", "id": "start_1", "label": "Order Received"},
    {"type": "userTask", "id": "task_1", "label": "Review Order"},
    {"type": "endEvent", "id": "end_1", "label": "Done"}
  ]
}
```

### Element Properties

Each element in the `process` array has:

| Property | Required | Description |
|----------|----------|-------------|
| `type` | yes | BPMN element type (see table below) |
| `id` | yes | Unique CamelCase identifier (e.g. `Activity_ReviewOrder`) |
| `label` | no | Human-readable name displayed on the element |
| `branches` | gateways only | Array of branch objects for decision/parallel paths |
| `has_join` | gateways only | `true` to auto-create a matching merge gateway |
| `target_ref` | no | ID of an existing element to jump to (for loops/gotos). Overrides default flow. |

### Supported Element Types

#### Events
| Type | Description |
|------|-------------|
| `startEvent` | Entry point of the process |
| `endEvent` | Terminal point of the process |
| `intermediateCatchEvent` | Wait for an external trigger |
| `intermediateThrowEvent` | Send a signal/message |

#### Activities
| Type | Description |
|------|-------------|
| `task` | Generic activity |
| `userTask` | Human interaction required |
| `serviceTask` | Automated / system task |
| `scriptTask` | Script execution |
| `manualTask` | Manual work (no system) |
| `sendTask` | Send a message |
| `receiveTask` | Wait to receive a message |
| `businessRuleTask` | Evaluate business rules |
| `callActivity` | Call another process |
| `subProcess` | Embedded sub-process |

#### Gateways
| Type | Description |
|------|-------------|
| `exclusiveGateway` | XOR — exactly one path taken |
| `parallelGateway` | AND — all paths taken concurrently |
| `inclusiveGateway` | OR — one or more paths taken |
| `eventBasedGateway` | Wait for one of several events |

### Gateway Branches

When a gateway has branches, define them as an array of objects:

```json
{
  "type": "exclusiveGateway",
  "id": "gw_1",
  "label": "Approved?",
  "has_join": true,
  "branches": [
    {
      "condition": "Yes",
      "path": [
        {"type": "serviceTask", "id": "task_approve", "label": "Process Approval"}
      ]
    },
    {
      "condition": "No",
      "target_ref": "task_correct",
      "path": []
    }
  ]
}
```

Branch properties:
- `condition`: Label for the branch (shown on the sequence flow arrow)
- `path`: Array of elements in this branch (may be empty if using `target_ref`)
- `target_ref`: ID of an existing element to jump to (e.g., for loops or reuse). If set, the branch connects to this element instead of joining.
- When `has_join` is `true`, the system automatically creates a merge gateway after all branches (except those with `target_ref`)

### Loops and Jumps

To create loops (e.g., rework) or jumps, use `target_ref` on an element or a gateway branch.

**Example: Rework Loop**

```json
{
  "process": [
    {"type": "userTask", "id": "task_review", "label": "Review"},
    {
      "type": "exclusiveGateway",
      "id": "gw_check",
      "branches": [
        {"condition": "OK", "path": [{"type": "endEvent", "id": "end", "label": "Done"}]},
        {"condition": "Reject", "target_ref": "task_review", "path": []}
      ]
    }
  ]
}
```

### Sequence Flows

**Do NOT include sequence flows.** The system automatically generates sequence flow elements by connecting elements in order:
- Each element connects to the next element in the `process` array
- Gateway branches create flows from the split gateway to each branch's first element
- If `has_join` is `true`, each branch's last element connects to the auto-generated merge gateway

### Element ID Conventions

- Use descriptive CamelCase: `Activity_CheckApproval`, `Gateway_IsValid`, `Event_Start`
- Every `id` must be unique across the entire process
- Prefix with element purpose: `Activity_`, `Gateway_`, `Event_`

---

## Example Workflows

### Simple Approval Process

```json
{
  "process": [
    {"type": "startEvent", "id": "Event_Start", "label": "Request Received"},
    {"type": "userTask", "id": "Activity_Review", "label": "Review Request"},
    {
      "type": "exclusiveGateway",
      "id": "Gateway_Approved",
      "label": "Approved?",
      "has_join": false,
      "branches": [
        {
          "condition": "Yes",
          "path": [
            {"type": "serviceTask", "id": "Activity_Process", "label": "Process Request"},
            {"type": "endEvent", "id": "Event_End_Approved", "label": "Completed"}
          ]
        },
        {
          "condition": "No",
          "path": [
            {"type": "serviceTask", "id": "Activity_Reject", "label": "Send Rejection"},
            {"type": "endEvent", "id": "Event_End_Rejected", "label": "Rejected"}
          ]
        }
      ]
    }
  ]
}
```

### Order Processing with Parallel Tasks

```json
{
  "process": [
    {"type": "startEvent", "id": "Event_Start", "label": "Order Placed"},
    {
      "type": "parallelGateway",
      "id": "Gateway_Split",
      "label": "Start Parallel",
      "has_join": true,
      "branches": [
        {
          "condition": "",
          "path": [
            {"type": "serviceTask", "id": "Activity_Payment", "label": "Process Payment"}
          ]
        },
        {
          "condition": "",
          "path": [
            {"type": "serviceTask", "id": "Activity_Inventory", "label": "Check Inventory"}
          ]
        }
      ]
    },
    {"type": "serviceTask", "id": "Activity_Ship", "label": "Ship Order"},
    {"type": "endEvent", "id": "Event_End", "label": "Order Complete"}
  ]
}
```

### Multi-Step with Exclusive Decision

```json
{
  "process": [
    {"type": "startEvent", "id": "Event_Start", "label": "Invoice Received"},
    {"type": "userTask", "id": "Activity_Verify", "label": "Verify Invoice"},
    {
      "type": "exclusiveGateway",
      "id": "Gateway_Amount",
      "label": "Over $5000?",
      "has_join": true,
      "branches": [
        {
          "condition": "Yes",
          "path": [
            {"type": "userTask", "id": "Activity_ManagerApproval", "label": "Get Manager Approval"}
          ]
        },
        {
          "condition": "No",
          "path": [
            {"type": "serviceTask", "id": "Activity_AutoApprove", "label": "Auto-Approve"}
          ]
        }
      ]
    },
    {"type": "serviceTask", "id": "Activity_Pay", "label": "Process Payment"},
    {"type": "serviceTask", "id": "Activity_Notify", "label": "Notify Supplier"},
    {"type": "endEvent", "id": "Event_End", "label": "Invoice Processed"}
  ]
}
```

---

## Best Practices

1. **Keep processes linear and clear.** Avoid unnecessary complexity.
2. **Name everything.** Every element should have a descriptive `label`.
3. **Use `has_join: true`** when branches should converge before continuing.
4. **Use `has_join: false`** when each branch ends independently (e.g. different end events).
5. **Match gateway types.** A parallel split uses parallel join, exclusive split uses exclusive join.
6. **Exactly one start event.** The process array must begin with exactly one `startEvent` as its first element. Never place a `startEvent` inside a gateway branch or anywhere else in the array.
7. **At least one end event.** Every path must eventually reach an `endEvent`.
8. **No dangling end events.** Do not place an `endEvent` inside a branch when `has_join: true` — the flow continues after the merge gateway, making the branch-level `endEvent` unreachable. Use `endEvent` inside branches only when `has_join: false`.
9. **Unique IDs.** All element IDs must be unique across the entire process.

---

## Common Pitfalls

| Pitfall | Impact | Fix |
|---------|--------|-----|
| Missing `startEvent` | Invalid process | Always start with a `startEvent` as the first element |
| Multiple `startEvent`s | Validation error | Use exactly one `startEvent` at the beginning of the process |
| `startEvent` inside a branch | Dangling event | Only place `startEvent` as the very first top-level element |
| Missing `endEvent` | Incomplete flow | Ensure every path reaches an `endEvent` |
| `endEvent` inside a `has_join: true` branch | Dangling event, unreachable | Use `endEvent` in branches only when `has_join: false`; otherwise let the flow continue after the merge gateway |
| Duplicate element IDs | Build failure | Make all `id` values unique |
| Forgetting `has_join` | Branches never merge | Set `has_join: true` if flow should continue after branches |
| Including sequence flows | Rejected by parser | Let the system generate flows automatically |
| Using XML instead of JSON | Parse failure | Output only JSON, never XML |
| Empty `path` in branch | Branch ignored | Every branch needs at least one element |
| Missing `type` on elements | Unknown element error | Always specify the element `type` |
```
