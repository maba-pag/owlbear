---
id: 977
title: 'GREEN: Cockpit block:user tag lifecycle'
status: archived
priority: medium
created: 2026-04-18T21:18:03.821522+00:00
updated: 2026-04-19T03:07:03.601434+00:00
tags:
- scope:cockpit
- type:build
parent: 973
depends_on:
- 975
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase per w-tdd-green. Makes #975 tests pass.

## Acceptance Criteria

File: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`

Per Brief decision D3:

- Block path (`edit_task` route when transitioning to blocked) adds `block:user` to task tags. Idempotent — no duplicates if already present.
- Unblock path removes `block:user` from task tags. No-op if not present.
- No new arguments to the route. No MCP routing change. Cockpit continues to call the engine directly.

All tests in #975 pass; all existing cockpit tests still pass.
[[2026-04-19]]

## Architecture Review

### Verdict: REJECT (redundant — recommend archive)

### Evaluation

This task's entire scope was already delivered by sibling tasks in the #973 subtask tree:

- **#975** (commit `22264efc`): Implemented `_apply_block_kwargs()` in `mutation.py` (lines 133–160) — adds `block:user` on block, removes on unblock, idempotent. 4 integration tests in `TestFromAC_BlockUserTag`.
- **#990** (status: review): Extended with tag-diff conflict resolution. 3 additional tests in `TestFromAC_BlockUserTagConflict`. Its architecture review explicitly states: "#977 is **redundant** — #975's pipeline execution already completed the GREEN phase. #977 should be closed."

Every AC line of #977 maps to code and tests that already exist and pass. Advancing would produce a zero-diff pipeline pass through 5 agents for no deliverable.

### Challenge Results

- Challenger: **block** (confidence 0.15 in original APPROVE)
- Key issues: task explicitly marked redundant by #990's architecture review, implementation and tests pre-exist, zero-value pipeline pass
- Architect response: **accepted** — challenger is correct, rejecting as redundant

### Action Taken

Rejected to research. Recommend orchestrator archive this task — no remaining work.
[[2026-04-19]]

## Research

**Verdict: Redundant — advance to backlog for archival.**

Verified all 3 AC lines of #977 are already implemented and tested:

- `_apply_block_kwargs()` in `mutation.py:138-159` — block adds `block:user` idempotently, unblock removes it, conflict resolution strips contradictory tag-diff entries.
- 7 tests pass across `TestFromAC_BlockUserTag` (4 tests, #975) and `TestFromAC_BlockUserTagConflict` (3 tests, #990).
- Parent #973 and #975 already archived.

No research doc needed — no novel findings, only redundancy confirmation.
No follow-up tasks created — zero remaining work.
Decision requests: none.

Recommend orchestrator archive this task at backlog.
[[2026-04-19]]

## Architecture Review (2nd pass)

### Verdict: APPROVE (redundant drain — zero implementation needed)

### Context

This task completed a reject→research→backlog cycle. The researcher confirmed all 3 AC lines are already implemented and tested by sibling tasks (#975, #990). Rejecting again would create an infinite loop.

### Codebase Verification

- `_apply_block_kwargs()` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:138-159` — block adds `block:user` idempotently, unblock removes it, conflict resolution strips contradictory tag-diff entries.
- `TestFromAC_BlockUserTag` (4 tests, line 491) + `TestFromAC_BlockUserTagConflict` (3 tests, line 570) in `tests/test_cockpit_mutation_api.py` — all passing.
- Parent #973 and dependency #975 already archived.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern (block:user tag lifecycle) — already delivered |
| Interface clarity | PASS | AC is precise — moot since already implemented |
| Dependency correctness | PASS | #975 archived (done) |
| Module layering | PASS | All in cockpit routes layer |
| TDD compliance | PASS | Tests pre-exist from #975 RED phase |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | FAIL | Capability already exists — but rejecting loops, so approving to drain |
| Pattern consistency | PASS | Follows existing mutation route pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Cockpit only |

### Challenge Results

