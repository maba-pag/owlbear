---
id: 616
title: Add project-local knowledge source (.owlbear/knowledge/) to mcp-knowledge
status: in-progress
priority: nice-to-have
created: 2026-04-05T00:16:00.8159576+02:00
updated: 2026-04-05T22:25:19.0176485+02:00
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

[[2026-04-05]] Sun 12:45
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Research parent, no implementation scope |
| Interface clarity | N/A | AC is placeholder ("needs research and decomposition") |
| Dependency correctness | PASS | No declared deps; #617/#618 correctly split |
| Module layering | PASS | Recommendation reuses existing scope-column layering from #135 |
| TDD compliance | N/A | Research task, no test surface |
| KISS/YAGNI | PASS | Option C (scope params + import/export) reuses #135 infra |
| Premise challenge | PASS | Scope exposure is a real MCP tool layer gap |
| Pattern consistency | PASS | Follows existing scope-column pattern on Entity, Edge, Document, KnowledgeSource |
| Security surface | N/A | No implementation in this task |
| Single domain | PASS | scope:mcp + knowledge domain only |
| DR verification | FAIL | T3 classified, no DR in pending or resolved |

### Codebase Evidence
- Scope infra confirmed: models.py (scope fields), graph_store.py (scopes param), query_service.py (scopes param), ingest.py (scope param)
- server.py: 5 tool handlers do NOT expose scope params, confirms the gap
- QdrantVectorStore defaults to :memory:, validates cold-start concern for dual-stack
- Research quality: high, challenger interaction improved recommendation

### Challenge Results
- Challenge: SKIPPED (REJECT verdict)

### Verdict: REJECT
T3 research with no approved DR. Task body confirms DR needed. No DR found in .owlbear/decisions/ pending or resolved.

### Action Required
1. User review: .owlbear/research/project-local-knowledge-source.md
2. Create + approve T3 DR for scope-params + import/export approach (Option C)
3. Once approved: move #617 and #618 to backlog for arch review; archive #616 as completed research parent

### Follow-up Quality
- #617 (scope param exposure): precise, verifiable AC, ready for backlog once DR approved
- #618 (import/export tools): reasonable AC but notes "Needs decomposition", planner should process after DR

[[2026-04-05]] Sun 13:30
## Research (validation pass)\n- Existing research doc: .owlbear/research/project-local-knowledge-source.md — validated, all 5 codebase claims confirmed current\n- Scope infra: models.py (scope fields on all 4 model classes), graph_store.py (scopes param), query_service.py (scopes in __init__ only), ingest.py (scope param), server.py (5 tools still lack scope params except list_sources)\n- DR gap resolved: .owlbear/decisions/pending/616-scope-params-import-export.md created (T3 blocking)\n- Follow-up tasks confirmed: #617 (backlog, depends on #633), #618 (backlog, needs decomposition)\n- Sources: already logged in .owlbear/sources/overview.md (4 external, 1 internal)\n- No codebase changes since prior research — all findings hold at .80 confidence\n\n## Challenge Results\n- Challenge: SKIPPED — validation pass of existing research; original challenge (reconsider) already incorporated in prior cycle\n- Confidence in recommendation: .80 (unchanged)

## Decision Resolved

**Status:** Approved (T3 decision)
**Decision:** Option A — Scope-based tool parameters + import/export
**User notes:** i need more depth on the risk: what is the cost of Qdrant cold-start migration on every restart, Qdrant cold-start latency on restart? How risky and how realistic is schema drift in a single-user local-laptop dev setting? how big is the effort actually? (caution, your time estimates are usually off by a factor of 12-24: you say 3 days but really it is 3-6 hours max.)

**Next steps:** #617 and #618 can proceed to implementation. User emphasized that effort estimates need careful calibration (likely 3–6 hours, not 3 days).

[[2026-04-05]] Sun 20:42
## Research (risk depth pass)
- Updated doc: .owlbear/research/project-local-knowledge-source.md § 4a
- Qdrant cold-start: **non-issue for Option C** — `:memory:` cold-start is pre-existing for ALL data (global included). No re-indexing exists today. Option C doesn't change this. Hypothetical re-index: 20–55s for 50–200 chunks (dominated by BGE-M3 model load).
- Schema drift: **near-zero** — Option C uses single DB; init_db() auto-migrates idempotently. Drift was only a concern for rejected dual-stack Option A.
- Effort (calibrated): #617 ~2.5h (scope params + tests), #618 ~4.5h (import/export + tests). Total ~7h, ~300 LOC delta.
- Challenge: SKIPPED — risk-depth pass on approved decision, no new recommendation.
- Confidence: .85 (up from .80; risks analyzed and found lower than anticipated)

[[2026-04-05]] Sun 21:07
## Architecture Review (2nd pass)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Research parent — no implementation scope |
| Interface clarity | N/A | AC is placeholder; implementation AC lives in #617, #618, #633 |
| Dependency correctness | PASS | No deps. Follow-ups correctly structured: #633 → #617 → #618 queryable |
| Module layering | PASS | Recommendation reuses #135 scope-column infra |
| TDD compliance | N/A | Research task, no test surface |
| KISS/YAGNI | PASS | Option C (scope params + import/export) is minimal viable approach |
| Premise challenge | PASS | Scope exposure is a confirmed gap (server.py lacks scope params) |
| Pattern consistency | PASS | Follows existing scope-column pattern |
| Security surface | N/A | No implementation in this task |
| Single domain | PASS | knowledge/mcp domain only |
| DR verification | PASS | .owlbear/decisions/resolved/616-scope-params-import-export.md — approved T3 |

### Research Completeness
- 3 research passes: initial (.80), validation, risk-depth (.85)
- DR approved by user with risk-depth addendum
- Follow-ups: #633 (query scopes prerequisite, backlog), #617 (scope params, backlog, depends #633), #618 (import/export, todo, needs decomposition)
- Note: Original research claimed query() downstream "already supports" per-query scopes. #617 research discovered query() only accepts scopes at construction time. Remediated by creating #633. Pipeline self-corrected.

### Challenge Results
- Challenger: reconsider (0.70) / proceed-if-amended (0.85)
- Concerns: (1) research doc's "already supported" claim incomplete for query(), (2) dependency chain not explicit
- Architect response: accepted — gap caught and remediated by #633 creation during #617 research. Dependency chain explicit in task metadata. Noted here for downstream visibility.

### Verdict: APPROVE
Research parent complete. All deliverables met: research doc, DR approved, risks analyzed per user request, follow-up tasks created with verifiable AC. Advancing to todo for pipeline pass-through.

### Action Taken
- Verified DR approval (.owlbear/decisions/resolved/616-scope-params-import-export.md)
- Confirmed follow-up status: #618 (todo, approved), #617 (backlog), #633 (backlog)
- Noted query() scopes gap for transparency
- Advanced to todo with research pass-through tag (already present)

[[2026-04-05]] Sun 22:25
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.
