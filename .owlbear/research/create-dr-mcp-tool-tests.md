# Test create_dr MCP Tool

> **Owning task:** #1182 — P1-03: Test create_dr MCP tool
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

What test structure and patterns should be used for the `create_dr` MCP tool adapter tests? The tool doesn't exist yet (#1183 implements it); this task writes the RED-phase test suite.

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` | 0.95 | Pattern: AppContext + mock AgentView, async tool call, response shape assertion |
| `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` | 0.90 | Error mapping pattern: KanbanError → ToolError with user_message |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 0.85 | Registration pattern: `@mcp.tool()`, `mcp._tool_manager._tools` introspection |
| Brief `draft-dr-script-replacement/brief.md` §MCP Tool | 1.00 | Interface contract: 4 params, response shape, error cases |
| Brief decisions D13 | 0.80 | Response shape: `{created: true, path: "..."}` only, no task_blocked field |

## 3. Analysis

### Test Structure (from AC)

| AC Line | Test Case | Pattern |
|---------|-----------|---------|
| Registration via `@mcp.tool()` | Introspect `mcp._tool_manager._tools` for "create_dr" | Static test (no async needed) |
| 4 required params: task_id, agent, request_type, body | Inspect tool function signature | `inspect.signature` |
| Returns `{created: true, path: "..."}` on success | Mock `decisions.create_dr` → return Path, call tool, assert dict shape | Async + mock |
| Error when task not found | Mock raises NotFoundError → assert ToolError | Async + mock side_effect |
| File collision (counter suffix) | Handled by engine layer — MCP tool just delegates. Test the path passthrough | Async + mock |
| request_type enum validation | Pass invalid value → expect ToolError or Pydantic validation error | Async |

### Implementation Pattern

The tool will be a thin adapter in `server.py`:
```python
@mcp.tool()
async def create_dr(ctx: Context, *, task_id: str, agent: str, request_type: str, body: str) -> dict:
    # validate request_type ∈ {"decision", "action"}
    # delegate to decisions.create_dr(...)
    # return {"created": True, "path": str(relative_path)}
```

Tests should mock `decisions.create_dr` (patch at the import point in server module) and verify:
1. Delegation with correct args
2. Response dict shape
3. Error mapping (NotFoundError → ToolError)
4. Enum validation (reject values other than "decision"/"action")

### Test File Location

`serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` — follows existing naming convention (tool name + task ID).

## 4. Recommendation

Follow the `test_mcp_mutation_tools_1087.py` pattern exactly: mock the underlying function, test delegation and error mapping. No live filesystem tests at this layer (those belong in #1180's `decisions.py` unit tests).

Confidence: 0.92

Challenge: FALLBACK — trivial T1 test scaffolding, no decision trade-offs to challenge.

## 5. Follow-up Tasks

None needed — this task IS the test-writing task. The test file will be created during the TODO→in-progress phase by the test-writer agent.
