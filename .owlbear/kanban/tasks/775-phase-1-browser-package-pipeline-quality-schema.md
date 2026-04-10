---
id: 775
title: 'Phase 1: Browser Package + Pipeline Quality + Schema'
status: research
priority: critical
created: '2026-04-10T11:45:08.164060+00:00'
updated: '2026-04-10T11:45:08.164060+00:00'
tags:
- browser
- knowledge
- phase-1
parent: 751
depends_on:
- 752
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
# Phase 1: Browser Package + Pipeline Quality + Schema

Needs decomposition: multiple interdependent subtasks across two new packages (serve/browser/, serve/mcp-browser/), knowledge pipeline changes (content cleaner, content safety inversion, extraction prompt), schema migration (v8→v9: source_pages table, source_id FK on documents), and entity model extension (5 corporate types + 2 relation types).

## Scope

1. `owlbear_browser` core library — Edge CDP launcher/manager, content extractor, HTML-to-markdown cleaner
2. `owlbear_mcp_browser` MCP server — navigate, click, type, select, read_text, snapshot tools with URL domain allowlist
3. `AUTHENTICATED_WEB` source type + `_handle_authenticated_web()` handler in RefreshOrchestrator
4. `ContentFetcher` protocol injection into knowledge pipeline
5. Schema v9 migration — `source_pages` lifecycle table, `source_id` FK on `documents`
6. Entity types: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
7. Relation types: GOVERNS, SUPERSEDES_VERSION
8. Content safety predicate inversion — wrap all except file/text source types
9. `LLM_EXTRACTION_PROMPT` update with corporate entity examples
10. Replace-on-change refresh semantics (cascade delete old → re-ingest)

## Dependencies

- Depends on Phase 0 go/no-go (#752)

## Context

- Parent: #751 — Authenticated Content Pipeline
- Research: `.owlbear/research/751-authenticated-content-pipeline.md`
- Brief: `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`
- Architect voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/architect.md`
- Security voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/security.md`
- Data quality voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md`