- Challenger: SKIPPED — task is verified-redundant, approval is a pipeline-drain action, not an endorsement of new work
- Architect response: N/A

### Action Taken

Approved to `todo` to drain through pipeline for archival. All downstream agents should find zero work: tests already pass, implementation already exists. Recommend fast pass-through at each gate.
[[2026-04-19]]

## Test-Writer Notes

Verified-redundant drain pass-through — no new tests written.

**Existing test coverage (already passing):**

- File: `tests/test_cockpit_mutation_api.py`
- `TestFromAC_BlockUserTag` (line 491) — 4 tests (AC1–AC4 from #975)
- `TestFromAC_BlockUserTagConflict` (line 570) — 3 tests (AC1–AC3 from #990)
- Total: 7 tests, all PASS

**AC coverage:**

| AC line | Test | Status |
|---------|------|--------|
| Block adds `block:user` idempotently | `test_block_adds_block_user_tag`, `test_block_user_tag_is_idempotent` | Covered (pre-existing) |
| Unblock removes `block:user` | `test_unblock_removes_block_user_tag` | Covered (pre-existing) |
| No-op if tag not present | `test_unblock_without_tag_present_returns_200` | Covered (pre-existing) |

Architecture review (2nd pass) approved this task to drain through pipeline — implementation and tests were delivered by #975 and #990. All downstream agents should pass through with zero work.
[[2026-04-19]]

## Builder Notes

**Drain pass-through — zero implementation work.**

### Files changed

None. All AC already implemented by #975 and #990.

### Test results

- `TestFromAC_BlockUserTag` (4 tests) — PASS
- `TestFromAC_BlockUserTagConflict` (3 tests) — PASS
- Total: 7 passed, 0 failed

### Lint status

No files changed — ruff N/A.

### Coverage

Pre-existing coverage from #975. `_apply_block_kwargs()` at `mutation.py:138–159` — fully covered.

### Evidence summary

All 3 AC lines verified already live in `mutation.py`:

- Block adds `block:user` idempotently ✓
- Unblock removes `block:user` ✓
- No-op if tag not present ✓
Pipeline drain complete — advance to review for archival.
[[2026-04-19]]

## Review Evidence

### Test Execution (Quality-Runner — independent)

- `tests/test_cockpit_mutation_api.py`: **37 passed, 0 failed**
- Lint (`mutation.py` + test file): **clean**
- Coverage for `owlbear_cockpit.routes.mutation`: not reported (quality-runner returned `owlbear_kanban` coverage instead — module resolution mismatch). Implementation verified directly by code-reader as compensating evidence.

### Builder Process Quality

- 1 builder notes section. Drain pass-through — zero files changed. No loop.

### Step 5.2 — TestFromAC Comparison

No TestFromAC_ modifications by builder (zero files changed). All pre-existing tests intact — PRESERVED.

### Step 5.3 — Test Quality: WEAK (auto-FAIL)

| Test | Finding | Assessment |
|------|---------|------------|
| `test_block_adds_block_user_tag` (line 511) | Asserts `"block:user" in tags` only. Does NOT assert `response.json()["blocked"] is True`. A regression dropping `kwargs["blocked"] = True` in `_apply_block_kwargs` would silently pass. | **WEAK** |
| `test_unblock_removes_block_user_tag` (line 519) | Asserts `"block:user" not in tags` only. Does NOT assert `response.json()["blocked"] is False`. Symmetric regression surface on the unblock path. | **WEAK** |
| `test_block_conflict_preserves_block_user_tag` (line 575) | Asserts `"block:user" in tags` but does not verify sibling tag `scope:test` survives conflict resolution. A bug that preserves `block:user` while stripping all other tags would pass. | **WEAK** |
| `test_block_user_tag_is_idempotent` (line 533) | `.count("block:user") == 1` — strong, catches both missing and doubled tag | STRONG |
| `test_unblock_without_tag_present_returns_200` (line 553) | Checks `blocked is False` — good; covers no-op robustness path | STRONG |

### Step 5.0 — AC-to-Test Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|---------------------------|---------|
| Block adds `block:user` idempotently | `test_block_adds_block_user_tag`, `test_block_user_tag_is_idempotent` | Partially — tag mutation yes, `blocked` field state no | LAX |
| Unblock removes `block:user` (no-op if absent) | `test_unblock_removes_block_user_tag`, `test_unblock_without_tag_present_returns_200` | Partially — tag removal yes, `blocked=False` state no | LAX |
| No new route arguments, engine called directly | Structural — verified at `mutation.py:197,210`. No dedicated test. | No dedicated test; existing suite provides compensating coverage | COVERED (structural) |

### Step 5.1 — Security

No concerns. `task_id: int` validated by FastAPI; `extra="forbid"` on `EditRequest` prevents field injection; `ValueError` caught without stack trace leakage; no SQL/subprocess/template paths.

### Step 5.5 — Implementation-Aware Gap Analysis (code-reader)

- `block_reason=""` (empty string) passes `is not None` guard → sets `blocked=True`. No validator on `block_reason` min-length; no test documents or rejects this path. Notable gap.
- Idempotency guards in block and unblock paths (`if "block:user" not in add_tags`, `if "block:user" not in remove_tags`) are untested branches. Minor but the add-conflict and remove-conflict sub-paths are each only covered one-sided.

### Deductions

| Finding | Category | Deduction |
|---------|----------|-----------|
| `test_block_adds_block_user_tag` WEAK (no `blocked=True` check) | Step 5.3 | −0.12 |
| `test_unblock_removes_block_user_tag` WEAK (no `blocked=False` check) | Step 5.3 | −0.12 |
| `test_block_conflict_preserves_block_user_tag` WEAK (no sibling tag check) | Step 5.3 | −0.04 |
| **Total** | | **−0.28** |

### Verdict

**Confidence: .72 → FAIL**

Three WEAK test assertions. Implementation is correct (`mutation.py:138-159` verified, all 37 tests pass, lint clean). Tests insufficient.

**Action for test-writer:**

1. Strengthen `test_block_adds_block_user_tag`: add `assert response.json()["blocked"] is True`
2. Strengthen `test_unblock_removes_block_user_tag`: add `assert response.json()["blocked"] is False`
3. Strengthen `test_block_conflict_preserves_block_user_tag`: add `assert "scope:test" in response.json()["tags"]`
4. Optional: add a test covering `block_reason=""` path to document intended behavior.
[[2026-04-19]]

## Test-Writer Notes

Retry cycle — reviewer cited WEAK assertions in 3 tests (Step 5.3 FAIL). Applied reviewer's explicit action items.

**Changes made** (tests/test_cockpit_mutation_api.py):

- `test_block_adds_block_user_tag`: added `assert response.json()["blocked"] is True`
- `test_unblock_removes_block_user_tag`: added `assert response.json()["blocked"] is False`
- `test_block_conflict_preserves_block_user_tag`: added `assert "scope:test" in response.json()["tags"]`

**Test results (post-change):**

- `TestFromAC_BlockUserTag`: 4 tests — all PASS
- `TestFromAC_BlockUserTagConflict`: 3 tests — all PASS
- Total: 7 PASS (implementation is already correct)
- ruff: clean

**AC coverage:**

| AC line | Test | Status |
|---------|------|--------|
| Block adds `block:user` idempotently + sets blocked=True | `test_block_adds_block_user_tag`, `test_block_user_tag_is_idempotent` | COVERED (strengthened) |
| Unblock removes `block:user` + sets blocked=False | `test_unblock_removes_block_user_tag` | COVERED (strengthened) |
| No-op if tag not present | `test_unblock_without_tag_present_returns_200` | COVERED |
| Sibling tags preserved during conflict | `test_block_conflict_preserves_block_user_tag` | COVERED (strengthened) |

Commit: `09e8c67a` — test: strengthen block:user tag assertions per reviewer (#977, test-writer)
[[2026-04-19]]

## Builder Notes

**Drain pass-through — zero implementation work.**

### Files changed

None. All AC already implemented by #975 and #990. Test-writer strengthened 3 assertions in prior cycle (commit `09e8c67a`).

### Test results

- `TestFromAC_BlockUserTag` (4 tests) — PASS
- `TestFromAC_BlockUserTagConflict` (3 tests) — PASS
- Full `tests/test_cockpit_mutation_api.py` (37 tests) — PASS, 0 failed
- Lint: `ruff check` — clean

### Evidence summary

- All 3 AC lines verified live in `mutation.py` (`_apply_block_kwargs` at lines 138–159)
- Strengthened assertions present and passing: `blocked is True`, `blocked is False`, `scope:test` sibling tag preserved
- No files touched — no diff produced
[[2026-04-19]]

## Review Evidence

### Test Execution (Quality-Runner — independent, cycle 2)

- `tests/test_cockpit_mutation_api.py`: **37 passed, 0 failed**
- Lint (`mutation.py` + test file): **clean**
- Coverage for `owlbear_cockpit.routes.mutation`: not in coverage output (module resolution mismatch — same known issue as cycle 1; code-reader direct code verification used as compensating evidence)

### Step 5.2 — TestFromAC Comparison

No builder file changes in this cycle. Test-writer changes from commit `09e8c67a` verified:

| Original Test | Change Made | Assessment |
|---|---|---|
| `test_block_adds_block_user_tag` | Added `assert response.json()["blocked"] is True` at line 513 | STRENGTHENED |
| `test_unblock_removes_block_user_tag` | Added `assert response.json()["blocked"] is False` at line 528 | STRENGTHENED |
| `test_block_conflict_preserves_block_user_tag` | Added `assert "scope:test" in response.json()["tags"]` at line 608 | STRENGTHENED |
| All remaining TestFromAC_ methods | Unchanged | PRESERVED |

All 7 TestFromAC_ methods present (4 in `TestFromAC_BlockUserTag`, 3 in `TestFromAC_BlockUserTagConflict`). No weakening detected.

### Step 5.3 — Test Quality: STRONG

Cycle-1 WEAK items resolved. Mutation reasoning on the strengthened assertions:

- Line 513 (`blocked is True`): kills a bug that adds `block:user` tag but omits `blocked=True` from kwargs — orthogonal to tag check. **Genuine mutation killer.**
- Line 528 (`blocked is False`): kills a bug where unblock strips tag but leaves `blocked=True` in response. **Genuine mutation killer.**
- Line 608 (`scope:test in tags`): kills a bug where conflict resolution over-strips sibling tags. **Genuine mutation killer.**

Setup guards present on every test with a precondition (`assert "block:user" in (task.tags or [])  # confirm setup`). Identity comparisons (`is True` / `is False`), not truthy. Test names descriptive.

One minor gap (6.3, informational): `test_block_user_tag_is_idempotent` checks tag count on `r2` but not `r2.json()["blocked"] is True`. Not rated WEAK — compensating coverage exists in `test_block_adds_block_user_tag`, and the idempotency test's purpose is tag-count verification.

### Step 5.0 — AC-to-Test Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| Block adds `block:user` idempotently | `test_block_adds_block_user_tag` (tag + `blocked=True`), `test_block_user_tag_is_idempotent` (count==1), conflict variant | Yes — tag missing, duplicated, or `blocked` state wrong all caught | COVERED |
| Unblock removes `block:user`; no-op if absent | `test_unblock_removes_block_user_tag` (removal + `blocked=False`), `test_unblock_without_tag_present_returns_200` | Yes — tag persists or `blocked` persists both caught | COVERED |
| No new route args; engine called directly | `extra="forbid"` on `EditRequest` tested by existing 422 tests; TestClient + `dependency_overrides` architecture unchanged | Structural — compensating coverage | COVERED |

### Step 5.1 — Security

No concerns. `task_id: int` validated by FastAPI, `extra="forbid"` prevents field injection, `ValueError` caught without stack trace leakage, no SQL/subprocess/template paths.

### Step 5.4 — Data Safety

All tests use `tmp_path` with function-scoped `board_dir`/`engine` fixtures. Full isolation between runs. No shared mutable state.

### Step 5.5 — Implementation-Aware Test Gap Analysis

`_apply_block_kwargs()` at `mutation.py:138–159` verified by code-reader. All major branches covered:

- Block path: `if "block:user" not in add_tags` guard (idempotency), `kwargs["blocked"] = True` set
- Unblock path: `if "block:user" not in remove_tags` guard, `kwargs["blocked"] = False` set
- Conflict resolution (from #990): strips contradictory entries

Minor gap (informational): `kwargs["remove_tags"] = []` written unconditionally in block branch when strip yields empty list — inconsistent with `_apply_list_diff` guard (`if add:` / `if remove:`). Behaviourally harmless; no test needed.

### Step 5.7 — Builder Process Quality

2 × `## Builder Notes` sections (cycle 1 drain, cycle 2 drain). Zero files changed both times. Test-writer addressed all reviewer action items. **CLEAN** — no loop.

### Informational (6.x)

- 6.3: `TestFromAC_BlockUserTag` class docstring says "must FAIL until GREEN" — stale RED-phase note (harmless)
- 6.3: `test_block_user_tag_is_idempotent` missing `blocked is True` on `r2` — minor gap, compensated
- 6.4: `_apply_block_kwargs` writes `remove_tags=[]` unnecessarily; cosmetic inconsistency

### Deductions

Cycle-1 deductions (−0.28) fully remediated. No new Pass-1 findings.

| Finding | Category | Deduction |
|---|---|---|
| Coverage module mismatch (known, compensated) | Step 4 | −0.02 |
| Idempotency test missing `blocked is True` on r2 (informational) | Step 6.3 | −0.02 |
| **Total** | | **−0.04** |

### Verdict

**Confidence: .96 → PASS**

37/37 tests pass. Lint clean. All 3 cycle-1 WEAK assertions strengthened with genuine mutation killers. AC fully covered. No security issues. No loop. Implementation correct and unchanged.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Feature (`_apply_block_kwargs`) was delivered by #975. This task only strengthened test assertions (commit `09e8c67a`). No new endpoints or route signature changes. `copilot-instructions.md` endpoint table already current. |
| 2 | Module docstrings | Yes | Verified | All public symbols in `mutation.py` have docstrings: module, `MoveRequest`, `EditRequest`, `move_task`, `_build_edit_kwargs`, `_apply_block_kwargs`, `_apply_list_diff`, `edit_task`, `release_task`. No updates needed. |
| 3 | External attribution | No | N/A | No external patterns cited in task or review evidence. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | Researcher explicitly noted "No research doc needed — no novel findings, only redundancy confirmation." |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/977-*` files found)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Block adds `block:user` idempotently | `_apply_block_kwargs` mutation.py:148-153; `test_block_adds_block_user_tag` (tag + `blocked is True`), `test_block_user_tag_is_idempotent` (count==1) | PASS |
| Unblock removes `block:user`; no-op if absent | `_apply_block_kwargs` mutation.py:155-159; `test_unblock_removes_block_user_tag` (`blocked is False`), `test_unblock_without_tag_present_returns_200` | PASS |
| No new route args; engine called directly | `extra="forbid"` on EditRequest; structural verification by reviewer code-reader | PASS |
| All tests pass; existing cockpit tests still pass | 37/37 mutation tests pass; full suite 658 passed | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all outside task scope: test_outputschema_541, test_search_v2, test_phase_a_config)
- ruff: clean

### Architect Quality: 4/5

AC was precise and testable ("idempotent", "no-op if not present", "no new arguments"). Minor gap: task itself was redundant (caught by architecture review, drained correctly). AC specificity adequate for verification.

### Deduction Breakdown

| Criterion | Deduction |
|-----------|-----------|
| Coverage module mismatch (known, compensated by code-reader) | -0.02 |
| Total | -0.02 |

No AC lines without evidence. Lint clean. Reviewer evidence detailed (2 cycles, PASS). No suite failures in scope. AC quality 4/5 (above threshold).

### Confidence: .98

### Action: archive
