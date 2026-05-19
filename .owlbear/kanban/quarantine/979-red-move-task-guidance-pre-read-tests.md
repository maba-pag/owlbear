---
id: 979
title: 'RED: move_task guidance + pre-read tests'
status: archived
priority: needed
created: 2026-04-18T21:18:15.559609+00:00
updated: 2026-04-19T12:20:39.347267+00:00
tags:
- scope:mcp
- scope:kanban
- type:test
parent: 973
depends_on:
- 976
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. RED phase. Depends on guidance module from #976.

## Acceptance Criteria

File: `serve/mcp-kanban/tests/test_guidance_integration.py`

- `move_task` to a status > 1 slot ahead of prior status returns forward-skip message in `guidance`
- `move_task` to adjacent status (1-slot forward) returns empty `guidance`
- `move_task` backward returns empty `guidance`
- `move_task` to "archived" returns empty `guidance` (archive is excluded from skip detection per D6)
- `move_task` pre-reads the prior status via `_show_validated()` before calling engine

All tests must FAIL (server.py not yet wired with pre-read + collect_guidance).
[[2026-04-19]]

## Architecture Review

### Verdict: REJECT (stale — work already completed)

**Stale task.** All work described by this task was completed by sibling tasks under the same parent #973 epic, which is now archived.

**Evidence:**

- Parent #973 (Block-Time Guidance from owlbear-kanban MCP): **archived**
- Dependency #976 (GREEN: KanbanTask.guidance field + guidance.py module): **archived**
- Sibling #991 (Wire guidance into `move_task` with forward-skip detection): **archived**
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L209–227: `move_task` already calls `_show_validated()` pre-read and `collect_guidance("move", ...)` — the exact wiring this task's tests are meant to drive
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py`: integration tests already cover all 5 AC items (forward-skip >1 slot, adjacent 1-slot, backward, archive exclusion, pre-read via implicit guidance content assertions)

**AC premise is false:** Task body states "All tests must FAIL (server.py not yet wired with pre-read + collect_guidance)" — but server.py is already wired. Tests would PASS, not fail.

**Recommendation:** Archive this task as a stale artifact of the completed #973 epic. No further pipeline processing needed.
[[2026-04-19]]

## Research

**Verdict: Stale — archive immediately.** All work described by this task was completed by sibling tasks under parent #973 (now archived).

### Evidence verified

| AC item | Test / Code | Result |
|---------|-------------|--------|
| Forward skip >1 slot → guidance | `test_forward_skip_more_than_one_slot_returns_guidance` | PASS |
| Adjacent 1-slot → empty guidance | `test_forward_skip_one_slot_returns_empty_guidance` | PASS |
| Backward → empty guidance | `test_backward_move_returns_empty_guidance` | PASS |
| Archive → empty guidance | `test_archive_move_returns_empty_guidance` | PASS |
| Pre-reads via `_show_validated()` | `server.py` L216 + implicit in all test results | Wired |

- Parent #973, dependency #976, sibling #991: all archived
- `server.py` L213-230: `move_task` already calls `_show_validated()` and `collect_guidance("move", ...)`
- `test_guidance_move_task_973.py`: 5/5 tests pass (0.34s)
- AC premise "All tests must FAIL" is **false** — implementation complete

### Disposition

- Research doc: none (stale artifact, no open questions)
- Sources: 0 external, codebase-only verification
- Follow-up tasks created: none
- Decision requests: none
- **Recommendation:** Archive directly — no further pipeline processing needed
[[2026-04-19]]

## Architecture Review (2nd pass)

### Verdict: APPROVE (stale — pass-through to archive)

### Independent Verification

| Claim | Verified | Evidence |
|-------|----------|----------|
| Parent #973 archived | YES | show_task returns "not found in tasks" |
| Dependency #976 archived | YES | show_task returns "not found in tasks" |
| server.py pre-read wired | YES | L215: `pre_task = await _show_validated(app_ctx, task_id)` |
| server.py guidance wired | YES | L228: `result.guidance = collect_guidance("move", before=pre_task, ...)` |
| All 5 AC items covered by tests | YES | `test_guidance_move_task_973.py` — 5 test methods map to all AC items |
| AC premise "tests must FAIL" is false | YES | Implementation complete; tests pass |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Stale task — no work to assess |
| Interface clarity | N/A | Work completed under #991 |
| Dependency correctness | PASS | Deps #976 archived (completed) |
| Module layering | N/A | No new code |
| TDD compliance | N/A | RED phase already delivered by #991 |
| KISS/YAGNI | PASS | No excess scope |
| Premise challenge | FAIL | Task premise is false — tests pass, not fail |
| Pattern consistency | N/A | No new code |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | mcp-kanban only |

### Challenge Results

- Challenger: **proceed** (confidence 0.75)
- Concerns raised: (C1) contextlib.suppress makes empty-guidance tests vacuously true, (C2) AC filename mismatch (specifies test_guidance_integration.py, actual is test_guidance_move_task_973.py), (C3) work attributed to #991 not #979, (C4) pre-read verified by code inspection not direct test
- Architect response: **override accepted** — all concerns are precision/auditing issues, not substantive blockers. Pre-existing design patterns (C1) and naming conventions (C2) are not in scope for this stale-task disposition. The core conclusion (work complete, task superseded by #991) is sound.

### Action Taken

Approved to `todo` for pipeline pass-through. Task is stale — all described work was completed by sibling #991 under parent #973 (both archived). The `type:test` pass-through tag is present. Downstream agents should pass through and archive.
[[2026-04-19]]

## Test-Writer Notes

- Non-implementation pass-through: task tagged `type:test`.
- **Stale task** — all work described by this RED phase task was completed by sibling #991 under parent #973 (both archived).
- Existing coverage: `serve/mcp-kanban/tests/test_guidance_move_task_973.py` — 5 tests, all 5 AC items covered, all PASS.
- AC premise "tests must FAIL" is false — `server.py` is already wired with `_show_validated()` pre-read and `collect_guidance("move", ...)`.
- No new test file created. No production code touched.
- Downstream agents should continue pass-through to archive.
[[2026-04-19]]

## Builder Notes

**Pass-through — stale task.**

### Files changed

None. No production code or test files touched.

### Test results

- `serve/mcp-kanban/tests/test_guidance_move_task_973.py`: **5 passed, 0.31s**
- All 5 AC items covered by existing tests (forward-skip >1 slot, 1-slot, backward, archive exclusion, pre-read wiring)

### Lint status

No changes → ruff clean (nothing to check).

### Evidence summary

- AC premise "tests must FAIL" is false — `server.py` was already wired with `_show_validated()` pre-read (L215) and `collect_guidance("move", ...)` (L228) by sibling #991 under parent #973 (both archived).
- All prior pipeline agents (researcher, architect ×2, test-writer) unanimously confirmed stale status.
- Builder verification: 5/5 tests PASS independently.

**Verdict: DONE — advance to review for archive.**
[[2026-04-19]]

## Review Evidence

### Changed Files

None — builder made no changes (correct for stale pass-through disposition).

### Test Results (independently run)

- `serve/mcp-kanban/tests/test_guidance_move_task_973.py`: **5 passed, 0 failed**
- Lint (ruff): **clean**
- Coverage: `owlbear_mcp_kanban.guidance` 77%, `owlbear_mcp_kanban.server` 42%
- Exit codes: pytest 0, ruff 0

### Server.py Wiring Verified

- L215: `pre_task = await _show_validated(app_ctx, task_id)` — pre-read confirmed
- L228: `result.guidance = collect_guidance("move", before=pre_task, after=result, status_names=status_names)` — guidance wiring confirmed

### AC Compliance Table

| AC Line | Test | Status |
|---------|------|--------|
| `move_task` >1 slot forward → guidance message | `test_forward_skip_more_than_one_slot_returns_guidance` — asserts `len(guidance) > 0` | PASS |
| `move_task` 1-slot forward → empty guidance | `test_forward_skip_one_slot_returns_empty_guidance` — asserts `guidance == []` | PASS |
| `move_task` backward → empty guidance | `test_backward_move_returns_empty_guidance` — asserts `guidance == []` | PASS |
| `move_task` to "archived" → empty guidance | `test_archive_move_returns_empty_guidance` — asserts `guidance == []` | PASS |
| Pre-reads via `_show_validated()` before engine | Code inspection L215 + implicitly validated by forward-skip test requiring correct before→after diff | INDIRECT PASS |

### Notes

- `contextlib.suppress(Exception)` wraps guidance collection in server.py (pre-existing, not builder-introduced). Empty-guidance assertions are theoretically vacuous if collect_guidance raises — but `test_forward_skip_more_than_one_slot_returns_guidance` asserts non-empty guidance and **cannot** vacuously pass, providing strong evidence the guidance path is live and functioning.
- AC premise "All tests must FAIL" is false — wiring was completed by sibling #991. All 5 prior pipeline agents independently confirmed stale status. Builder disposition is correct.
- No `TestFromAC_*` tests modified.

### Deductions

- −0.02: contextlib.suppress makes empty-guidance tests theoretically vacuous (pre-existing, not new risk)

### Verdict

Confidence: **0.98** → **PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Builder made zero code changes — stale pass-through. No behavior or API modified. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Verification was codebase-only (server.py + test file inspection). No external patterns used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` file produced — inline research notes were embedded in task body, consistent with stale-task disposition. No follow-up tasks required. |

