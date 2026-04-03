# Memory-MCP Tools Implementation Readiness

> **Owning task:** #525 — Implement memory-mcp tools
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #525 implements 4 MCP tools (get_knowledge, record_learning, list_entries, mark_for_deletion) on the already-scaffolded mcp-memory package (#524, done). The design is specified in `docs/research/memory-mcp-server-design.md` §3E and approved via DR #387 (Option A) and DR #428. This research validates implementation readiness and documents the concrete patterns the builder should follow.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Design doc §3E | `docs/research/memory-mcp-server-design.md` | 1.0 |
| S2 | mcp-kanban server (tool pattern) | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .95 |
| S3 | mcp-knowledge server (SQLite pattern) | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .90 |
| S4 | MCP Python SDK README | github.com/modelcontextprotocol/python-sdk | .80 |
| S5 | Mem0 Python SDK quickstart | docs.mem0.ai/open-source/python-quickstart | .70 |
| S6 | DR #387 resolved | `docs/decisions/resolved/387-memory-mcp-architecture.md` | 1.0 |
| S7 | DR #428 resolved | `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` | 1.0 |
| S8 | Scaffolded mcp-memory | `packages/mcp-memory/src/owlbear_mcp_memory/server.py` | 1.0 |

## 3. Analysis

### 3A. Implementation patterns from existing MCP servers

| Pattern | mcp-kanban (S2) | mcp-knowledge (S3) | Apply to mcp-memory |
|---------|----------------|--------------------|--------------------|
| Tool decorator | `@mcp.tool(annotations=ToolAnnotations(...))` | Same | Same |
| Context access | `ctx.request_context.lifespan_context` | Same | Same |
| SQLite calls | N/A (subprocess) | `asyncio.to_thread` | `asyncio.to_thread` |
| Read-only returns | `list[dict]`, `str` | `list[dict]`, `str` | `list[dict]`, `str` |
| Mutation returns | `str` (id or error) | `str` | `str` |
| Validation errors | `f"error: ..."` string | `f"error: ..."` string | Same |
| Hard errors | `ToolError` (from `mcp.server.fastmcp.exceptions`) | N/A | For missing entries |
| Tool exclusion | `_apply_tool_exclusions` + `KANBAN_TOOLS_EXCLUDE` | Same + `KNOWLEDGE_TOOLS_EXCLUDE` | Add `MEMORY_TOOLS_EXCLUDE` |

### 3B. Scope-specificity sorting (get_knowledge)

SQL CASE avoids Python-side sorting — efficient and deterministic:

```sql
ORDER BY
  CASE
    WHEN scope_agent = :agent AND scope_project = :project THEN 0
    WHEN scope_agent = :agent AND scope_project IS NULL THEN 1
    WHEN scope_agent IS NULL AND scope_project = :project THEN 2
    ELSE 3
  END,
  confidence DESC
```

WHERE clause: `approval_state != 'deleted'` AND scope matches union of all 4 tiers (agent+project, agent-only, project-only, general). The AC says "sorted by scope-specificity then confidence" — this SQL delivers exactly that.

### 3C. Validation for record_learning

- **Confidence >= 0.7**: return `error: confidence must be >= 0.7, got {value}` (soft error, per MCP convention S2)
- **Category validation**: re-use `MemoryEntry.category` Literal type. Invalid category returns `error: invalid category '{value}'. Valid: preference, knowledge, context, behavior, goal`
- **UUID generation**: `uuid.uuid4()` for entry `id`
- **Timestamps**: `datetime.now(UTC).isoformat()` for `created_at`/`updated_at`
- **Source field**: auto-populate as `agent_id` (agent passes their name)

### 3D. Scaffold gaps to address alongside tools

| Gap | Fix | Effort |
|-----|-----|--------|
| No `_apply_tool_exclusions` | Add per mcp-kanban pattern + `MEMORY_TOOLS_EXCLUDE` env var | ~15 LOC |
| `__all__` incomplete | Add 4 tool function names + `_apply_tool_exclusions` | 1 line |
| No `asyncio` import | Add `import asyncio` | 1 line |

These are minor additions that naturally accompany tool implementation — not separate tasks.

## 4. Recommendation (.92 confidence)

Proceed with implementation. All prerequisites satisfied: scaffold done (#524), architecture approved (DR #387), patterns adopted (DR #428). The 4 tools follow well-established patterns from mcp-kanban and mcp-knowledge. No design decisions remain — the builder has a clear spec (design doc §3E) and concrete patterns (§3A–3D above) to follow.

Challenge: SKIPPED — info-only readiness validation, no alternative approaches considered.

**Classification: T1 (Autonomous).** No DR needed — implementing already-approved design on an existing scaffold.

## 5. Follow-up Tasks

Task #525 already exists and covers the full scope. No additional tasks needed. The AC is complete and test-writable. Dependency #524 is satisfied (done status).
