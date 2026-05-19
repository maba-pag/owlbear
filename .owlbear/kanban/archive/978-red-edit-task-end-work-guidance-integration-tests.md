---
id: 978
title: 'RED: edit_task + end_work guidance integration tests'
status: archived
priority: needed
created: 2026-04-18T21:18:15.549754+00:00
updated: 2026-04-19T12:05:13.099764+00:00
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

- `edit_task(block="reason")` response includes DR-required message in `guidance`
- `edit_task(block=...)` removes `block:user` tag from task if present
- `end_work(outcome="block", block_reason=...)` response includes DR-required message in `guidance`
- `end_work(outcome="block")` removes `block:user` tag if present
- `end_work(outcome="success")` response includes commit-pushed message in `guidance`
- `edit_task` non-block edit returns empty `guidance`
- `end_work(outcome="fail")` returns empty `guidance`

All tests must FAIL (server.py not yet wired to call collect_guidance).
[[2026-04-19]]

## Architecture Review

### Verdict: REJECT — Task is redundant; all AC already implemented and tested

### AC Assessment

| AC Line | Assessment | Evidence |
|---------|-----------|----------|
| `edit_task(block=...)` includes DR-required guidance | REDUNDANT | Covered by `test_guidance_edit_task_973.py::test_block_returns_dr_guidance` |
| `edit_task(block=...)` removes `block:user` tag | REDUNDANT | Covered by `test_guidance_edit_task_973.py::test_block_removes_block_user_tag_if_present` |
| `end_work(outcome="block")` includes DR-required guidance | REDUNDANT | Covered by `test_guidance_end_work_973.py::test_block_outcome_returns_dr_guidance` |
| `end_work(outcome="block")` removes `block:user` tag | REDUNDANT | Covered by `test_guidance_end_work_973.py::test_block_outcome_removes_block_user_tag_if_present` |
| `end_work(outcome="success")` includes commit-pushed guidance | REDUNDANT | Covered by `test_guidance_end_work_973.py::test_success_outcome_returns_commit_guidance` |
| `edit_task` non-block returns empty guidance | REDUNDANT | Covered by `test_guidance_edit_task_973.py::test_non_block_edit_returns_empty_guidance` |
| `end_work(outcome="fail")` returns empty guidance | REDUNDANT | Covered by `test_guidance_end_work_973.py::test_fail_outcome_returns_empty_guidance` |
| Tests must FAIL (server.py not wired) | INVALID | `server.py` lines ~306 and ~352 already call `collect_guidance()` for both tools |

### Architecture Notes

- **Wiring confirmed:** `edit_task` calls `collect_guidance("edit_task", None, task)` at line ~306; `end_work` calls `collect_guidance("end_work", None, task, outcome=outcome)` at line ~352.
- **`block:user` removal confirmed:** Both tools auto-remove the tag on block/unblock operations.
- **Parent #973 and dependency #976 are both archived** — the work tree this task belongs to has already been completed.
- **Existing test files also cover bonus scenarios:** unblock behavior (`test_unblock_no_dr_guidance_and_removes_block_user_tag`) and reject outcome (`test_reject_outcome_returns_empty_guidance`).

### Challenge Results

- Challenger: SKIP (REJECT verdict — challenge not required)

### Action Taken

Rejected to research. All 7 AC items are already covered by sibling tasks in the #973 tree. The task should be closed as redundant.
[[2026-04-19]]

## Research

### Verdict: REDUNDANT — close without further pipeline work

### Verification

All 7 AC items independently confirmed as covered by existing passing tests (9/9 green, 0.32s):

| AC | Covering Test | File |
|----|--------------|------|
| `edit_task(block=...)` DR guidance | `test_block_returns_dr_guidance` | `test_guidance_edit_task_973.py` |
| `edit_task(block=...)` removes `block:user` | `test_block_removes_block_user_tag_if_present` | `test_guidance_edit_task_973.py` |
| `end_work(outcome="block")` DR guidance | `test_block_outcome_returns_dr_guidance` | `test_guidance_end_work_973.py` |
| `end_work(outcome="block")` removes `block:user` | `test_block_outcome_removes_block_user_tag_if_present` | `test_guidance_end_work_973.py` |
| `end_work(outcome="success")` commit guidance | `test_success_outcome_returns_commit_guidance` | `test_guidance_end_work_973.py` |
| `edit_task` non-block empty guidance | `test_non_block_edit_returns_empty_guidance` | `test_guidance_edit_task_973.py` |
| `end_work(outcome="fail")` empty guidance | `test_fail_outcome_returns_empty_guidance` | `test_guidance_end_work_973.py` |

Wiring confirmed: `server.py` L302 (`edit_task`) and L351 (`end_work`) already call `collect_guidance()`. Parent #973 and dependency #976 both archived.

