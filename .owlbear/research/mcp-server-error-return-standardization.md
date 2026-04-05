# Standardize Error Handling, Return Types, and Exports Across MCP Servers

> **Owning task:** #496 — Standardize error handling, return types, and exports across MCP servers
> **Date:** 2026-04-02 **Status:** Complete (re-audit)

## 1. Context and Question

Three custom MCP servers (kanban, knowledge, project) evolved separately. A
prior audit (2026-03-31) identified gaps; most were subsequently fixed. This
re-audit verifies current state and identifies remaining inconsistencies.

A fourth server (mcp-memory) exists as a scaffold with no tools — excluded.

## 2. Sources Studied

| Source | Path / URL | What | Relevance |
|--------|-----------|------|-----------|
| MCP Spec 2025-06-18 § Error Handling | modelcontextprotocol.io/specification/2025-06-18/server/tools | Two mechanisms: protocol errors (JSON-RPC) and tool errors (`isError: true`) | 1.0 |
| MCP Python SDK — ToolError | `.venv/.../mcp/server/fastmcp/exceptions.py` | `ToolError` sets `isError: true`; normal returns set `isError: false` | 1.0 |
| mcp-kanban server.py | `packages/mcp-kanban/src/.../server.py` | Dual pattern: `ToolError` for typed returns, `error: ` for str returns | 1.0 |
| mcp-knowledge server.py | `packages/mcp-knowledge/src/.../server.py` | 6 tools + 2 resources; `__all__` present but incomplete | 1.0 |
| mcp-project server.py | `packages/mcp-project/src/.../server.py` | 4 tools + 2 resources; fully conformant | 0.9 |

## 3. Analysis

### 3a. Error Handling — Current State

| Server | Tool | Error format | Status |
|--------|------|-------------|--------|
| kanban | str-return tools | `f"error: {stderr.strip()}"` | OK |
| kanban | typed-return tools | `ToolError(msg)` | OK (spec-aligned) |
| knowledge | `search_knowledge` | `"error: ..."` + null check | OK |
| knowledge | `ingest_document` | `f"error: ingestion failed: {exc}"` | OK |
| knowledge | `list_entities` | `f"error: Invalid entity_type..."` | OK |
| knowledge | `get_stats` | No null check, crashes if `graph_store is None` | GAP |
| knowledge | `list_sources` | No null check, crashes if `source_store is None` | GAP |
| knowledge | `list_entities` | No null check, crashes if `graph_store is None` | GAP |
| project | all tools | `"error: ..."` where appropriate | OK |

**Null safety gap.** `AppContext` types all service fields as `T | None`, but
only `search_knowledge` checks for `None`. Three tools (`list_sources`,
`list_entities`, `get_stats`) crash with `AttributeError` if services are
unavailable. `ingest_document`'s bare `except Exception` masks the crash.

**Dual error convention.** mcp-kanban uses `ToolError` for Pydantic-return
tools (can't embed error string in a typed return) and `error: ` prefix for
str-return tools. Both are spec-valid (MCP §6 defines protocol errors and tool
execution errors as separate mechanisms). Convention doc omits this nuance.

### 3b. Return Types — Pre-Satisfied

All knowledge tools now return structured data (`list[dict]`, `dict`).
Project server already conformant. No changes needed.

### 3c. Module Exports

| Server | `__all__`? | Gap |
|--------|-----------|-----|
| kanban | 10 symbols | None |
| knowledge | 8 symbols | Missing `get_stats` (registered MCP tool) |
| project | 8 symbols | None |

### 3d. Convention Docs — Partial

MCP Server Conventions section exists in `copilot-instructions.md` (6 bullets).
Gap: doesn't explain dual error pattern (`ToolError` vs `error: ` string).

### 3e. Annotation Completeness

Convention says every tool declares all three annotation hints. Partial gaps
exist across all servers — overlaps with #492, not duplicated here.

### 3f. Legacy `tools.py`

`packages/mcp-knowledge/src/.../tools.py` contains an older `search_knowledge`
with its own `AppContext` and no `error:` prefix. Used by one test. Needs
consolidation but has test coupling (test import migration required).

## 4. Recommendation (.80 confidence)

T1 — consistency refactor. Two focused tasks remain:

1. **Null safety + `__all__`** — Add None checks to 4 knowledge tools; add
   `get_stats` to `__all__`. Small, testable, no design decisions.
2. **Convention doc clarification** — Add note about dual error pattern.

Challenge: reconsider (.55). Accepted: expanded null safety from 1 to 4 tools.
Rebutted T2: no meaningful trade-offs; dual pattern already established.

## 5. Follow-up Tasks

See task #496 body for executed commands and created task IDs.
