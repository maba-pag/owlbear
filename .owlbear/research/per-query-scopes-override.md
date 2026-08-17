# Per-Query Scopes Override for KnowledgeQueryService

> **Owning task:** #633 — Add per-query scopes override to KnowledgeQueryService.query()
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #633 (prerequisite for #617) adds an optional `scopes: list[str] | None = None` parameter to `KnowledgeQueryService.query()` and `_search_chunks()` so that the MCP tool layer can override the instance-level `self._scopes` at runtime.

**Question:** Is the approach sound, what are the risks, and is the codebase ready?

## 2. Sources Studied

| Source | Location | Relevance | What |
|--------|----------|-----------|------|
| #617 research doc | .owlbear/research/expose-scope-mcp-knowledge-tools.md | 1.0 | Identified the gap; recommends Option A (~5 LOC) |
| query_service.py | serve/knowledge/src/owlbear_knowledge/query_service.py | 1.0 | Current implementation; `query()` and `_search_chunks()` use `self._scopes` only |
| graph_store.py | serve/knowledge/src/owlbear_knowledge/graph_store.py | .85 | Established `scopes: list[str] \| None = None` param pattern (8+ call sites) |
| retrieval.py | serve/knowledge/src/owlbear_knowledge/retrieval.py:86 | .90 | `retrieve(query, top_k, scopes)` already accepts scopes param |
| qdrant.py | serve/knowledge/src/owlbear_knowledge/qdrant.py:151 | .80 | `search_similar` uses `scopes` filter — downstream is ready |
| MCP server.py | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | .85 | `search_knowledge` calls `qs.query()` — consumer of this change |

## 3. Analysis

### 3.1 Research Gate Checklist

| Gate | Verdict |
|------|---------|
| Theoretical validity | Sound — optional param with None default preserves backward compat |
| Environment audit | No existing mechanism provides per-query scope override |
| Prior art | `graph_store.py` uses identical `scopes: list[str] \| None = None` pattern at 8+ sites |
| Technical feasibility | Trivial — ~5 LOC in one file, Python standard optional param idiom |
| Architecture fit | Mirrors existing pattern; both downstream callees (`retrieve()`, `search_similar()`) already accept scopes |
| Implementation approach | `effective = scopes if scopes is not None else self._scopes` in both methods |
| Testing strategy | New unit tests: with-scope override, without-scope fallback; existing tests unchanged |

### 3.2 Implementation Shape

```python
# _search_chunks: add scopes param, resolve effective scopes
def _search_chunks(self, prompt: str, top_k: int, scopes: list[str] | None = None):
    effective = scopes if scopes is not None else self._scopes
    # use effective wherever self._scopes was used


# query: add scopes param, forward to _search_chunks
async def query(self, prompt, *, top_k=5, token_budget=4000, scopes=None):
    raw = self._search_chunks(prompt, top_k, scopes=scopes)
```

### 3.3 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing callers | None | Default is None → existing behavior preserved |
| Thread safety | None | No mutation of `self._scopes`; effective scopes are local |
| `query_for_context()` not updated | Low | Out of scope for #633; can add later if MCP needs it |

### 3.4 Open Consideration

`query_for_context()` also calls `_search_chunks()` but is not in the AC for #633. Since `_search_chunks()` gets the param, `query_for_context()` can forward it in a future task if needed. No action required now.

## 4. Recommendation (.95 confidence)

Proceed with implementation as specified in the AC. The change is trivial, safe, backwards-compatible, and follows an established codebase pattern. No design alternatives need consideration — Option A from #617 research is the clear choice.

**Tier: T1 (Autonomous).** Optional parameter addition with no breaking changes.

Challenge: Skipped — trivial/info-only research. Single viable option with .95 confidence.

## 5. Follow-up Tasks

No new follow-up tasks needed. #633 itself was created as a follow-up from #617 research. Once implemented, #617 can proceed with MCP tool wiring.
