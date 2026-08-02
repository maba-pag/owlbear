---
id: 1262
title: Extend SSE watcher to recursive kanban_dir with typed multi-surface 
  events
status: archived
priority: medium
created: 2026-05-01T09:53:38.519349+00:00
updated: 2026-05-02T11:53:39.805646+00:00
tags:
- cockpit
- backend
parent: 1236
depends_on:
- 1234
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1234 (tasks-only SSE) lands, refactor the watcher from `awatch(tasks_dir, recursive=False)` to `awatch(kanban_dir, recursive=True)` with path-based classification. Emit typed events: `tasks-changed`, `decisions-changed`, `activity-changed`. Add watch filter that accepts tasks/*.md (not .tmp-), decisions/pending/*.md, and activity.jsonl. See .owlbear/research/1236-extend-sse-decisions-activity.md

## Acceptance Criteria

- [ ] AC1: Watch filter accepts paths matching: (a) `tasks/*.md` — direct children only (depth=1; nested paths like `tasks/sub/x.md` must be rejected), excluding `.tmp-` prefix, (b) `decisions/pending/*.md` — direct children only, (c) exact `activity.jsonl` path; rejects all other paths under `kanban_dir` (td:2)
- [ ] AC2: Path classification returns `"tasks-changed"` | `"decisions-changed"` | `"activity-changed"` | `None` based on which surface the path belongs to; only direct children of each surface directory qualify — nested descendants return `None`; filter and classifier require board-specific paths (`engine.tasks_dir`, decisions/pending dir, activity.jsonl path) (td:2)
- [ ] AC3: `awatch` uses `engine.kanban_dir` with `recursive=True` replacing the current `engine.tasks_dir` with `recursive=False` (td:1)
- [ ] AC4: Each change batch yields exactly one SSE event per distinct surface type present — `event={type}` and `data={"mtime": <max_st_mtime_ns>}`; multiple same-type paths in one batch coalesce into that single event with the maximum mtime; if all paths for a type are deleted (stat fails), no event is emitted for that type (td:2)
- [ ] AC5: Missing `kanban_dir` → stream returns immediately, no events, no crash (td:1)

## Builder Guidance

- Existing implementation in `serve/cockpit/src/owlbear_cockpit/routes/events.py` is correct and complete — builder was done as of commit 4d8931e1. This cycle is **test-only**.
- **Test gaps to fill (from second review, confidence 0.83):**
  1. AC1/AC2: No nested-descendant rejection tests exist. The `_is_direct_md` helper (line 26) enforces depth=1, but no test supplies `tasks/subdir/x.md` or `decisions/pending/subdir/x.md` and asserts rejection/None. Add these.
  2. AC4: `test_per_surface_mtime_is_max_of_paths_for_that_surface` asserts the first `tasks-changed` mtime but does not prove exactly one `tasks-changed` event was emitted for the batch. A buggy implementation emitting multiple same-type events per batch would pass. Assert exact event count per type.
- Existing `test_cockpit_events_1234.py` encodes stale pre-1262 expectations — informational context only, not blocking.
- Research pseudocode in `.owlbear/research/1236-extend-sse-decisions-activity.md` §3.3–§3.4 provides reference implementation.
- `decisions/pending/` may not exist on disk at startup; recursive watch on `kanban_dir` handles late-created directories automatically.

[[2026-05-02]]
## Research

**Validation pass** — parent research (.owlbear/research/1236-extend-sse-decisions-activity.md) covers this task comprehensively. Findings confirmed against live code:

| Check | Result |
|-------|--------|
| Dep #1234 (tasks-only SSE) | ✓ Done (archived) |
| Dep #1235 (useEventSource hook) | ✓ Done (archived) |
| `engine.kanban_dir` → Path property | ✓ Confirmed |
| `engine.tasks_dir` → Path property | ✓ Confirmed |
| decisions path: `kanban_dir / "decisions" / "pending"` | ✓ Matches `deps.get_decisions_dir` |
| activity path: `kanban_dir / "activity.jsonl"` | ✓ Matches `activity_store._ACTIVITY_FILE` |
| Current events.py: awatch(tasks_dir, recursive=False) | ✓ ~65 LOC, tasks-only |
| decisions/pending dir doesn't exist on disk | ✓ Recursive watch handles this |
| Frontend follow-ups exist (#1263, #1264) | ✓ Both at research status |

**Implementation scope:** ~20 LOC delta — replace `awatch(tasks_dir, recursive=False)` with `awatch(kanban_dir, recursive=True)`, add path-based `watch_filter` + `classify()`, emit typed events per research doc §3.3.

**Classification:** T1 — Autonomous. Extends existing SSE transport with additional event types. No new capability, same architecture.

**Confidence:** 0.85 (high — validated against live code, all deps satisfied, clear pseudocode in parent research)

[[2026-05-02]]
## Architecture Review (first pass)

Approved — 5 verifiable AC lines with td annotations and builder guidance. Challenger raised concerns about AC contradiction and helper contract ambiguity; resolved by removing contradictory AC6, adding builder guidance. Advanced to todo.

## Test-Writer Notes (first pass)
- Test file: tests/test_cockpit_events_1262.py
- 19 tests, all FAIL (RED phase). Commit: 1bf6414d

## Builder Notes
- Implementation: updated serve/cockpit/src/owlbear_cockpit/routes/events.py
- Switched watcher from engine.tasks_dir (non-recursive) to engine.kanban_dir (recursive)
- 19 TestFromAC tests passed, 96% coverage, lint clean
- Commit: 4d8931e1

## Review Evidence (first pass)
- Confidence: 0.66, Verdict: FAIL
- Gaps: AC1 .tmp- untested, AC2 board-specific negatives missing, AC4 deletion-only suppression missing, AC5 empty-stream unproven

## Test-Writer Notes (retry 1)
- Filled 4 gaps with 5 new tests (surgical fill mode)
- Total: 24 tests, all PASS, 97% coverage
- Builder skip: test-only retry. Commit: 4cda55d2

## Review Evidence (second pass)
- Confidence: 0.83, Verdict: FAIL
- Remaining gaps: AC1/AC2 no nested-descendant rejection tests (`_is_direct_md` depth=1 unproven), AC4 same-type coalescing proof gap (no exact one-event-per-type assertion)
- Implementation confirmed correct; all gaps are test-proof quality only
[[2026-05-02]]
## Architecture Review (re-review after second review FAIL)

### Verdict: APPROVE (REFINE + advance)

### Context
Task returned to backlog after second review cycle (0.83 confidence). Implementation is correct and complete at 97% coverage. All remaining gaps are test-proof quality — no implementation defect found.

### AC Refinements
Three AC lines tightened to eliminate test-writer ambiguity:

| AC | Change | Rationale |
|----|--------|-----------|
| AC1 | Added "direct children only (depth=1; nested paths like `tasks/sub/x.md` must be rejected)" | Glob `tasks/*.md` was technically correct but test-writer twice failed to write nested-descendant rejection tests |
| AC2 | Added "only direct children of each surface directory qualify — nested descendants return `None`" | Same depth=1 proof gap on classifier side |
| AC4 | Changed "yields a separate SSE event" → "yields exactly one SSE event per distinct surface type present"; added "multiple same-type paths in one batch coalesce into that single event" | Previous wording allowed ambiguous "at least one" reading; coalescing proof was missing |

AC3 and AC5 passed both reviews unchanged.

### Builder Guidance Updated
- Flagged as test-only cycle with specific gap descriptions and line references
- Two concrete test additions required: nested-descendant rejection for AC1/AC2, exact event-count assertion for AC4

### Architecture Assessment
No re-evaluation needed — design is sound, implementation validated by reviewer in both passes. The loop-breaker triggered on proof quality, not architectural concerns.

### Challenge
Skipped — this is a refinement pass for an already-approved and implemented task. The original approval challenger results remain valid; the design is unchanged.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED
[[2026-05-02]]
## Test-Writer Notes (retry 2)
- Retry: added 4 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.

**Gap 1 — AC1/AC2: Nested-descendant rejection (3 tests)**
- `TestFromAC_WatchFilter::test_filter_rejects_nested_tasks_subdir_md` — filter returns False for `tasks/subdir/x.md` (depth=2)
- `TestFromAC_WatchFilter::test_filter_rejects_nested_decisions_pending_subdir_md` — filter returns False for `decisions/pending/subdir/dr.md` (depth=2)
- `TestFromAC_Classify::test_nested_tasks_subdir_classified_as_none_no_event` — end-to-end: nested path bypasses filter via mock awatch, classifier returns None, no SSE event emitted

**Gap 2 — AC4: Exact one-event-per-type count (1 test)**
- `TestFromAC_TypedEvents::test_multiple_same_type_tasks_paths_emit_exactly_one_event` — two tasks/*.md in one batch → exactly one `tasks-changed` event (coalescing via dict-keyed accumulation)

**Totals:** 24 existing tests preserved + 4 new → 28 total, all PASS. Lint clean. Commit: ae25f07a
[[2026-05-02]]
## Builder Notes
- Scope: test-only retry validation; no source edits required.
- Files changed: none.
- Tests: 28 passed (`tests/test_cockpit_events_1262.py`), 0 failed, 0 skipped.
- Coverage: 97% on `owlbear_cockpit.routes.events` (quality-runner reported missed lines: 95, 98).
- Ruff: clean (no violations).
- Evidence summary: reviewer-identified proof gaps were test-only; latest test-writer retry added nested-descendant rejection and same-type coalescing count assertions, and the suite passes against current implementation.
- Fixes applied: none in builder phase (implementation already complete from prior builder pass).
[[2026-05-02]]
## Review Evidence
### Test Results
- pytest: 28 passed, 0 failed, 0 skipped on `tests/test_cockpit_events_1262.py`

### Lint
- Ruff: clean on `serve/cockpit/src/owlbear_cockpit/routes/events.py` and `tests/test_cockpit_events_1262.py`

### Coverage
- `owlbear_cockpit.routes.events`: 97% (69 statements, missed lines 95 and 98 only)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | Watch filter allowlist and rejection paths are exercised by `TestFromAC_WatchFilter` at `tests/test_cockpit_events_1262.py:142`, `:155`, `:171`, `:198`, `:210`, `:232`, `:255`, `:273`, and `:288`, matching `_build_watch_filter()` in `serve/cockpit/src/owlbear_cockpit/routes/events.py:35-50` | PASS |
| AC2 | Board-specific classifier positives and negatives are exercised by `TestFromAC_Classify` at `tests/test_cockpit_events_1262.py:315`, `:404`, `:443`, `:484`, `:526`, and `:569`, matching `_classify_path()` in `serve/cockpit/src/owlbear_cockpit/routes/events.py:57-68` | PASS |
| AC3 | `awatch` target and recursion are asserted at `tests/test_cockpit_events_1262.py:619` and `:636`, matching the callsite in `serve/cockpit/src/owlbear_cockpit/routes/events.py:87-92` | PASS |
| AC4 | Typed multi-surface events, per-surface max mtime, deletion suppression, and exact same-type coalescing are exercised by `TestFromAC_TypedEvents` at `tests/test_cockpit_events_1262.py:655`, `:758`, `:806`, `:862`, `:929`, `:982`, and `:1040`, matching the per-type accumulation and emission logic in `serve/cockpit/src/owlbear_cockpit/routes/events.py:100-120` | PASS |
| AC5 | Missing-board short-circuit and empty-stream behavior are asserted at `tests/test_cockpit_events_1262.py:1092` and `:1140`, matching the early return guard in `serve/cockpit/src/owlbear_cockpit/routes/events.py:79-80` | PASS |

#### Security Review
- No issues found. The route normalizes paths and restricts them to board-local watched surfaces before classification or emission.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found in the current file.
- No commit diff or earlier file snapshot was provided for a strict immutability comparison, so confidence is reduced slightly rather than failing on integrity.

#### Test Quality
- Prior proof gaps are addressed: nested descendant rejection now exists for tasks and decisions in the filter tests, nested classifier rejection exists end-to-end for tasks, and exact same-type coalescing is asserted directly at `tests/test_cockpit_events_1262.py:1040`.
- I reviewed the remaining code-reader concerns and did not treat them as blocking. `_classify_path()` shares `_is_direct_md()` across tasks and decisions in `serve/cockpit/src/owlbear_cockpit/routes/events.py:57-68`, and coalescing is surface-agnostic through the `latest_mtimes` dictionary in `serve/cockpit/src/owlbear_cockpit/routes/events.py:100-120`.

#### Data Safety
- No issues found. Per-batch state is local, and delete-after-notify races are handled by `FileNotFoundError` suppression before event emission.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Filter branches in `serve/cockpit/src/owlbear_cockpit/routes/events.py:35-50`; allow/reject coverage in `tests/test_cockpit_events_1262.py:142-302` | `TestFromAC_WatchFilter` | PASS |
| AC2 | Classifier branches in `serve/cockpit/src/owlbear_cockpit/routes/events.py:57-68`; board-specific event/no-event coverage in `tests/test_cockpit_events_1262.py:310-601` | `TestFromAC_Classify` | PASS |
| AC3 | Watch target callsite in `serve/cockpit/src/owlbear_cockpit/routes/events.py:87-92`; assertions in `tests/test_cockpit_events_1262.py:615-647` | `TestFromAC_AWatchTarget` | PASS |
| AC4 | Per-surface batching logic in `serve/cockpit/src/owlbear_cockpit/routes/events.py:100-120`; event and mtime coverage in `tests/test_cockpit_events_1262.py:655-1079` | `TestFromAC_TypedEvents` | PASS |
| AC5 | Missing-board guard in `serve/cockpit/src/owlbear_cockpit/routes/events.py:79-80`; empty-stream coverage in `tests/test_cockpit_events_1262.py:1087-1178` | `TestFromAC_MissingKanbanDir` | PASS |

### Deductions
- Small confidence deduction: no diff/baseline was available for a strict `TestFromAC_*` immutability check.
- Small confidence deduction: part of the AC2 and AC4 proof is indirect through the shared depth helper and the generic per-surface coalescing logic rather than duplicated per-surface exact-count tests.

### Verdict
- PASS
- Confidence: 0.91
- Action: advance to docs
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/cockpit/README.md` Dependencies table references SSE endpoint and watchfiles — still accurate after multi-surface extension. No section describes specific event types; existing description ("invalidation endpoint") remains correct. No update needed. |
| 2 | Module docstrings | Yes | Verified | All public functions in `serve/cockpit/src/owlbear_cockpit/routes/events.py` have accurate docstrings: module, `_resolve`, `_is_direct_md`, `_build_watch_filter`, `_classify_path`, `events` route. No updates needed. |
| 3 | External attribution | No | N/A | No external patterns used — internal extension of existing watchfiles/SSE architecture. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1236-extend-sse-decisions-activity.md` exists and is linked in task body. Follow-ups #1263 and #1264 noted in research section. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**` — matches `serve/cockpit/src/owlbear_cockpit/routes/events.py`. Footer updated to `Last verified: 2026-05-02 (14303b97)`. Committed as `5d0f94d5`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. Builder changed `events.py` in-place; no orphaned docs. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/events.py` | IN (docstrings) | Verified — all docstrings accurate |
| `tests/test_cockpit_events_1262.py` | OUT (test file) | N/A |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `2026-05-02 (14303b97)`, committed `5d0f94d5`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`1262-*` — no files)

[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Watch filter accepts tasks/*.md (depth=1), decisions/pending/*.md (depth=1), activity.jsonl; rejects .tmp- and all other | `_build_watch_filter` at events.py:35-50, `_is_direct_md` depth=1 check at :26-31; 9 filter tests in test_cockpit_events_1262.py:142-302 including nested rejection at :255, :273, :288 | PASS |
| AC2: Path classification returns typed event names or None; only direct children qualify | `_classify_path` at events.py:57-68; classifier tests at test_cockpit_events_1262.py:315-601 including nested-None at :569 | PASS |
| AC3: awatch uses engine.kanban_dir with recursive=True | Callsite at events.py:91-92; assertions at test_cockpit_events_1262.py:619, :636 | PASS |
| AC4: One SSE event per distinct surface type per batch, max mtime, deleted paths suppressed | `latest_mtimes` dict accumulation at events.py:100-120; typed event tests at test_cockpit_events_1262.py:655-1079 including exact-count at :1040 | PASS |
| AC5: Missing kanban_dir → immediate return, no crash | Guard at events.py:79-80; empty-stream tests at test_cockpit_events_1262.py:1092, :1140 | PASS |

### Test Results
- pytest: 3597 passed, 131 failed (0 in task-scoped test_cockpit_events_1262.py; 10 in stale test_cockpit_events_1234.py due to superseded API — architect-acknowledged; 121 pre-existing unrelated failures)
- ruff: 3 violations, all in unrelated packages (knowledge, mcp-knowledge, orchestrator/examples)

### Commit Integrity
| Commit | Type | Agent |
|--------|------|-------|
| 1bf6414d | test (RED) | test-writer |
| 4d8931e1 | feat (GREEN) | builder |
| 4cda55d2 | test (gap fill) | test-writer retry 1 |
| ae25f07a | test (depth/count) | test-writer retry 2 |
| 5d0f94d5 | docs (diagram footer) | doc-writer |

### Architect Quality: 4/5
AC lines were specific and testable with td annotations. Initial AC wording for depth and coalescing was ambiguous enough to require two reviewer FAILs and an architect re-review pass to tighten. Final AC is exemplary — the loop was caused by insufficient initial precision, not missing concepts.

### Deduction Breakdown
- -.02: 10 stale test failures in test_cockpit_events_1234.py caused by API rename (acknowledged by architect as "not blocking" but no follow-up task created for cleanup)

### Confidence: 0.98
### Action: archive