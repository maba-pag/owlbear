---
id: 633
title: Add per-query scopes override to KnowledgeQueryService.query()
status: todo
priority: nice-to-have
created: 2026-04-05T12:59:29.4655727+02:00
updated: 2026-04-05T22:30:29.1560589+02:00
tags:
    - scope:knowledge
    - phase-2
class: standard
---

## Summary

Add an optional `scopes: list[str] | None = None` parameter to `KnowledgeQueryService.query()` and `_search_chunks()`. When provided, it overrides the instance-level `self._scopes`. When None (default), existing behavior is preserved.

## Context

Research for #617 found that `query()` only uses `self._scopes` (set at construction time). To support per-query scope filtering from the MCP tool layer, the method needs a runtime override parameter.

See: .owlbear/research/expose-scope-mcp-knowledge-tools.md

## Acceptance Criteria

- [ ] AC1: `query()` accepts optional `scopes: list[str] | None = None` parameter
- [ ] AC2: `_search_chunks()` accepts optional `scopes: list[str] | None = None` parameter
- [ ] AC3: When `scopes` is provided, it is used instead of `self._scopes` for that call
- [ ] AC4: When `scopes` is None (default), `self._scopes` is used (preserves existing behavior)
- [ ] AC5: Existing tests pass unchanged

## Files Affected

- serve/knowledge/src/owlbear_knowledge/query_service.py (query, _search_chunks signatures)
- serve/knowledge/tests/ (new tests for scopes override)

## Notes

- ~5 LOC change. Fully backwards-compatible.
- This is a prerequisite for #617 (expose scope params in MCP tools).

[[2026-04-05]] Sun 20:50
## Research
- Research doc: .owlbear/research/per-query-scopes-override.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Proceed as specified — add `scopes` param to `query()` and `_search_chunks()` using established `effective = scopes if scopes is not None else self._scopes` idiom (confidence: .95)
- Follow-up tasks created: none (task is already a follow-up from #617 research)
- Decision requests: none
- Note: `query_for_context()` also calls `_search_chunks()` but is out of scope for this task

[[2026-04-05]] Sun 22:30
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One change: add scopes param to query() and _search_chunks() |
| Interface clarity | PASS | AC1-AC4 are precise, testable. Inputs/outputs/side-effects clear |
| Dependency correctness | PASS | No dependencies needed. Self-contained within query_service.py |
| Module layering | PASS | Change is within serve/knowledge/ only. No cross-package imports |
| TDD compliance | PASS | Test-writer will derive tests from AC1-AC4. Files Affected lists test dir |
| KISS/YAGNI | PASS | ~5 LOC. Minimal scope. No hypothetical requirements |
| Premise challenge | PASS | Required prerequisite for #617. No existing per-query scope override mechanism |
| Pattern consistency | PASS | Follows established scopes: list[str] | None = None pattern (8+ sites in graph_store.py). Both downstream callees already accept scopes |
| Security surface | PASS | No new system boundaries. Scope filtering is internal |
| Single domain | PASS | Only touches serve/knowledge/ — knowledge domain |

### Failure Mode Map
No new failure modes. Replaces self._scopes reads with local effective variable. Existing exception handling unchanged.

### Challenge Results
- Challenger: RECONSIDER (confidence 0.65)
- Architect response: OVERRIDE — all 5 concerns dismissed:
  1. Keyword-only vs positional for _search_chunks(): private method, implementation detail for builder
  2. query_for_context() inconsistency: intentionally out of scope per research doc S3.4. YAGNI
  3. Empty list semantics: pre-existing behavior, not introduced by this task
  4. Missing test AC: pipeline handles this — test-writer derives tests from AC1-AC4
  5. Positional vs keyword mismatch: same as 1 — implementation detail

### Codebase Evidence
- query_service.py:68-81: _search_chunks() uses self._scopes in retriever path (L71) and vector path (L78-79)
- retrieval.py:86: retrieve(query, top_k, scopes) already accepts scopes
- qdrant.py:151: search_similar() accepts scopes filter
- graph_store.py: 8+ sites use identical pattern
- tests/test_knowledge_engine_extraction.py: existing tests use keyword args — backward compatible
- tests/test_query_service_160.py:217: existing tests verify instance-level scopes forwarding — unaffected

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC precise, architecture sound, codebase patterns verified.
