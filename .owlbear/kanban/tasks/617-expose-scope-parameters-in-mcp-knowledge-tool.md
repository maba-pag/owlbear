---
id: 617
title: Expose scope parameters in mcp-knowledge tool signatures
status: backlog
priority: nice-to-have
created: 2026-04-05T01:26:23.6081166+02:00
updated: 2026-04-05T13:00:14.5824569+02:00
tags:
    - scope:mcp
    - phase-2
depends_on:
    - 633
class: standard
---

## Summary

Add `scopes` parameter to `search_knowledge`, `scope` parameter to `ingest_document`, and `scope` parameter to `list_entities` MCP tool signatures. All downstream services (KnowledgeQueryService, IngestPipeline, GraphStore) already support these parameters — this task only wires them through to the MCP tool layer.

## Context

Research #616 (docs/research/project-local-knowledge-source.md) recommends scope-based tool parameters as the foundation for project-local knowledge. The existing scope infrastructure from #135 handles the hard work; this task exposes it.

## Acceptance Criteria

- [ ] AC1: `search_knowledge` tool accepts optional `scopes: list[str] | None` parameter, passed to `KnowledgeQueryService.query()`
- [ ] AC2: `ingest_document` tool accepts optional `scope: str = "global"` parameter, passed to `IngestPipeline.ingest_text()`
- [ ] AC3: `list_entities` tool accepts optional `scopes: list[str] | None` parameter, passed to `GraphStore.list_entities()`
- [ ] AC4: Existing tests pass unchanged (default behavior preserved)
- [ ] AC5: New tests verify scope parameters are forwarded correctly

## Files Affected

- serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (search_knowledge, ingest_document, list_entities tool signatures)
- serve/mcp-knowledge/tests/ (new scope-forwarding tests)

## Notes

- Do NOT modify downstream services (KnowledgeQueryService, IngestPipeline, GraphStore) — they already support scope params
- Default values must preserve current behavior (scopes=None, scope="global")

[[2026-04-05]] Sun 13:00
## Research
- Research doc: .owlbear/research/expose-scope-mcp-knowledge-tools.md
- Sources: 7 studied, 5 high-relevance (≥.90)
- Recommendation: Proceed with prerequisite for AC1 gap (confidence: .90)
- Follow-up tasks created: #633 (Add per-query scopes override to KnowledgeQueryService.query()) at ideation
- Decision requests: none — T1 autonomous (optional params with backward-compatible defaults)

## Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Confidence in original: .90
- Key challenges: AC1 gap — query() lacks per-query scopes param; task body incorrectly states downstream "already supports" this
- Researcher response: created prerequisite task #633 to close the gap before #617 implementation

## Key Finding
AC1 (search_knowledge scopes) requires a ~5 LOC prerequisite change to KnowledgeQueryService.query() (#633). AC2 and AC3 are straight wiring with no downstream changes needed. Test pattern: mirror test_list_sources.py scope-forwarding tests.
