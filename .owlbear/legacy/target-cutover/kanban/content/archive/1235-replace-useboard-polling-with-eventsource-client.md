---
id: 1235
title: Replace useBoard polling with EventSource client
status: archived
priority: medium
created: 2026-04-30 16:48:42.996529+00:00
updated: 2026-05-01T14:13:02.212770+00:00
tags:
- cockpit
- frontend
- research
parent:
depends_on:
- 1233
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the 3s setInterval in useBoard.ts with an EventSource connection to /api/events. On receiving tasks-changed event, trigger the existing refetch logic. Implement fallback: after 15s without events or repeated connection failures, resume 3s polling. Integrate with health badge (green=SSE connected, yellow=reconnecting, red=polling fallback). Preserve existing test contracts. See .owlbear/research/1233-realtime-cockpit-updates.md
[[2026-05-01]]
## Research

**Key findings:** EventSource integration requires a new `useEventSource` hook + `paused` option on existing `usePollingFetch`. Critical correction from challenger: fallback trigger must be readyState-based (15s in CONNECTING or permanent CLOSED), NOT "15s without data events" — silence on invalidation-only SSE means no mutations, a healthy state. Architecture uses Option A (separate hooks, separate concerns). Graceful degradation: deploying before backend #1234 is safe — EventSource fails immediately on missing endpoint, fallback activates, behavior identical to today.

**Challenge outcome:** reconsider (0.39 confidence in original). Challenger identified false-fallback contradiction, stale task framing (timer in usePollingFetch not useBoard), initial hydration gap, backend not live. All addressed in revised design. Revised confidence: 0.75.

**Trade-off matrix:** See .owlbear/research/1235-eventsource-client-implementation.md §3.1 and §3.3.

**Follow-up tasks created:** #1259 (paused option), #1260 (useEventSource hook), #1261 (integration orchestration).

**Classification:** T1 — autonomous. Approach already approved in #1233. No new capability (refinement of transport layer), no architecture change.

**Doc:** .owlbear/research/1235-eventsource-client-implementation.md
[[2026-05-01]]


## Acceptance Criteria
- [ ] Research doc `.owlbear/research/1235-eventsource-client-implementation.md` produced with complete design: option selection (A), state machine, hook interfaces, fallback triggers, testing strategy (td:0)
- [ ] Challenger feedback incorporated: fallback trigger is readyState-based (15s CONNECTING stall or permanent CLOSED), not event-silence-based (td:0)
- [ ] Implementation decomposed into subtasks with correct dependency chain: #1259 (paused option), #1260 (useEventSource hook), #1261 (integration orchestration — depends on #1259 + #1260) (td:0)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research + design for one feature (EventSource client integration) |
| Interface clarity | PASS | AC checkboxes verify concrete research deliverables |
| Dependency correctness | PASS | #1233 archived (satisfied). Subtasks #1259/#1260/#1261 depend on this task correctly |
| Module layering | N/A | Research task — no code produced |
| TDD compliance | N/A | Research pass-through (tagged `research`) |
| KISS/YAGNI | PASS | Option A (separate hooks) is simplest viable approach; justified in §3.1 trade-off matrix |
| Premise challenge | PASS | SSE reduces unnecessary polling; EventSource is well-supported; graceful degradation means no regression risk |
| Pattern consistency | PASS | Design follows existing hook separation pattern (usePollingFetch, useConnectionHealth already separate) |
| Security surface | PASS | EventSource is read-only (server→client); no new user input surfaces |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map
N/A — research task; implementation failure modes documented in research doc §3.3 for subtask use.

### Codebase Verification
- `useBoard.ts`: confirmed — uses `usePollingFetch` with `intervalMs: 3000`, calls `markHealthy()`/`updateHealth()` from `useConnectionHealth`
- `usePollingFetch.ts`: confirmed — owns the `setInterval` loop, supports `onSuccess`/`onError` callbacks, no `paused` option yet
- `useConnectionHealth.ts`: confirmed — elapsed-time thresholds at 6000ms (green→yellow) and 15000ms (yellow→red)
- Research doc accurately reflects live code; no stale claims detected

### Design Diverge
Skipped — single recommended approach (Option A) dominates on all criteria (§3.1). No split criteria requiring parallel evaluation.

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (research deliverables, no testable code)
- Research-phase challenger already ran: reconsider (0.39→revised 0.75). Findings integrated into design.

### Test Depth
- Max depth: 0
- Test-writer: SKIP (all td:0)

