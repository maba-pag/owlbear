---
id: 1233
title: Research — WebSocket/SSE real-time updates for cockpit
status: backlog
priority: nice-to-have
created: 2026-04-30 16:31:18.682845+00:00
updated: 2026-04-30T22:37:50.283811+00:00
tags:
- cockpit
- architecture
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace polling with server-push for real-time board updates.

## Context
Currently the cockpit polls /api/tasks every 3s. When MCP or cockpit mutates tasks, the change takes up to 3s to appear. For a "central viewport" this feels laggy.

## Research Questions
- WebSocket vs SSE — which fits FastAPI + React better for this use case?
- How to detect mutations (engine events? file watchers? explicit push after API calls?)
- Impact on deployment (uvicorn workers, connection limits)?
- Fallback to polling when connection drops?
[[2026-04-30]]
## Planning

Created 3 follow-up tasks at research status:

| ID | Title | Tags | Priority | Depends |
|----|-------|------|----------|---------|
| #1234 | Implement SSE endpoint with watchfiles-based file watcher | cockpit, backend | nice-to-have | #1233 |
| #1235 | Replace useBoard polling with EventSource client | cockpit, frontend | nice-to-have | #1233 |
| #1236 | Research — extend SSE to decisions and activity polling | cockpit, architecture | someday | #1233 |

Dependency graph: 1233 → {1234, 1235, 1236} (all three independent of each other, all depend on research completion).
[[2026-04-30]]
## Research

**Key findings:** SSE is the clear transport choice over WebSocket — cockpit only needs server→client push, and SSE gives auto-reconnect, HTTP-native streaming, zero protocol upgrades. Mutation detection via `watchfiles` (OS-native file watcher) catches all sources (cockpit API, MCP, CLI) with ~100ms latency vs. current 3s polling. Invalidation-only event model (push mtime, client refetches) preserves all existing test contracts.

**Trade-off matrix:** See .owlbear/research/1233-realtime-cockpit-updates.md §3.1–3.5

**Follow-up tasks created:** #1234 (SSE backend endpoint), #1235 (EventSource frontend), #1236 (extend to decisions/activity)

**Confidence:** 0.78 — challenger pushed back on scope boundaries and fallback definition; both addressed in final doc. Core SSE verdict was not disputed.
[[2026-04-30]]
## Test-Writer Notes
- Non-implementation task (tagged architecture/research, title "Research —") — no testable Python interfaces, no AC lines.
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Non-implementation task confirmed from Test-Writer Notes in task body.
- No code changes were required.
- No tests or lint executed by builder (pass-through classification).
- Passing through to review.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner: 0 passed, 0 failed, 0 skipped
- Scope note: research-only task; empty scoped inputs produced the expected no-op report, so no pytest execution applied to this task.

### Lint
- quality-runner: clean=true, 0 violations
- Scope note: research-only task; no lint paths applied.

### Coverage
- N/A — research-only task with no implementation scope.

### Live-State Verification
- `serve/cockpit/web/src/hooks/useBoard.ts:52-53,85,112` confirms the current board flow is initial `/api/board` + `/api/tasks` fetch, then 3-second polling of `/api/tasks`.
- `serve/cockpit/web/src/hooks/useScanPolling.ts:3,41` and `serve/cockpit/web/src/hooks/usePendingDRs.ts:3,53` confirm the adjacent decisions/scan surfaces still poll at 60-second intervals.
- Conclusion: the spawned follow-up tasks match current live polling behavior; the failure is not child-task drift.

### Research Question Coverage
| Task question | Evidence | Status |
|---|---|---|
| WebSocket vs SSE — which fits FastAPI + React better? | `.owlbear/research/1233-realtime-cockpit-updates.md:24-41,99` | PASS |
| How to detect mutations? | `.owlbear/research/1233-realtime-cockpit-updates.md:43-59` | PASS |
| Impact on deployment? | `.owlbear/research/1233-realtime-cockpit-updates.md:87-95` | PASS |
| Fallback to polling when connection drops? | `.owlbear/research/1233-realtime-cockpit-updates.md:73-85` | PASS |

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — research-only task, no `TestFromAC_*` classes expected.

#### Security Review
- No code changes or new runtime surface were introduced by this task.

#### Test Integrity
- N/A — no task-scoped tests.

#### Test Quality
- N/A — no task-scoped tests.

#### Data Safety
- N/A — no implementation changes.

#### Implementation-Aware Test Gap Analysis
- N/A — no implementation changes.

#### Necessity Check
- Deferred. This recommendation proposes a T3 architecture change but the mandatory decision path was not created, so necessity cannot be closed inside this review.

#### Builder Process Quality
- CLEAN. One pass-through builder section only: `.owlbear/kanban/tasks/1233-research-websocket-sse-real-time-updates-for-cockpit.md:62-64`.

