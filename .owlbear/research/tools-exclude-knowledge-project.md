# TOOLS_EXCLUDE Config for Knowledge and Project MCP Servers

> **Owning task:** #493 — Add TOOLS_EXCLUDE config to knowledge and project MCP servers
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #473/#491 implemented `KANBAN_TOOLS_EXCLUDE` in mcp-kanban using a lifespan-level
`_apply_tool_exclusions(server)` helper that calls `FastMCP.remove_tool()` for each
comma-separated tool name. This task validates whether the same pattern applies directly
to the mcp-knowledge and mcp-project servers.

**Question:** Can we replicate the mcp-kanban TOOLS_EXCLUDE pattern to the other two
custom MCP servers without modification?

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|---------------|-----------|
| 1 | mcp-kanban `_apply_tool_exclusions` impl | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L72-90 | .95 — reference pattern |
| 2 | mcp-kanban TOOLS_EXCLUDE research (#473) | `docs/research/kanban-tools-exclude-config.md` | .90 — design rationale |
| 3 | mcp-knowledge `server.py` | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .95 — target: 5 tools, lifespan receives `_server` |
| 4 | mcp-project `server.py` | `packages/mcp-project/src/owlbear_mcp_project/server.py` | .95 — target: 4 tools, lifespan receives `_server` |
| 5 | `test_kanban_tools_exclude_491.py` | `tests/test_kanban_tools_exclude_491.py` | .85 — test pattern to replicate |

## 3. Analysis

### 3.1 Pattern Applicability

| Aspect | mcp-kanban (reference) | mcp-knowledge | mcp-project |
|--------|----------------------|---------------|-------------|
| Lifespan receives `_server: FastMCP` | Yes | Yes | Yes |
| Tools registered via `@mcp.tool()` | 8 tools | 5 tools | 4 tools |
| Env var prefix | `KANBAN_` | `OWLBEAR_` (existing: `OWLBEAR_KB_PATH`) | `OWLBEAR_` (existing: `OWLBEAR_ROOT`) |
| Proposed env var | `KANBAN_TOOLS_EXCLUDE` | `KNOWLEDGE_TOOLS_EXCLUDE` | `PROJECT_TOOLS_EXCLUDE` |
| LOC to add | (done) | ~12 | ~12 |
| Existing test infra | `tests/` | `packages/mcp-knowledge/tests/` | `packages/mcp-project/tests/` |

### 3.2 Env Var Naming

The AC specifies `KNOWLEDGE_TOOLS_EXCLUDE` and `PROJECT_TOOLS_EXCLUDE`. These differ
from the existing `OWLBEAR_` prefix used by other env vars in these servers, but match
the per-server naming from the design notes. The `{SERVER}_TOOLS_EXCLUDE` convention
established by `KANBAN_TOOLS_EXCLUDE` is consistent — each server owns its namespace.

### 3.3 Implementation Approach

Identical to mcp-kanban: copy `_apply_tool_exclusions()` into each server module,
changing only the env var name. Call it in `app_lifespan` before `yield`. Each server
remains independent (no shared library) per the design notes.

### 3.4 Test Strategy

Mirror `test_kanban_tools_exclude_491.py` for each server:

- Exclude single tool — verify `remove_tool` called once
- Exclude multiple tools — verify all removed
- No env var — verify no removals
- Invalid/unknown name — verify silently ignored (exception swallowed)

Tests go in each server's package test directory.

## 4. Recommendation (.95 confidence)

Replicate the mcp-kanban `_apply_tool_exclusions` pattern verbatim to both servers.
No alternatives considered — the pattern is proven, ~12 LOC per server, KISS-aligned.

Challenge: Skip — trivial replication of established pattern, no trade-offs.

**Tier: T1 (Autonomous)** — replicating an existing config pattern to sibling modules.
No new capability, no architecture change, no security impact.

## 5. Follow-up Tasks

Task #493 already has complete AC covering both servers. No additional tasks needed —
advance #493 to `backlog` for architect gate.
