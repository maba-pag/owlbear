---
id: 633
title: Add per-query scopes override to KnowledgeQueryService.query()
status: ideation
priority: nice-to-have
created: 2026-04-05T12:59:29.4655727+02:00
updated: 2026-04-05T12:59:29.4655727+02:00
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