### Critical Findings
1. **Missing mandatory T3 decision path / authority reconciliation**
   - Existing cockpit authority still locks polling: `.owlbear/briefs/draft-cockpit/decisions.md:19` says `2–5 s. Short-poll the revision counter; no SSE/WebSocket in v1.`
   - The current cockpit brief also reaffirms mtime-scan polling at `.owlbear/briefs/draft-cockpit/brief.md:57`, `.owlbear/briefs/draft-cockpit/brief.md:71`, and `.owlbear/briefs/draft-cockpit/brief.md:119`, while `.owlbear/briefs/draft-cockpit/decisions.md:65` locks `Poll @ 3 s` with mtime-scan as primary change detection.
   - This research recommends overturning that authority at `.owlbear/research/1233-realtime-cockpit-updates.md:99`, and operationalizes it through follow-up tasks `.owlbear/kanban/tasks/1234-implement-sse-endpoint-with-watchfiles-based-file-watcher.md:22` and `.owlbear/kanban/tasks/1235-replace-useboard-polling-with-eventsource-client.md:22`.
   - Search of `.owlbear/decisions/**` for `1233|realtime-cockpit-updates|SSE|WebSocket` returned no matches.
   - Verdict: **FAIL**. This is a T3 architecture change without the mandatory decision record.

2. **External source ledger missing**
   - The research doc records external sources at `.owlbear/research/1233-realtime-cockpit-updates.md:16-20`.
   - `.owlbear/sources/overview.md` contains source-table sections (for example, header at line 7), but search for `1233|realtime-cockpit-updates|germano.dev|digitalbiztalk|sse-starlette|watchfiles` returned no matches.
   - Verdict: **FAIL**. Required research artifact is incomplete.

### Informational Findings
- `.owlbear/research/1233-realtime-cockpit-updates.md:106` claims `watchfiles` is already used by uvicorn for reload, but `serve/cockpit/pyproject.toml:6` currently lists only `owlbear-kanban`, `fastapi`, `uvicorn`, and `pydantic`, and repo search found no manifest entry for `watchfiles` or `sse-starlette`. Treat that mitigation as unverified until packaging is checked explicitly.

### Deductions
- -0.22 missing T3 decision/authority resolution
- -0.15 missing `.owlbear/sources/overview.md` source rows
- -0.05 unevidenced dependency-mitigation claim
- Confidence: 0.58

### Required Follow-up
1. Return the task to backlog for architecture/research correction.
2. Either align the recommendation with existing cockpit polling authority, or create the required T3 decision request that explicitly overturns it.
3. Add task-1233 external sources to `.owlbear/sources/overview.md`.
4. Re-validate the `watchfiles` packaging/dependency claim against actual runtime dependencies before re-advancing.

### Verdict
- FAIL -> backlog

### Post-task Reflection
- Research-only tasks still need artifact governance; `no code changes` does not waive source-log or DR requirements.
- Reading the current cockpit brief/decisions early prevented a false-positive pass on a thoughtful but unsanctioned recommendation.
- Child-task dependency wiring was correct; the failure is governance, not follow-up creation.
[[2026-04-30]]
## Architecture Review

### Context
Research task returned to backlog by reviewer (confidence 0.58) due to two governance failures. Research findings themselves are sound — all 4 questions answered, SSE verdict uncontested by challenger.

### Critical Governance Gap
Existing cockpit brief authority explicitly locks polling:
- `.owlbear/briefs/draft-cockpit/decisions.md:19` — "no SSE/WebSocket in v1"
- `.owlbear/briefs/draft-cockpit/decisions.md:65` — "Poll @ 3s" locked

This research recommends overturning that locked authority (T3 architecture change) without a mandatory Decision Request. Criterion 12 applies.

### Action Taken
1. Created DR via scribe: `.owlbear/decisions/pending/1233-cockpit-polling-vs-sse.md`
   - Option A: Approve SSE, overturn v1 polling lock, unblock #1234/#1235/#1236
   - Option B: Reject SSE, retain polling, archive follow-ups
   - Option C: Defer to v2, retain tasks at someday priority
2. Tagged `type:user-action` — user decision required to resolve authority conflict.
3. Blocked pending DR resolution.

### Remaining Governance Items (post-DR)
- External source ledger: sources from research doc must be logged in `.owlbear/sources/overview.md`
- `watchfiles` dependency claim needs validation against actual `serve/cockpit/pyproject.toml`
- Both items must be resolved before task can re-advance through pipeline

### Verdict: BLOCK
DR pending: `.owlbear/decisions/pending/1233-cockpit-polling-vs-sse.md`
## Decision Resolved