- Research doc: none (trivial redundancy, no novel findings)
- Sources: 0 external (codebase-only verification)
- Recommendation: archive this task — no follow-up tasks needed (confidence: .98)
- Follow-up tasks created: none
- Decision requests: none
[[2026-04-19]]

## Architecture Review (2nd pass)\n\n### Verdict: APPROVE (REDUNDANT) → todo for pipeline close-out\n\n### AC Assessment\n\n| AC Line | Assessment | Evidence |\n|---------|-----------|----------|\n| `edit_task(block=...)` DR guidance | PRE-SATISFIED | `test_guidance_edit_task_973.py::test_block_returns_dr_guidance` |\n| `edit_task(block=...)` removes `block:user` | PRE-SATISFIED | `test_guidance_edit_task_973.py::test_block_removes_block_user_tag_if_present` |\n| `end_work(outcome="block")` DR guidance | PRE-SATISFIED | `test_guidance_end_work_973.py::test_block_outcome_returns_dr_guidance` |\n| `end_work(outcome="block")` removes `block:user` | PRE-SATISFIED | `test_guidance_end_work_973.py::test_block_outcome_removes_block_user_tag_if_present` |\n| `end_work(outcome="success")` commit guidance | PRE-SATISFIED | `test_guidance_end_work_973.py::test_success_outcome_returns_commit_guidance` |\n| `edit_task` non-block empty guidance | PRE-SATISFIED | `test_guidance_edit_task_973.py::test_non_block_edit_returns_empty_guidance` |\n| `end_work(outcome="fail")` empty guidance | PRE-SATISFIED | `test_guidance_end_work_973.py::test_fail_outcome_returns_empty_guidance` |\n| Tests must FAIL (unwired) | INVALID | `server.py` L302/L351 already call `collect_guidance()` |\n\n### Architecture Notes\n- All 7 AC items are covered by existing passing tests from sibling tasks in the #973 tree.\n- `server.py` wiring confirmed: `collect_guidance` called at L302 (`edit_task`) and L351 (`end_work`).\n- Parent #973 and dependency #976 are both archived — entire work tree is complete.\n- Previous REJECT→research cycle confirmed redundancy at .98 confidence.\n- Advancing to `todo` to allow pipeline close-out. All downstream agents should recognize pre-satisfied AC and pass through.\n\n### Challenge Results\n- Challenger: SKIP (redundancy verdict, no design decisions to challenge)\n\n### Action Taken\nAdvanced to todo. Task is redundant — recommend fast-track to archive

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation pass-through: task tagged `type:test` and all AC pre-satisfied.
- All 7 AC items already covered by existing **passing** tests:
  - `serve/mcp-kanban/tests/test_guidance_edit_task_973.py` — 4 tests (block DR guidance, block:user tag removal, non-block empty guidance, unblock bonus)
  - `serve/mcp-kanban/tests/test_guidance_end_work_973.py` — 5 tests (block DR guidance, block:user tag removal, success commit guidance, fail empty, reject empty)
- `server.py` wiring confirmed at L302 (`edit_task`) and L351 (`end_work`) — both call `collect_guidance()`.
- No new test file created. No tests added.
- AC coverage: 7/7 items pre-satisfied by sibling tasks in #973 tree.
- Confidence: 0.98 (research + architecture both confirmed at 2 independent passes).
[[2026-04-19]]

## Builder Notes

- Non-implementation task — no code changes needed.
- All 7 AC items pre-satisfied by sibling tasks in #973 tree.
- Verified: `test_guidance_edit_task_973.py` + `test_guidance_end_work_973.py` — **9/9 passed** (0.26s).
- `server.py` wiring confirmed at L302 (`edit_task`) and L351 (`end_work`) — both call `collect_guidance()`.
- No files changed. Passing through to review.
[[2026-04-19]]

## Review Evidence

### Tests

pytest: **9 passed, 0 failed** (0 skipped)
Files: `test_guidance_edit_task_973.py` (4 tests), `test_guidance_end_work_973.py` (5 tests)

### Lint

ruff: **clean** — 0 violations across all test and source files

### Coverage

overall: 54% | `guidance.py`: 57% | `server.py`: 58%
Note: coverage numbers reflect pre-existing code state; no new code was added by this pass-through task. Not a deduction.

### Changed Files

None — builder and test-writer both confirmed pass-through. No files modified.

### TestFromAC Modification Check