### Verdict: APPROVE
### Action Taken: Tagged `research` for non-impl pass-through. Added formal AC for research deliverables. Advancing to `todo`.
[[2026-05-01]]
Architecture review complete. Research task with all td:0 AC — tagged `research` for non-impl pass-through. Codebase verified: research doc accurately reflects live hooks (useBoard, usePollingFetch, useConnectionHealth). Design (Option A: separate useEventSource hook + paused option on usePollingFetch) is sound — follows existing hook separation pattern, challenger feedback integrated. Subtasks #1259/#1260/#1261 handle implementation with correct dependency chain.
[[2026-05-01]]
## Test-Writer Notes
- Non-implementation task (tagged `research`) — all AC lines are (td:0).
- Passing through to builder.
[[2026-05-01]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body contains test-writer non-impl pass-through note.
- Passing through to review.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner: no pytest scope executed. The subagent reported test_paths=[] and confirmed this task is a td:0 research pass-through with no claimed code changes.

### Lint
- quality-runner: no lint scope executed. The subagent reported lint_paths=[] and confirmed there are no code files to lint for this task.

### Coverage
- Not applicable. No source-code changes were claimed or required by the acceptance criteria.

### Pass 1 - CRITICAL
- td:0 research task. Per the review workflow, code-reader, coverage, TestFromAC audit, and sequential critical code checks were skipped because all AC lines are research deliverables only.
- Builder process quality: CLEAN. First review cycle; no prior Review Evidence section found in the task file.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Research doc `.owlbear/research/1235-eventsource-client-implementation.md` produced with complete design: option selection (A), state machine, hook interfaces, fallback triggers, testing strategy | `.owlbear/research/1235-eventsource-client-implementation.md:26` and `:34` document Option A; `:36` documents the state machine; `:57` documents revised fallback triggers; `:78` documents hook interfaces; `:104` documents testing strategy. Live-hook grounding still matches current code at `serve/cockpit/web/src/hooks/useBoard.ts:57-58,67-68`, `serve/cockpit/web/src/hooks/usePollingFetch.ts:3,5,20,97`, and `serve/cockpit/web/src/hooks/useConnectionHealth.ts:3,6-7,11`. | N/A (td:0) | PASS |
| Challenger feedback incorporated: fallback trigger is readyState-based (15s CONNECTING stall or permanent CLOSED), not event-silence-based | `.owlbear/research/1235-eventsource-client-implementation.md:10` records the critical correction; `:57` defines fatal CLOSED and prolonged CONNECTING as the fallback triggers. | N/A (td:0) | PASS |
| Implementation decomposed into subtasks with correct dependency chain: #1259, #1260, #1261 with #1261 depending on #1259 + #1260 | `.owlbear/kanban/tasks/1259-add-paused-option-to-usepollingfetch.md:12-13` depends on 1235; `.owlbear/kanban/tasks/1260-create-useeventsource-hook.md:12-13` depends on 1235; `.owlbear/kanban/tasks/1261-integrate-eventsource-into-useboard-with-fallback-orchestration.md:12-15` depends on 1235, 1259, and 1260. | N/A (td:0) | PASS |

### Deductions
- 0.03 informational deduction: `.owlbear/research/1235-eventsource-client-implementation.md:129` says the backend `/api/events` endpoint does not exist yet, while live code now has the route at `serve/cockpit/src/owlbear_cockpit/routes/events.py:27,65,69`. This is time-scoped context drift, not an AC failure, because the follow-up decomposition still matches the live frontend work and the fallback reasoning remains valid.

### Verdict
- PASS. Confidence: 0.95.

### Action
- Review gate satisfied. Advancing to docs.

### Post-task Reflection
- Verifying the spawned task frontmatter directly was necessary; MCP task summaries alone are weaker proof for dependency-chain AC.
- quality-runner handled the empty td:0 scope correctly and provided explicit evidence instead of a false-green test report.
- The only notable gap was time-scoped doc drift around backend availability; it did not invalidate the research design or child-task chain.
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Pure research task — no behavior, API, CLI, or package structure changed; no README references this area |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` lines 16–22 already contain a `## EventSource Client Implementation (Task #1235)` section with WHATWG HTML Spec §9.2, reactuse.com/useeventsource, and github.com/suqingdong/useEventSource entries; all dated 2026-05-01 |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1235-eventsource-client-implementation.md` exists (148 lines); linked in task body ("See .owlbear/research/1235-eventsource-client-implementation.md"); follow-up tasks #1259, #1260, #1261 created and verified in Review Evidence |
| 5 | Diagram maintenance (describes match) | No | N/A | `cockpit.excalidraw` describes `serve/cockpit/src/**` and `serve/cockpit/web/src/**` — no files in those paths were changed (builder confirmed no-code pass-through) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1235-eventsource-client-implementation.md` | IN | Verified — exists, accurate, externally attributed |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc produced with complete design (option A, state machine, hooks, fallback, testing) | `.owlbear/research/1235-eventsource-client-implementation.md` exists (148 lines); sections 3.1 (Option A trade-off), 3.2 (state machine), 3.3 (fallback triggers), 3.4+ (hook interfaces, testing) | PASS |
| Challenger feedback incorporated: readyState-based fallback, not event-silence | Research doc section 1 "Critical correction" + section 3.3 "Fallback Trigger (Revised)" explicitly uses readyState===CLOSED and 15s CONNECTING stall | PASS |
| Subtasks #1259/#1260/#1261 with correct dependency chain | #1259 depends_on=[1235], #1260 depends_on=[1235], #1261 depends_on=[1235,1259,1260]; all reference research doc by section | PASS |

### Research Task Checklist
- Research doc exists: YES
- Follow-up tasks created at research or higher: YES (3 tasks at research)
- Follow-up tasks reference research doc: YES (all 3 cite specific sections)

### Test Results
- pytest: 105 failures, all in unrelated packages (kanban engine/storage/models/decisions) — pre-existing background debt, 0 in task scope
- ruff: 4 violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator) — 0 in task scope
- No code produced by this research task

### Upstream Commits
- c7f7ba74 research(#1235): EventSource client implementation analysis — contains research doc + subtask files

### Architect Quality: 4/5
AC lines are concrete, verifiable research deliverables with specific content requirements. Minor gap: "testing strategy" criterion is loosely defined but easily filled.

### Deduction Breakdown
- AC lines without evidence: 0 (all 3 verified) = -.00
- Lint in scope: 0 = -.00
- AC quality (4, above threshold): -.00
- Reviewer evidence: present, detailed, PASS = -.00
- Suite failures in scope: 0 = -.00

### Confidence: 1.00
### Action: archive