# Expose Scope Parameters in mcp-knowledge Tool Signatures

> **Owning task:** #617 — Expose scope parameters in mcp-knowledge tool signatures
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #617 asks to wire scope parameters through the MCP tool layer for `search_knowledge`, `ingest_document`, and `list_entities`. The task body states: "All downstream services already support these parameters — this task only wires them through." This research validates that claim and identifies the implementation approach.

## 2. Sources Studied

| Source | Location | Relevance | What |
|--------|----------|-----------|------|
| #135 research doc | .owlbear/research/knowledge-scoping.md | .95 | Column-based scope filtering design, flat string format, implemented in schema v3 |
| #616 research doc | .owlbear/research/project-local-knowledge-source.md | .95 | Recommends scope-based tool params (Option C) as foundation for project-local knowledge |
| server.py (MCP tools) | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | 1.0 | Current tool signatures — `search_knowledge`, `ingest_document`, `list_entities` lack scope params; `list_sources` already has `scope` param |
| query_service.py | serve/knowledge/src/owlbear_knowledge/query_service.py | 1.0 | `query()` does NOT accept per-query `scopes` — only at construction via `__init__` |
| ingest.py | serve/knowledge/src/owlbear_knowledge/ingest.py | .90 | `ingest_text(text, metadata, scope="global")` — already supports `scope` param |
| graph_store.py | serve/knowledge/src/owlbear_knowledge/graph_store.py | .90 | `list_entities(entity_type, scopes, source_pipeline)` — already supports `scopes` param |
| test_list_sources.py | serve/mcp-knowledge/tests/test_list_sources.py | .85 | Existing scope-forwarding test pattern to mirror |

## 3. Analysis

### 3.1 Downstream Readiness Assessment

| AC | Tool | Downstream method | Accepts scope? | Wiring needed |
|----|------|-------------------|----------------|---------------|
| AC1 | `search_knowledge` | `KnowledgeQueryService.query()` | **NO — gap** | Add `scopes` param to `query()`, then wire |
| AC2 | `ingest_document` | `IngestPipeline.ingest_text()` | YES (`scope="global"`) | Wire only |
| AC3 | `list_entities` | `GraphStore.list_entities()` | YES (`scopes=None`) | Wire only |

### 3.2 AC1 Gap: `query()` Lacks Per-Query Scopes

`KnowledgeQueryService.__init__` accepts `scopes: list[str] | None` and stores it as `self._scopes`. Both `_search_chunks()` and `query()` use `self._scopes` — neither accepts a runtime override. The task body's claim that downstream "already supports" scopes for search is **incorrect** at the `query()` API boundary.

| Option | Description | LOC | KISS | Risk |
|--------|-------------|-----|------|------|
| A: Add `scopes` param to `query()` (.90) | Optional override; when not None, temporarily shadow `self._scopes` | ~5 | High | None — default preserves behavior |
| B: Mutate `qs._scopes` before call (.40) | Set instance field per-request from MCP tool | ~2 | Low | Race condition if concurrent calls; violates encapsulation |
| C: New QS per request (.30) | Construct new `KnowledgeQueryService` per tool invocation | ~15 | Very low | Overhead: re-creates embedding provider bindings each call |

**Verdict:** Option A. Add `scopes: list[str] | None = None` to `query()` and `_search_chunks()`, using the param when provided, falling back to `self._scopes`. This is a ~5 LOC change in `query_service.py`, fully backwards-compatible.

### 3.3 Implementation Approach

For all three tools, mirror the `list_sources` pattern (already implemented):
1. Add optional scope param to MCP tool signature with backward-compatible default
2. Pass param through to the downstream service call
3. Test: mock downstream service, assert scope param forwarded correctly

### 3.4 Testing Strategy

Mirror `test_list_sources.py` pattern per tool:
- Test with-scope: call tool with scope param, assert downstream mock received it
- Test without-scope: call tool without scope, assert downstream received default (None or "global")
- Existing tests pass unchanged (default behavior preserved)

## 4. Recommendation (.90 confidence)

Proceed with #617 as specified, with one prerequisite: a small downstream change to add `scopes` param to `KnowledgeQueryService.query()` and `_search_chunks()`. This unblocks AC1.

AC2 and AC3 are straight wiring — no downstream changes needed.

**Tier: T1 (Autonomous).** All changes add optional parameters with defaults that preserve existing behavior. No breaking changes, no new capability — just exposes existing scope infrastructure at the MCP tool boundary.

Challenge: FALLBACK — no challenger agent available in this session.
Confidence in original: .90. The only risk is the query() gap, mitigated by the prerequisite task.

## 5. Follow-up Tasks

1. **Prerequisite task** (created at ideation): Add per-query `scopes` override to `KnowledgeQueryService.query()` — #617 depends on this.
2. **#617 itself** is ready for backlog once the prerequisite is created and dependency recorded.
