# Phase 1 Enrichment Tools — Implementation State

> **Owning task:** #1328 — P2-12: Phase 1 enrichment tools (get_next_batch, store_enrichment)
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1328 requires implementing two MCP tools (`get_next_batch`, `store_enrichment`) for the enrichment worker subsystem. The question: what remains to be done?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Brief §4.4 | `.owlbear/briefs/draft-knowledge-activation/brief.md` L80–98 | 1.0 — authoritative spec |
| Test suite #1327 | `tests/test_mcp_knowledge_enrichment_tools_1327.py` (28 tests) | 1.0 — defines expected behavior |
| Implementation | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L223–349 | 1.0 — current code |
| Schema | `serve/knowledge/src/owlbear_knowledge/schema.py` | 0.9 — edge UNIQUE index, enrichment_state column |
| MCP tool registrations | `server.py` L624–1060 (14 `@mcp.tool` decorators) | 0.9 — shows registration pattern |

## 3. Analysis

### Current State

| AC | Status | Evidence |
|----|--------|----------|
| get_next_batch: IMMEDIATE txn + claimed update | DONE | Implementation L234–272; test AC1 passes |
| Returns: chunk_id, text, doc_title, section_path, source_name | DONE | Implementation L274–283; test AC2 passes |
| Claimed excluded from subsequent calls | DONE | Implementation L246 (`enrichment_state = 'pending'`); test AC3 passes |
| Lease expiry >10 min | DONE | Implementation L250–253 (`strftime` comparison); test AC4 passes |
| store_enrichment: UPSERT entities | DONE | Implementation L305–318 (`INSERT OR REPLACE`); test AC5 passes |
| store_enrichment: INSERT OR IGNORE edges w/ UNIQUE | DONE | Implementation L320–332; schema idx_edges_d17_unique; test AC6 passes |
| Updates enrichment_state to 'enriched' | DONE | Implementation L334–337; test AC7 passes |
| Per-source enrich flag | DONE | Implementation L247 (`COALESCE(ks.enrich, 1) = 1`); test AC9 passes |
| All #1327 tests pass | DONE | 28/28 tests pass (verified 2026-05-05) |

### Gap Identified

Both functions exist as **plain helper functions** (no `@mcp.tool` decorator). They are NOT registered on the MCP tool surface. The test suite imports them directly via `from owlbear_mcp_knowledge.server import get_next_batch, store_enrichment`, so tests pass regardless of MCP registration.

**The only remaining work:** Add `@mcp.tool()` decorators with appropriate `ToolAnnotations` to both functions.

### Implementation Approach

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def get_next_batch(...):  # existing implementation unchanged

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def store_enrichment(...):  # existing implementation unchanged
```

Both are non-read-only (they UPDATE state) and non-destructive (no data loss). Pattern matches `ingest_document` and `refresh_source` annotations.

## 4. Recommendation

**Classification: T1 — Autonomous.** Adding decorators is a mechanical wiring change. No architecture, security, or behavioral decisions needed.

**Confidence: 0.95** — Implementation is proven by passing tests; the only gap is MCP tool registration (2-line change).

Challenge: SKIPPED — trivial wiring, no recommendation trade-offs to challenge.

## 5. Follow-up Tasks

No new tasks needed. Task #1328 itself is the follow-up — it can proceed directly to `backlog` → `todo` pipeline with the finding that the builder only needs to add `@mcp.tool` decorators.
