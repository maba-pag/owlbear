---
id: 1558
title: Ideate knowledge source lifecycle ownership
status: archived
priority: important
created: 2026-05-14T17:24:27.895979+00:00
updated: 2026-05-18T03:31:50.461584+02:00
tags:
  - scope:knowledge
  - type:ideation
  - blocked-by-design
parent:
depends_on:
  - 1556
  - 1557
blocked: false
block_reason: DR pending
claimed_at:
archival_reason: completed
archival_refs: []
---
Context:
Knowledge module audit found that source lifecycle is modeled but not yet operable as a user workflow. Sources have scope, fetch method, enabled state, priority, and enrichment flags, but the active workflow does not yet provide a clear owner for registering, editing, disabling, deleting, or correcting sources over time.

This is intentionally not a build task yet. Core source identity and enrichment graph persistence must be repaired first, then a tiny pilot ingestion should provide evidence about the real source-management pain points.

Objective:
Run a user-led ideation/design pass to decide where source lifecycle belongs: MCP tools, manifest workflow, Cockpit UI, or a combination.

Acceptance Criteria:
- [ ] Core dependency tasks #1556 and #1557 are complete or no longer blocking this decision.
- [ ] A tiny pilot ingestion with a few representative sources has been run or explicitly waived by the user.
- [ ] User decides the source lifecycle owner: MCP tool surface, manifest files, Cockpit surface, or hybrid approach.
- [ ] Decision covers at minimum: register source, edit fetch method, toggle enrichment, inspect source health, remove bad source data, and preserve rebuildability.
- [ ] Follow-up build tasks are created only after the ownership decision is made.

Out of scope:
- Implementing source lifecycle tools or UI in this task.
- Full KB ingestion.
- Changing the intentional manual VS Code-agent enrichment model.
2026-05-14T18:53:31+00:00


Audit amendment — authenticated source support:
Finding 9 added this explicit ideation requirement. The ownership decision must cover authenticated/browser-backed source ingestion and refresh: where `fetch_method` is stored/edited, how HTTP-first validation falls back to browser fetching, which agent/tool is allowed to drive browser automation, and how source refresh behaves when browser fetching is required. This does not authorize implementation before the ideation task is unblocked.
2026-05-15T01:32:41+00:00


Audit refinement — authenticated web refresh must not report silent success when unwired:
`RefreshOrchestrator._handle_authenticated_web(...)` currently returns a zero-count result with no errors when `content_fetcher` is not configured. The outer `refresh(...)` then updates `last_refreshed_at`, making an unwired/no-op refresh look like a completed refresh.

Design constraint for this ideation:
- Authenticated/browser-backed sources need an explicit lifecycle state for unsupported, unwired, skipped, or failed refresh attempts.
- A missing content fetcher must not silently update source metadata as if a refresh happened.
- Decide whether the future behavior should be `failed`, `skipped`, `disabled/unsupported`, or a richer source-health state, and document how MCP `refresh_source` should surface it.
2026-05-15T03:50:43+00:00


Audit refinement — source refresh errors must be visible to operators:
The active `refresh_source(...)` MCP tool returns only `source_id`, `refreshed`, `skipped`, and `failed`, even though `RefreshResult` carries `errors` and source records store `last_error`. A caller can see a failure count without the failure reason.

Design constraint for this ideation:
- Source lifecycle ownership must define where refresh errors and source health are surfaced: MCP return payload, `list_sources`, Cockpit, manifest report, or a combination.
- `refresh_source` should not hide available error messages once source-health semantics are decided.
- The decision should distinguish user-facing error summaries from verbose logs/debug traces.
2026-05-15T03:58:44+00:00


Audit refinement — direct-ingest source records need explicit lifecycle semantics:
`ingest_document(..., source_url=...)` auto-creates a `KnowledgeSource` with `source_type=AUTHENTICATED_WEB`, `fetch_method="url"`, and `config={"url": source_url}`. Authenticated refresh paths expect `config["urls"]` as a list, so these direct-ingest source records can look refreshable while being incompatible with refresh behavior.

Design constraint for this ideation:
- Decide whether direct-ingest `source_url` records are one-shot/manual provenance records, refreshable managed sources, or candidates that must be converted before refresh.
- Define the required `source_type`, `fetch_method`, and `config` shape for each lifecycle state.
- `refresh_source` should not silently no-op on one-shot/manual source records that are not refreshable.

## ideation done
follow up tasks created: #1650 and children #1651-#1655.

[[2026-05-18T03:31:50+02:00]]
## Audit
### Regression Detection
- Ideation task — zero code changes (only .owlbear/briefs/ and .owlbear/kanban/ files)
- No test domains affected per test domain mapping (.owlbear/ → skip)
- Regression verdict: PASS (no code to regress)

### Intent Verification
- Scope alignment: PASS — all changes in .owlbear/briefs/draft-knowledge-source-lifecycle/ (17 files) and .owlbear/kanban/ (follow-up tasks). Correct ideation domain.
- Purpose match: PASS — AC asked for ownership decision + follow-up tasks. D2 resolved ownership (narrow scope on existing MCP surface, user-accepted). Follow-ups #1650-#1655 created with structured decomposition and dependency graph.
- AC coverage: Dependencies #1556/#1557 archived. Brief covers register (D2: ingest_document sufficient), inspect health (O1), remove data (O4), edit/toggle (D2: deferred at this scale), refresh honesty (O2/D3), direct-ingest typing (O3/D4). Pilot ingestion superseded by challenger code-analysis that drove D2 narrow scope.
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was specific and verifiable for ideation. All 5 criteria addressable. Minor gap: pilot ingestion criterion somewhat rigid but included \"explicitly waived\" escape hatch. D2 decision quality excellent — two independent challengers converged on narrow scope.

### Commit Integrity
- Upstream commit presence: PASS
  - Phase 1 discovery: 6641c09e
  - Phase 2 mediation: 0e911f82
  - Follow-up tasks: 17b7360c (creates #1650-#1655)
- Kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