User decision: **A: Approve SSE approach — overturn v1 polling lock**

This overturns the existing cockpit brief authority (`.owlbear/briefs/draft-cockpit/decisions.md:19,65`) and unlocks follow-up implementation tasks #1234/#1235/#1236.

Downstream actions required:
1. Amend `.owlbear/briefs/draft-cockpit/decisions.md` to remove polling lock
2. Approve #1234/#1235/#1236 for architecture review
3. Validate `watchfiles` dependency availability before builder starts
4. Log external sources in `.owlbear/sources/overview.md`
[[2026-04-30]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research task: 4 clearly scoped questions, well bounded |
| Interface clarity | N/A | Research output; follow-up tasks #1234/#1235/#1236 created with correct dependency wiring |
| Dependency correctness | PASS | Follow-up tasks wired correctly |
| Module layering | N/A | Research task |
| TDD compliance | N/A | Research task, no testable Python interface |
| KISS/YAGNI | PASS | Scope bounded to 4 questions; invalidation-only SSE model is minimal |
| Premise challenge | PASS | T3 DR approved (Option A); SSE verdict was uncontested by challenger |
| Pattern consistency | N/A | Research task |
| Security surface | N/A | No code changes introduced |
| Single domain | PASS | cockpit/architecture |

### Failure Mode Map
N/A — research task, no codepath changes.

### Design Diverge
Skipped — research task, no architecture design choices in this review cycle.

### Challenge Results
Skipped — research task; T3 DR resolved (Option A) provides the authority gate.

### Test Depth
All AC lines: td:0 — no testable Python interface.
Test-writer: SKIP

### Verdict: REJECT → research

### Governance resolved
- T3 DR: APPROVED — `resolved/1233-cockpit-polling-vs-sse.md` (Option A, user-approved).
- Tags `type:user-action` and `needs-ideation` removed (DR resolved, research complete).

### Remaining FAIL conditions (from reviewer, still open)

1. **Sources ledger incomplete** — 6 external sources in `.owlbear/research/1233-realtime-cockpit-updates.md` (lines 16–20) have not been added to `.owlbear/sources/overview.md`. Add a `## Real-Time Cockpit Updates (Task #1233)` section with rows for:
   - germano.dev/sse-websockets (2022)
   - digitalbiztalk.com — SSE vs WebSockets 2026
   - Medium — FastAPI SSE implementation (2025)
   - github.com/sysid/sse-starlette
   - github.com/samuelcolvin/watchfiles
   - uvicorn.org/settings — concurrency limits

2. **`watchfiles` dependency claim unverified** — Research doc implies watchfiles is a zero-new-dep addition ("already used by uvicorn for reload"). `serve/cockpit/pyproject.toml` does NOT list `watchfiles` or `uvicorn[standard]`. Either: (a) retract the claim and note watchfiles as a new explicit dependency for #1234 to add, or (b) document the transitive dep path with evidence (e.g. from installed packages or uv.lock). This affects builder scoping for #1234.

### Required action before re-advancing
Researcher must fix both items above and then move #1233 to backlog for a second architect pass.

### Downstream action (tracked separately)
`.owlbear/briefs/draft-cockpit/decisions.md` D6 still states "no SSE/WebSocket in v1". Must be amended to reflect Option A approval. A separate task has been created for this — see new task created alongside this rejection.


**Note from architect:** Brief amendment task created for D6 update — see new task in backlog.
[[2026-04-30]]
## Research

**Correction pass** — fixed two governance failures flagged by architect review:

**1. Sources ledger** — Added `## Real-Time Cockpit Updates (Task #1233)` section to `.owlbear/sources/overview.md` with 6 rows:
- germano.dev/sse-websockets (confirmed URL, valid)
- digitalbiztalk.com SSE vs WebSockets 2026 (domain unresolvable at validation time — flagged in ledger; exact article path unknown)
- Medium FastAPI SSE 2025 (best-match URL: mahdijafaridev.medium.com)
- github.com/sysid/sse-starlette (confirmed)
- github.com/samuelcolvin/watchfiles (confirmed)
- uvicorn.org/settings (confirmed)

**2. watchfiles dependency claim** — Retracted the "already used by uvicorn for reload" mitigation. Verified: `uv pip show watchfiles` → not found; `uvicorn v0.46.0` depends only on `click` + `h11`. `watchfiles` requires `uvicorn[standard]` which is NOT installed. Updated `.owlbear/research/1233-realtime-cockpit-updates.md §4 Risks` to note watchfiles as a **new explicit dependency** that #1234 must add. Task #1234 body already says "Dependency: sse-starlette + watchfiles packages" — consistent.

All three architect pre-conditions now met: T3 DR resolved (Option A), sources ledger complete, watchfiles claim corrected.