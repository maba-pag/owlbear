# Dual Error Pattern in MCP Server Conventions

> **Owning task:** #540 — Clarify dual error pattern in MCP convention docs
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

The MCP Server Conventions section in `copilot-instructions.md` documents a single
error convention (`error: ` string prefix) but mcp-kanban uses two patterns:
`ToolError` exceptions for typed returns and `error: ` strings for str returns.
Should the conventions doc clarify this dual pattern?

## 2. Sources Studied

| Source | Path / URL | What | Relevance |
|--------|-----------|------|-----------|
| MCP Spec §6 Error Handling | modelcontextprotocol.io/specification/2025-06-18/server/tools | Two mechanisms: protocol errors (JSON-RPC) and tool execution errors (`isError: true`) | 1.0 |
| MCP Python SDK lowlevel/server.py | `.venv/.../mcp/server/lowlevel/server.py` L467–576 | `_make_error_result` sets `isError=True`; normal returns set `isError=False` | 1.0 |
| mcp-kanban server.py | `packages/mcp-kanban/src/.../server.py` | `show_task`/`move_task`/`pick_task` use `ToolError`; `list_tasks`/`create_task`/`edit_task`/`start_work`/`end_work` use `error: ` prefix | 1.0 |
| Prior research (#496) | `docs/research/mcp-server-error-return-standardization.md` §3a | Identified convention doc gap | 0.9 |

## 3. Analysis

N/A — trivial docs change. No trade-offs. The dual pattern exists because
typed-return tools (Pydantic models) cannot embed error strings in the model —
they must raise `ToolError`. Str-return tools can embed `error: ` directly.

Both mechanisms are spec-valid per MCP §6. The SDK handles them differently:
- `ToolError` (exception) → caught → `isError=true` in response
- `error: ` string (normal return) → `isError=false` in response

## 4. Recommendation (.95 confidence)

T1 — document existing behavior. Add ≤ 5 lines to MCP Server Conventions
clarifying when each pattern is used and why both are spec-valid.

Challenge: SKIP — info-only, no recommendation with trade-offs.

## 5. Follow-up Tasks

Task #540 IS the follow-up from #496 research. AC is validated and correct.
No additional tasks needed.
