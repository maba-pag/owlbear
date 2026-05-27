# Enrichment Tools Registry Alignment

> **Owning task:** #1901 — Knowledge: add enrichment tools to MCP_TOOL_ROUTING registry
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1901 proposes adding 4 enrichment tools to `MCP_TOOL_ROUTING` in `protocols/registry.py`. Research question: which tools actually exist, what are the correct routing values, and what pre-work is needed?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/knowledge/src/owlbear_knowledge/protocols/registry.py` L76–93 | Target registry (0.95) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L122–700 | Live tool implementations (0.95) |
| `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py` L196–388 | EnrichmentStore Protocol (0.95) |
| `serve/knowledge/src/owlbear_knowledge/protocols/DESIGN_DECISIONS.md` L1–20 | CP1 — consolidation retired (0.90) |
| `.owlbear/research/knowledge-mcp-tool-rename.md` | Prior research on #1895 (0.85) |
| `share/agents/knowledge-enricher.agent.md` L9 | Allowlist consumer (0.90) |

## 3. Analysis

### Task Body vs Reality

| Tool in task | Exists in server.py? | Protocol method? | Notes |
|---|---|---|---|
| `get_next_batch` | ✅ L122 | `EnrichmentStore.claim_batch` | Correct routing target |
| `get_consolidation_candidates` | ❌ | N/A — retired | CP1 removed consolidation pipeline |
| `store_enrichment` | ✅ L182 | `EnrichmentStore.submit_extractions` | Correct routing target |
| `retry_failed_enrichment` | ✅ L331+L591 (duplicate!) | ❌ None — uses raw SQL | Needs Protocol method first |

### Finding 1: `get_consolidation_candidates` Is Dead

Per `DESIGN_DECISIONS.md` CP1: the SAME_AS consolidation pipeline was deliberately abandoned. The tool was removed from server.py. No function, no Protocol method, no table — it cannot be added to the registry.

### Finding 2: `retry_failed_enrichment` Has No Protocol Method

This tool bypasses `EnrichmentStore` entirely — it runs raw SQL against `app_ctx.conn`. The registry pattern requires `Protocol.method` as the routing value. Either:

- **Option A:** Add `EnrichmentStore.reset_failed()` method, refactor tool to use it → enables clean routing
- **Option B:** Route as `EnrichmentStore.reset_failed` in registry (aspirational), implement Protocol method alongside rename

### Finding 3: Duplicate Definition Bug

`retry_failed_enrichment` is defined twice:
1. Bare function at L331, registered via `mcp.tool()(retry_failed_enrichment)` at L585
2. Re-defined with `@mcp.tool` decorator at L591

The second definition overwrites the first in module scope. Only 3 tools should be added to the registry, not 4.

### Corrected Registry Entries

| Proposed name | Routing value | Pre-work needed |
|---|---|---|
| `knowledge_enrichment_claim_batch` | `EnrichmentStore.claim_batch` | None |
| `knowledge_enrichment_store` | `EnrichmentStore.submit_extractions` | None |
| `knowledge_enrichment_retry` | `EnrichmentStore.reset_failed` | Add Protocol method + refactor tool |

### Agent Allowlist Impact

`knowledge-enricher.agent.md` tools line currently references:
```
ob-knowledge/get_next_batch, ob-knowledge/store_enrichment, ob-knowledge/retry_failed_enrichment
```
Must update to new names after rename.

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `retry_failed_enrichment` has no Protocol method | Medium | Add `reset_failed()` to EnrichmentStore as prerequisite |
| Duplicate function definition causes test confusion | Low | Fix as part of rename (delete dead code) |
| Task scope incorrect (4 tools → 3) | Low | Correct task body |

## 4. Recommendation

**Reduce scope to 3 tools and sequence correctly.** Confidence: **0.85**.

1. First: add `EnrichmentStore.reset_failed()` Protocol method (prerequisite)
2. Then: add 3 entries to `MCP_TOOL_ROUTING`, rename tools in server.py, update agent allowlist

Remove `get_consolidation_candidates` from the task — it was retired by design.

Challenge: FALLBACK — factual findings from codebase inspection, no contested trade-off.

## 5. Follow-up Tasks

1. **Correct #1901 scope** — remove `get_consolidation_candidates`, note Protocol gap for retry
2. **New task** — Add `EnrichmentStore.reset_failed()` Protocol method (prerequisite for clean routing)
3. **New task** — Fix `retry_failed_enrichment` duplicate definition in server.py
