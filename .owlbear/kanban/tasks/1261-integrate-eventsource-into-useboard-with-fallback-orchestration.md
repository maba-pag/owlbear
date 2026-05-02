---
id: 1261
title: Integrate EventSource into useBoard with fallback orchestration
status: review
priority: nice-to-have
created: 2026-05-01T09:34:27.630685+00:00
updated: 2026-05-02T02:44:28.698649+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
- 1259
- 1260
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Wire useEventSource into useBoard: SSE open pauses polling, tasks-changed triggers refetchTasks(), SSE failure/stall resumes polling. Update useConnectionHealth to accept transport-state override for health badge (green=SSE open, yellow=reconnecting, red=fallback). See .owlbear/research/1235-eventsource-client-implementation.md §3.4 and §3.6. Depends on the paused-option (#1259) and useEventSource (#1260) tasks.
[[2026-05-02]]
## Research

**Key findings:** All building blocks exist — `useEventSource` (#1260 done), `paused` option (#1259 done), backend `/api/events` endpoint live. Integration is ~30 LOC wiring in `useBoard.ts`:
- Derive `paused = (sseStatus === 'open')` for polling
- `useEffect` on `lastEventMtime` → `refetchTasks()`
- Compute `effectiveHealth` from SSE status (open→green, connecting→yellow, closed→fall through to polling health)

**Decision:** Option Y — health override stays in `useBoard` (local orchestration), NOT pushed into `useConnectionHealth` (kept as generic polling utility). Confidence: 0.85.

**Trade-offs:** See `.owlbear/research/1261-eventsource-board-integration.md` §3.3 table.

**No new follow-up tasks needed** — #1261 is self-contained (implementation = this task at backlog).
[[2026-05-02]]


## Acceptance Criteria

_Supersedes the original task description where they conflict (notably: useConnectionHealth is NOT modified)._

1. `useBoard` calls `useEventSource('/api/events')` and uses its return values for orchestration (td:1)
2. When `sseStatus === 'open'`, `usePollingFetch` receives `paused: true`, suppressing interval-driven polling (td:2)
3. When `lastEventMtime` changes (and SSE is open), `refetchTasks()` is called to fetch fresh task data (td:2)
4. When SSE is not open (`'connecting'` or `'closed'`), `paused` is `false` and polling resumes on its normal interval (td:2)
5. `useBoard` returns `health` (same field name, same `HealthState` type) computed as: `'green'` when sseStatus=`'open'`, `'yellow'` when sseStatus=`'connecting'`, falls through to polling-based `useConnectionHealth` value when sseStatus=`'closed'` (td:2)
6. `useConnectionHealth.ts` is NOT modified — health override is local to `useBoard` (Option Y per research) (td:0)
7. Existing `useBoard` tests pass with a global or per-suite `EventSource` stub/mock added to test infrastructure (td:1)
8. All existing Shell tests pass unchanged — `health` field name preserved in `UseBoardResult` (td:1)

### Builder Notes

- **Test infrastructure:** jsdom has no `EventSource`. Add a global stub in `vitest.setup.ts` that defaults to CLOSED (or mock per-test). Existing useBoard tests must not break.
- **Paused + pending edge case:** `usePollingFetch` suppresses pending-poll drain while paused (line ~89 in usePollingFetch.ts). If an SSE event arrives during an in-flight poll, the refetch queues but won't drain until the next event trigger or paused becomes false. Acceptable — next event catches up.
- **Stale health transient:** When SSE closes after a long open period, polling-based health from `useConnectionHealth` may briefly show stale state until the first successful poll calls `markHealthy()`. Brief transient, acceptable.
- **Reference:** `.owlbear/research/1261-eventsource-board-integration.md` §3.2–3.5
[[2026-05-02]]
## Architecture Review

**Verdict:** APPROVE — AC refined, architecture sound.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 1. useEventSource call | Clear, testable | Kept (td:1) |
| 2. paused=true when SSE open | Specific condition, verified `paused` option exists in usePollingFetch | Kept (td:2) |
| 3. lastEventMtime triggers refetch | Clear trigger + guard (SSE open) | Kept (td:2) — noted paused+pending edge case in builder notes |
| 4. Polling resumes on SSE not-open | Inverse of AC2, covers connecting + closed | Kept (td:2) |
| 5. health field with SSE-aware mapping | Rewrote from original — original said "update useConnectionHealth" which contradicted research Option Y. Now specifies local computation in useBoard, same field name | Refined (td:2) |
| 6. useConnectionHealth unchanged | Added — makes Option Y decision explicit and testable | Added (td:0) |
| 7. Existing useBoard tests pass | Added per challenger finding — jsdom has no EventSource, stub required | Added (td:1) |
| 8. Shell tests pass (field name) | Added per challenger finding — health field name must be preserved | Added (td:1) |

### Architecture Notes

- **Design:** Option Y (health override local to useBoard) is correct — useConnectionHealth is a polling-focused utility, SSE transport awareness doesn't belong there.
- **Module layering:** useBoard → useEventSource, usePollingFetch, useConnectionHealth. All peer hooks, no upward imports. ✓
- **Scope:** ~30 LOC in useBoard.ts + test infrastructure (EventSource mock). Single file change + test file.
- **Original AC contradiction fixed:** Task description said "Update useConnectionHealth" but research chose Option Y. Formalized AC supersedes.

### Dependency Analysis

- #1235 (SSE backend): archived/done — `/api/events` endpoint live
- #1259 (paused option): archived/done — `paused` option confirmed in usePollingFetch.ts
- #1260 (useEventSource): archived/done — hook exists at `serve/cockpit/web/src/hooks/useEventSource.ts`
- No missing dependencies

### Challenger Results

Challenger returned `block` at confidence 0.33. Evaluation:
1. **Test infrastructure** (critical) — Valid. Added AC7 requiring EventSource mock + builder note. Addressed.
2. **Paused+pending race** (critical) — Partially valid. Edge case when SSE event collides with in-flight poll — narrow window, next event catches up. Documented in builder notes. Not a design flaw.
3. **API contract** (moderate) — Valid. Added AC8 preserving `health` field name.
4. **Spec-coherence** (moderate) — Already identified. Fixed by AC rewrite superseding contradictory prose.
Override rationale: all concerns addressable through AC refinement, not architectural changes.
[[2026-05-02]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/useBoard_1261.test.ts
- Classes: TestFromAC_UseBoardSSEIntegration
- Tests per category: happy 6, edge 4, boundary 1, regression 1
- Total: 12 tests, all FAIL
- ESLint: clean

### AC Coverage

| AC | Tests | Category |
|----|-------|----------|
| AC1 (td:1) | creates an EventSource for /api/events on mount | happy |
| AC2 (td:2) | suppresses polling when SSE opens; no fires across multiple intervals; pauses mid-interval | happy, edge, boundary |
| AC3 (td:2) | triggers refetchTasks on tasks-changed event; triggers for each distinct event | happy, edge |
| AC4 (td:2) | polling resumes when SSE closes; polling resumes after SSE stall | happy, edge |
| AC5 (td:2) | health=green overrides degraded polling; health=yellow overrides healthy polling; health stays green during extended SSE-open | happy, happy, edge |
| AC6 (td:0) | skipped |  |
| AC7 (td:1) | returns all UseBoardResult fields with EventSource globally available | regression |
| AC8 (td:1) | folded into AC7 regression guard (health field name check) |  |

### Infrastructure Note
MockEventSource defined per-suite (same shape as useEventSource_1260.test.ts). No changes to vitest.setup.ts — builder should add a global closed-by-default stub there per AC7 builder note.
[[2026-05-02]]
## Builder Notes
- Implementation: integrated SSE orchestration in serve/cockpit/web/src/hooks/useBoard.ts and added a closed-by-default global EventSource jsdom stub in serve/cockpit/web/vitest.setup.ts.
- AC mapping:
  - AC1: useBoard now calls useEventSource('/api/events').
  - AC2/AC4: usePollingFetch now receives paused: sseStatus === 'open' (poll suppressed on open, resumes when not open).
  - AC3: useEffect now refetches tasks when lastEventMtime changes while SSE is open.
  - AC5: health remains the existing field name and type, computed locally as green(open) / yellow(connecting) / polling health(closed).
  - AC6: useConnectionHealth.ts unchanged.
  - AC7/AC8: test infra supports EventSource globally without changing useBoard result shape.
- Fixes applied during GREEN: removed unstable refetch loop by routing refetchTasks through a ref-backed effect trigger keyed only to lastEventMtime and sseStatus.
- Tests: 26 passed, 0 failed, 0 skipped (scoped run: useBoard_1261 + existing useBoard tests).
- Coverage: useBoard.ts 93.87% statements, 57.69% branches, 100% functions, 93.87% lines.
- Lint: ESLint clean (0 violations) on changed files.
- Commit: 2b26a212 (feat: integrate SSE orchestration in useBoard (#1261, builder)).

### Evidence Summary
- quality-runner scoped verification: vitest exit 0, eslint exit 0, no failures.
- Initial post-edit run had 4 failing tests; resolved by stabilizing SSE-triggered refetch effect dependencies.