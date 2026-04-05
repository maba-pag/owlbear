---
id: 616
title: Add project-local knowledge source (.owlbear/knowledge/) to mcp-knowledge
status: backlog
priority: nice-to-have
created: 2026-04-05T00:16:00.8159576+02:00
updated: 2026-04-05T01:27:04.1617457+02:00
tags:
    - scope:mcp
    - phase-2
    - research
class: standard
---

## Summary

Add support for a project-local knowledge source at `.owlbear/knowledge/` in the mcp-knowledge server, in addition to the global KB at `store/knowledge/`. When running in a target project context, the knowledge server should check both locations.

## Context

Split from #606 during architecture review. The parent restructure (#598) summary mentions "knowledge server reads from both store/knowledge/ (global) and .owlbear/knowledge/ (local)" but this is a new feature requiring architectural decisions, not a simple path update.

## Open Questions (needs research)

1. How should two separate SQLite databases be opened and managed? (Two connections in AppContext?)
2. How should search/query results from both sources be merged? (Union? Priority? Dedup?)
3. Which database receives new ingested documents? (Global by default? Configurable?)
4. Should there be a separate env var for the local KB path (e.g., OWLBEAR_LOCAL_KB_PATH)?
5. How does the Qdrant vector store handle dual sources? (Separate collections? Namespace?)

## Acceptance Criteria

Needs research and decomposition before implementation AC can be defined.

## Notes

- Current mcp-knowledge server uses single `_DEFAULT_KB_PATH` with `OWLBEAR_KB_PATH` env var override
- After #602, the global default will be `store/knowledge/knowledge.db`
- The project-local path would be `.owlbear/knowledge/knowledge.db` (if present)

[[2026-04-05]] Sun 01:27
## Research
- Research doc: docs/research/project-local-knowledge-source.md
- Sources: 5 studied, 3 high-relevance (internal #135, LightRAG, mcp-knowledge codebase)
- Recommendation: Scope-based tool params + import/export (confidence: .80)
- Follow-up tasks created: #617 (expose scope params), #618 (import/export tools)
- Decision requests: 1 needed (T3 — adds new MCP tools, changes tool signatures)

## Challenge Results
- Challenger: reconsider (confidence in dual-stack original: .55)
- Key challenges: (1) Qdrant cold-start re-indexing on restart, (2) 5 tool handlers need rewrite not just search, (3) silent schema migration in target repos
- Researcher response: accepted — adopted counter-proposal (scope params + import/export) which leverages existing #135 scope infrastructure

## Tier Classification
- T3 — Mandatory: adds new MCP tools (import_scope, export_scope), changes user-facing tool signatures (search_knowledge gains scopes param). Needs user approval.
- DR needed: scribe unavailable — user should review docs/research/project-local-knowledge-source.md before implementation proceeds.