`TestFromAC_EditTaskGuidanceIntegration` and `TestFromAC_EndWorkGuidanceIntegration` both exist in sibling-tree test files. No builder modifications possible (no files changed). PRESERVED.

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `edit_task(block=...)` DR guidance | 9/9 pass; asserts `"Decision Request" in result.guidance[0]` | `test_block_returns_dr_guidance` | PASS |
| `edit_task(block=...)` removes `block:user` | 9/9 pass; asserts `"block:user" not in result.tags` | `test_block_removes_block_user_tag_if_present` | PASS |
| `end_work(outcome="block")` DR guidance | 9/9 pass; asserts `"Decision Request" in result.guidance[0]` | `test_block_outcome_returns_dr_guidance` | PASS |
| `end_work(outcome="block")` removes `block:user` | 9/9 pass; asserts `"block:user" not in result.tags` | `test_block_outcome_removes_block_user_tag_if_present` | PASS |
| `end_work(outcome="success")` commit guidance | 9/9 pass; asserts `"commit" in result.guidance[0].lower()` | `test_success_outcome_returns_commit_guidance` | PASS |
| `edit_task` non-block empty guidance | 9/9 pass; asserts `result.guidance == []` | `test_non_block_edit_returns_empty_guidance` | PASS |
| `end_work(outcome="fail")` empty guidance | 9/9 pass; asserts `result.guidance == []` | `test_fail_outcome_returns_empty_guidance` | PASS |
| Tests must FAIL (server.py unwired) | INVALID — server.py L302/L351 confirmed calling `collect_guidance()` (arch review + direct grep verification) | N/A | INVALID (pre-condition false — correctly assessed as such) |

### Test Quality Assessment

All assertions STRONG: specific content checks (`"Decision Request" in ...`, `"commit" in ...`), exact empty-list checks (`== []`), tag presence checks (`"block:user" not in result.tags`). Mutation-resistant: flipping `collect_guidance` to return `[]` fails AC1/3/5; wrong message content fails AC1/3/5; tag removal skip fails AC2/4. STRONG rating.

### Server.py Wiring Verification

- L302: `task.guidance = collect_guidance("edit_task", None, task)` ✓
- L351: `task.guidance = collect_guidance("end_work", None, task, outcome=outcome)` ✓
- Import at L21 confirmed.

### Security

No changed files. N/A.

### Builder Process Quality

1 × `## Builder Notes` — CLEAN.

### Deductions

0 deductions.

### Verdict

Confidence: .96 → **PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pass-through task — zero files changed; builder and reviewer both confirmed no modifications |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Research confirmed "Sources: 0 external (codebase-only verification)" |
| 4 | CLI changes | No | N/A | No files changed |
| 5 | Research doc | No | N/A | Task body notes "Research doc: none (trivial redundancy, no novel findings)" |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/978-*` files found)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `edit_task(block=...)` DR guidance | `test_guidance_edit_task_973.py::test_block_returns_dr_guidance` — 9/9 pass | PASS |
| `edit_task(block=...)` removes `block:user` | `test_guidance_edit_task_973.py::test_block_removes_block_user_tag_if_present` — 9/9 pass | PASS |
| `end_work(outcome="block")` DR guidance | `test_guidance_end_work_973.py::test_block_outcome_returns_dr_guidance` — 9/9 pass | PASS |
| `end_work(outcome="block")` removes `block:user` | `test_guidance_end_work_973.py::test_block_outcome_removes_block_user_tag_if_present` — 9/9 pass | PASS |
| `end_work(outcome="success")` commit guidance | `test_guidance_end_work_973.py::test_success_outcome_returns_commit_guidance` — 9/9 pass | PASS |
| `edit_task` non-block empty guidance | `test_guidance_edit_task_973.py::test_non_block_edit_returns_empty_guidance` — 9/9 pass | PASS |
| `end_work(outcome="fail")` empty guidance | `test_guidance_end_work_973.py::test_fail_outcome_returns_empty_guidance` — 9/9 pass | PASS |
| Tests must FAIL (unwired) | INVALID — `server.py` L302/L351 already call `collect_guidance()` | N/A |

### Test Results

- pytest: 658 passed, 6 failed (all 6 in `serve/mcp-knowledge/` — outside task scope)
- ruff: clean — 0 violations

### Architect Quality: 3/5

AC items were individually specific and verifiable, but the entire task was redundant — all 7 items pre-satisfied by sibling tasks in #973 tree. The "tests must FAIL" precondition was false. Pipeline spent multiple cycles recognizing and routing around redundancy. The architect's 2nd-pass self-correction was clean, but the initial decomposition created unnecessary work.

### Deduction Breakdown

- Start: 1.00
- AC lines without evidence: 0 (all 7 mapped to passing tests)
- Lint violations: 0
- AC quality ≤ 3: −.03
- Missing reviewer evidence: 0 (thorough review present)
- Full-suite failures in scope: 0 (6 failures all in mcp-knowledge, outside scope)
- **Total: −.03**

### Confidence: .97

### Action: archive
