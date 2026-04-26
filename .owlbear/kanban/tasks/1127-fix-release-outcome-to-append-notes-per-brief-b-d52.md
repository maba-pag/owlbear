---
id: 1127
title: Fix release outcome to append notes per Brief B D52
status: review
priority: important
created: 2026-04-25 18:07:12.599139+00:00
updated: 2026-04-26T02:27:38.164106+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set."
Current implementation routes `release` through `release_task()` which does NOT append notes.
This is a D52 implementation bug separate from the `fail` outcome restoration (#1125).

Research doc: `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` (parent #1124, defect D2)

## Acceptance Criteria

- [ ] AC1: `AgentView.end_work(outcome="release", note="some note")` on a claimed task appends the timestamped note to the task body before releasing the claim
- [ ] AC2: `AgentView.end_work(outcome="release", note="any text")` on an unclaimed task remains a pure no-op per D55 — no note appended to stored body, no `updated` timestamp advanced
- [ ] AC3: The note-appending for `release` uses the same timestamped format as other outcomes — `now.replace(microsecond=0).isoformat()` newline then note text
- [ ] AC4: Activity event for `release` remains `action="release"`, `detail="released by agent"` — no change to session classification

## Implementation Notes
- **Approved approach: Option C** — Extract `_append_timestamped_note(record, note, now)` helper on `KanbanEngine`, call from both `end_work` (replacing inline note logic at L1409-1412) and `release_task` (when `note` is provided)
- Add `note: str | None = None` parameter to `release_task()` — backwards compatible (CockpitView and direct callers pass no note, defaulting to None)
- AgentView release branch (L2950) passes `note` to `release_task()` when claimed
- Unclaimed release path (L2919-2921) returns early unchanged — no code change needed
- **Downstream consumers of `release_task`:** `CockpitView.release_task` (L3143), cockpit mutation route, direct engine tests — all unaffected (default `None` means no note appended)
- **Existing tests to update:** `test_engine_end_work_1077.py` encodes old no-note behavior for release; test-writer writes new AC-derived tests, builder updates or replaces conflicting old assertions
- Dead guard `if outcome != "release":` in `KanbanEngine.end_work` (L1409) is replaced by the helper call — incidental cleanup, not a separate requirement

## Research
- Research doc: .owlbear/research/1127-release-note-appending.md
- Sources: 12 studied, 8 high-relevance
- Recommendation: Option C — extract `_append_timestamped_note` helper, call from both `end_work` and `release_task` (confidence: 0.75)
- Follow-up tasks created: none (this task moves to backlog)
- Decision requests: none (T1 — autonomous bug fix)

## Challenge Results
- Challenger: reconsider (confidence in original Option B: 0.55)
- Key challenges: DRY risk underpriced, helper extraction captures best of both, dead guard evidence
- Researcher response: revised from B to C — accepted DRY concern and helper proposal

[[2026-04-26]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One defect: release discards notes. One fix. |
| Interface clarity | PASS (after REFINE) | AC1-AC4 mechanically testable; AC2 corrected to include required `note` param |
| Dependency correctness | PASS | No strict dep on #1125 — different code paths (AgentView fail branch vs release_task note param). Overlap in engine.py noted in impl notes. |
| Module layering | PASS | AgentView → release_task delegation is correct direction |
| TDD compliance | PASS | Standard pipeline: test-writer writes RED tests at todo |
| KISS/YAGNI | PASS | Helper with 2 callers justified for DRY (prevents format drift) |
| Premise challenge | PASS | D52 explicitly mandates note appending on release; defect confirmed in code |
| Pattern consistency | PASS | Helper extraction replaces inline logic; backwards-compatible signature change |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine only |

### Failure Mode Map
No new failure modes. `release_task` has existing rollback on OSError. Helper is pure mutation on in-memory record before write.

### Challenge Results (architecture review)
- Research challenger: reconsider (0.55) — revised approach from B to C
- Architecture challenger: reconsider (0.58) — raised authority drift, AC2 API mismatch, surface area, existing test reversal
- Architect response: ACCEPTED concerns. Refined: (1) resolved Option A/C conflict → Option C approved, (2) AC2 now includes required `note` param, (3) added downstream consumer guidance and existing test notes to impl section. Remaining concerns (dead guard cleanup, CockpitView surface) addressed in impl notes as incidental and backwards-compatible respectively.

### Verdict: APPROVE (via REFINE)
### Action Taken: Rewrote Implementation Notes to endorse Option C, tightened AC2/AC3, added builder guidance on downstream consumers and existing tests. Advanced to todo.
[[2026-04-26]]
## Test-Writer Notes
- Test file: tests/test_engine_release_note_1127.py
- Classes: `TestFromAC_ReleaseNoteAppending`, `TestFromAC_ReleaseUnclaimedNoop`, `TestFromAC_ReleaseActivityEvent`
- Tests per category:
  - happy (AC1 compound: note + claim cleared): 3
  - boundary/format (AC3 timestamp format): 4
  - regression guard (AC2 unclaimed no-op): 3
  - regression guard (AC4 activity event): 3
- Total: 13 tests
- FAIL: 7 (AC1: 3, AC3: 4) — note not appended by current release_task() delegation
- PASS: 6 (AC2: 3, AC4: 3) — regression guards for existing correct behavior, per w-tdd-red "X unchanged" exception
- ruff: clean

AC coverage:
| AC | Tests | Status |
|----|-------|--------|
| AC1: claimed release appends note | test_release_claimed_note_in_returned_body, test_release_claimed_note_in_disk_body, test_release_claimed_compound_note_and_claim_cleared | FAIL |
| AC2: unclaimed release is no-op | test_unclaimed_release_body_not_modified_in_memory, test_unclaimed_release_disk_body_unchanged, test_unclaimed_release_updated_timestamp_not_advanced | PASS (regression guard) |
| AC3: same timestamp format as other outcomes | test_release_claimed_note_has_iso_timestamp_prefix, test_release_claimed_note_no_microseconds_in_timestamp, test_release_claimed_note_text_follows_timestamp, test_release_claimed_note_format_matches_other_outcomes | FAIL |
| AC4: activity event unchanged | test_release_claimed_emits_release_action, test_release_claimed_emits_released_by_agent_detail, test_release_claimed_no_end_work_event | PASS (regression guard) |

Commit: 5bb6e3fa
[[2026-04-26]]
## Builder Notes
- Verdict: Reject to test-writer due contradictory test contracts.
- RED verification (quality-runner, scoped): `tests/test_engine_release_note_1127.py` -> 7 failed / 6 passed as expected.
- GREEN attempt: Implemented AC-aligned release-note appending (claimed release path) with shared timestamp format; task tests passed (13/13, ruff clean).
- Conflict discovered in durable regression slice: `serve/kanban/tests/test_engine_end_work_1077.py::TestFromAC_EndWork::test_release_clears_claim_no_status_change_no_note` asserts old behavior (release must NOT append note).
- This conflicts directly with AC1/AC3 for #1127 (release with note must append timestamped note).
- Builder mode forbids test edits; cannot reconcile contradictory contracts in source alone.
- Action required (test-writer): update/replace stale assertion(s) in `serve/kanban/tests/test_engine_end_work_1077.py` to align with D52 release-note behavior.
- Repository state for this task: implementation changes were reverted; no source commit performed.

Post-task reflection:
- Problem: Legacy durable test still encodes pre-D52 behavior.
- Workaround attempted: validated both AC tests and durable slice to isolate contradiction.
- Pattern: Contract shifts need coordinated durable-suite updates alongside new TestFromAC coverage.
- Quality gap: AC-aligned task tests can pass while older durable suites still fail on outdated expectations.
[[2026-04-26]]
## Test-Writer Notes (Retry)
- Retry trigger: builder rejected — `serve/kanban/tests/test_engine_end_work_1077.py::TestFromAC_EndWork::test_release_clears_claim_no_status_change_no_note` asserted old pre-D52 behavior (note NOT appended on release), conflicting with AC1/AC3.
- Fix: renamed test to `test_release_clears_claim_no_status_change`; changed assertion from `"Releasing claim." not in body` → `"Releasing claim." in body` to align with D52 contract.
- Test file (unchanged): `tests/test_engine_release_note_1127.py` — 7 fail (AC1+AC3), 6 pass (AC2+AC4 regression guards)
- Durable file updated: `serve/kanban/tests/test_engine_end_work_1077.py` — `test_release_clears_claim_no_status_change` now fails (note not yet appended) instead of incorrectly passing
- Total across both files: 8 failed, 38 passed
- ruff: clean on both files
- Commit: efb42fae
[[2026-04-26]]
## Builder Notes
- Implementation: updated `serve/kanban/src/owlbear_kanban/engine.py`.
- Fixes applied:
  - Added `KanbanEngine._append_timestamped_note(record, note, now)` helper (Option C).
  - Extended `KanbanEngine.release_task(..., note: str | None = None)` to append timestamped note when provided, then release claim.
  - Replaced inline `end_work` note mutation with shared helper call.
  - Updated `AgentView.end_work` release branch to pass `note` through to `release_task` for claimed-task release.
- Behavioral evidence:
  - Claimed release with note appends timestamped note in-memory and on-disk (AC1/AC3).
  - Unclaimed release path remains pure no-op in `AgentView` (AC2 unchanged).
  - Release activity event remains `action="release"`, detail `released by agent` (AC4 unchanged).
- Verification (quality-runner, scoped):
  - `tests/test_engine_release_note_1127.py` + `serve/kanban/tests/test_engine_end_work_1077.py`: 46 passed, 0 failed.
  - ruff scoped: clean.
  - coverage report on module `owlbear_kanban.engine`: 26% (large legacy module; task-scoped tests are green).
- Additional regression context (quality-runner, full): unrelated existing failures outside task scope; no task-1127 regressions observed.

Post-task reflection:
- Shared helper prevents timestamp-format drift between `end_work` and `release_task`.
- Wiring note through `AgentView` release path preserves release-event classification while fixing D52 behavior.
- Scoped verification plus durable 1077 regression slice was necessary to avoid false-green against legacy expectations.