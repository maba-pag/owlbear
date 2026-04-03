# Add `start_work` Compound Tool to mcp-kanban Server

> **Owning task:** #470 — Add start_work compound tool to mcp-kanban server
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Every pipeline agent currently needs 2 tool calls to begin work on a task: `edit_task` (to claim) + `show_task` (to read details). A compound `start_work` tool would reduce this to 1 call, returning full task JSON plus the claim name used. The auto-generated claim name (via `kanban-md agent-name`) allows agents to release their claim at `end_work` without knowing their name in advance.

**Key questions:** What's the implementation pattern? How does `agent-name` work? How to handle errors? Does FastMCP support compound tools natively?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| MCP Python SDK (FastMCP) | https://github.com/modelcontextprotocol/python-sdk | Tool definition patterns, `@mcp.tool()` decorator, return types (.95) |
| FastMCP Tools docs | https://gofastmcp.com/servers/tools | Tool arguments, return values, error handling (.90) |
| OwlBear mcp-kanban server.py | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Existing 7-tool implementation, `_run_kanban` helper, `AppContext` pattern (.95) |
| OwlBear kanban-md SKILL.md | `skills/kanban-md/SKILL.md` | `agent-name` command, claim pitfalls, `--claim`/`--release` semantics (.90) |
| kanban-md CLI (live testing) | Local binary `kanban/kanban-md.exe` | `agent-name` output format, claim conflict error text (.95) |

## 3. Analysis

### 3.1 `kanban-md agent-name` behavior

Generates unique two-word names (e.g., "cedar-cloud", "solar-swift"). Each invocation produces a different name. Returns a plain string (no JSON). Exit code 0 on success.

### 3.2 Claim conflict error format

When claiming an already-claimed task, `kanban-md edit --claim X` returns exit code 1 with stderr: `task #N is claimed by "agent" (expires in Xm0s). If this is you, add: --claim agent`. The tool should surface this error clearly.

### 3.3 Implementation approach (.90 confidence)

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Pattern | Standard `@mcp.tool()` with sequential `_run_kanban` calls | Matches existing 7 tools. No special compound construct needed in FastMCP. |
| Auto-claim | Call `_run_kanban(ctx, "agent-name")` | Reuses existing subprocess helper. Returns plain text, strip whitespace. |
| Claim step | Call `_run_kanban(ctx, "edit", task_id, "--claim", name)` | No status change — claim only. |
| Show step | Call `_run_kanban(ctx, "show", task_id, "--json")` | Returns full task JSON. |
| Response | Parse show JSON, inject `claim_name` field, return merged JSON | Single JSON response with everything the agent needs. |
| Error: already claimed | Return error string from claim step stderr | Consistent with existing error pattern. Don't proceed to show. |
| Error: task not found | Return error from first failing step | Fail fast. |
| KANBAN_TOOLS_EXCLUDE | No action now — #473 handles exclusion generically | AC says "if implemented". |

### 3.4 Return format

```json
{
  "id": 470,
  "title": "...",
  "status": "ideation",
  "priority": "needed",
  "tags": ["scope:mcp"],
  "body": "...",
  "claim_name": "cedar-cloud"
}
```

All fields from `show --json` plus the `claim_name` field so the agent knows what name was used for later release.

### 3.5 Test strategy

| Test case | What to verify |
|-----------|---------------|
| Auto-generated claim | `agent-name` called when no `claim` param, edit called with generated name |
| Explicit claim | `agent-name` NOT called, edit called with provided name |
| Already-claimed error | Claim step returns rc≠0, tool returns error, show NOT called |
| Task not found | Edit step returns rc≠0, tool returns error |
| JSON response | Response is valid JSON with all show fields + `claim_name` |

Mock `_run_kanban` per existing test patterns — no real subprocess calls needed.

## 4. Recommendation (.90 confidence)

Implement as a single `@mcp.tool()` function doing 2-3 sequential `_run_kanban` calls (agent-name → edit --claim → show --json). Parse the show output as JSON, add `claim_name`, return the merged JSON string. This is ~30 LOC plus ~60 LOC of tests.

**Risks:** Minimal. The pattern directly mirrors existing tools. The only new element is parsing JSON from `show --json` output and injecting a field, which is straightforward.

## 5. Follow-up Tasks

Tasks already exist (#470 itself covers implementation). No additional decomposition needed — the task is well-scoped with clear AC. The sibling tasks #471 (end_work) and #473 (KANBAN_TOOLS_EXCLUDE) are independent and already on the board.
