---
id: 751
title: Authenticated Content Pipeline
status: todo
priority: critical
created: '2026-04-10T10:46:49.305763+00:00'
updated: '2026-04-10T12:01:08.655333+00:00'
tags:
- feature
- knowledge
- browser
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
# Authenticated Content Pipeline

## Investment Tier: Production

## Problem

OwlBear agents lack access to corporate knowledge that spans authenticated intranet sources. When agents perform knowledge-intensive work (security concepts, architecture docs, implementation planning), they can't reference corporate security requirements, solution blueprints, operating procedures, or tool documentation — because that content lives behind SSO on SharePoint, Confluence, internal web tools, and GitHub repos, and no pipeline exists to bring it into the knowledge graph.

The existing ingestion pipeline works for unauthenticated content. The gap is authenticated content: extraction through authenticated sessions, discovery of subpages from user-provided roots, user review of value, and ingestion with cross-source entity interconnection.

## Outcomes

1. Authenticated web content can be extracted programmatically via Edge CDP
2. A source management agent interactively onboards new sources
3. Ingested corporate content is queryable by pipeline agents with source attribution
4. Cross-source concepts are linked in the knowledge graph
5. Content freshness maintained through user-triggered refresh with replace-on-change semantics
6. Source removal cascade-deletes all associated content

## Approach

- Separate browser package (serve/browser/ + serve/mcp-browser/)
- Protocol injection (ContentFetcher) into knowledge pipeline
- AUTHENTICATED_WEB source type
- HTML→markdown cleaner + hash on cleaned content (ships with browser, not after)
- source_pages lifecycle table + source_id FK on documents
- Corporate entity types (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD)
- Full browser tool set with URL domain allowlist at tool level
- IDPI + untrusted content wrapping before go-live

## Delivery Phases

- Phase 0: Technical spike — validate Edge CDP on corporate laptop (go/no-go gate)
- Phase 1: Browser package + pipeline quality + schema + entity types + basic extraction
- Phase 2: Source management agent + interactive discovery + page review UX
- Phase 3: InterDocGraphBuilder for corporate types + cross-source linking
- Phase 4 (optional): SharePoint REST API parallel path

## Brief

Full brief: .owlbear/briefs/draft-browser-knowledge-extraction/brief.md

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/751-authenticated-content-pipeline.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Proceed with brief's approach as-is. Use trafilatura for HTML cleaning in Phase 1. Add trafilatura extraction quality test to Phase 0 spike alongside CDP validation. (confidence: .82)
- Follow-up tasks created: #774 (Phase 0: Edge CDP Technical Spike), #775 (Phase 1: Browser Package + Pipeline Quality + Schema — needs decomposition)
- Decision requests: T3 feature — blocking DR needed after Phase 0 spike completes (go/no-go gate)
- Challenge: FALLBACK — challenger subagent not available

### Key Findings
1. Playwright `connect_over_cdp` confirmed viable for Edge CDP (stable since v1.9, `is_local=True` since v1.58)
2. HTML cleaning comparison: trafilatura (.75 confidence) > readability-lxml + markdownify > markdownify + custom strip. html2text excluded (GPL-3.0)
3. Architecture fit validated: protocol injection, SourceType enum extension, lazy browser import all align with existing DI patterns
4. Content safety gap confirmed: ingest.py wrapping predicate must be inverted (wrap all except file/text)
5. Phased delivery (0→4) validated — dependency chain is correct

### Correction
Task #775 has `depends_on: [752]` which should be `depends_on: [774]` (Phase 0 task). Manual correction needed.
[[2026-04-10]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tracking epic for authenticated content pipeline feature. Children (#774, #775) carry single-responsibility implementation. |
| Interface clarity | PASS | Outcomes 1-6 map cleanly to delivery phases. Children have concrete AC. |
| Dependency correctness | PASS/FLAG | #751 itself has no deps (correct). **#775 has `depends_on: [752]` — must be corrected to `[774]`** (Phase 0 spike). Researcher noted this; manual correction still pending. |
| Module layering | PASS | Separate `serve/browser/` + `serve/mcp-browser/` packages respect layering. Protocol injection (`ContentFetcher`) into knowledge pipeline avoids upward imports. Package boundary test needs `owlbear_browser` and `owlbear_mcp_browser` entries. |
| TDD compliance | PASS | Children will go through RED/GREEN phases. #775 explicitly marked "Needs decomposition" for planner to create TDD task pairs. |
| KISS/YAGNI | PASS | Phase-gated delivery (0→4) with go/no-go gate prevents over-investment. Phase 4 (SharePoint REST) explicitly optional. |
| Premise challenge | PASS | No existing capability for authenticated content extraction. Existing pipeline handles only unauthenticated sources (URL_LIST, FILE_GLOB). Gap is real. |
| Pattern consistency | PASS | SourceType enum extension, RefreshOrchestrator handler dispatch, DI protocol injection, schema migration chain (v8→v9), entity/relation type extension — all follow established codebase patterns. |
| Security surface | PASS | Explicit security measures in approach: URL domain allowlist at tool level, IDPI + untrusted content wrapping, CDP binding to 127.0.0.1 only, content safety predicate inversion (wrap all except file/text). |
| Single domain | PASS | Multi-domain components (browser, knowledge, schema, MCP) are correctly decomposed into separate children. Epic tracks the overall feature. |

### Failure Mode Map

Not applicable — #751 is a tracking epic. Failure modes will be evaluated on implementation children.

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge; high confidence based on codebase evidence

### Codebase Evidence
- `SourceType` enum: `serve/knowledge/src/owlbear_knowledge/models.py:37-42` — extendable with AUTHENTICATED_WEB
- Content safety predicate: `serve/knowledge/src/owlbear_knowledge/ingest.py:191-196` — `_is_url = _meta.get("source_type") == "url"` confirms research finding of needed inversion
- RefreshOrchestrator: `serve/knowledge/src/owlbear_knowledge/refresh.py:86-93` — handler dispatch pattern ready for new source type
- Schema: `serve/knowledge/src/owlbear_knowledge/schema.py:19` — currently v8, v9 migration is natural next step
- Package boundaries: `tests/test_package_boundary.py:43-50` — ALLOWED_IMPORTS needs `owlbear_browser` and `owlbear_mcp_browser` entries

### Action Items
1. **#775 dependency fix**: `depends_on` must be corrected from `[752]` to `[774]` — orchestrator or next agent touching #775 should fix this
2. **Pass-through tag**: Added `quality` tag since #751 is a non-implementation tracking epic

### Verdict: APPROVE
### Action Taken: Advanced #751 to todo. Flagged #775 dependency correction (752→774) for orchestrator action.