### Files Updated

None — no documentation changes needed.

### Scratch Files

No `.owlbear/scratch/979-*` files found — nothing to clean.

### Summary

Zero-impact gate pass. Task #979 is a stale artifact of the completed #973 epic. All five prior pipeline agents (researcher, architect ×2, test-writer, builder, reviewer) unanimously confirmed no new work was performed. `## Review Evidence` section present and complete. Advancing to done.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| move_task >1 slot forward returns guidance | test_forward_skip_more_than_one_slot_returns_guidance PASS | PASS |
| move_task 1-slot forward returns empty guidance | test_forward_skip_one_slot_returns_empty_guidance PASS | PASS |
| move_task backward returns empty guidance | test_backward_move_returns_empty_guidance PASS | PASS |
| move_task to "archived" returns empty guidance | test_archive_move_returns_empty_guidance PASS | PASS |
| Pre-reads via _show_validated() before engine | server.py L215 + implicit in all test results | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all failures in serve/mcp-knowledge/tests/ — unrelated to task scope, pre-existing)
- ruff: clean

### Architect Quality: 4/5

Original AC was specific and verifiable. Task became stale because sibling #991 completed the work under parent #973 (both archived). Planning/sequencing issue, not AC quality.

### Deduction Breakdown

- AC lines: all 5 covered by existing tests, no deduction
- Lint: clean, no deduction
- AC quality 4/5, no deduction
- Reviewer evidence: present and detailed, no deduction
- Full-suite failures in task scope: 0, no deduction

### Confidence: 1.00

### Action: archive

Stale task — zero code changes. All work completed by sibling #991 under parent #973 (both archived). All 6 prior pipeline agents unanimously confirmed pass-through disposition. 5/5 AC items verified against existing test file and server.py wiring.
