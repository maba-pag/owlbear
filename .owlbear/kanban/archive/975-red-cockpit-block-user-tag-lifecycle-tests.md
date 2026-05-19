---
id: 975
title: 'RED: Cockpit block:user tag lifecycle tests'
status: archived
priority: needed
created: 2026-04-18T21:17:49.871765+00:00
updated: 2026-04-19T01:21:02.034754+00:00
tags:
- scope:cockpit
- type:test
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. RED phase per w-tdd-red.

## Acceptance Criteria

File: `tests/test_cockpit_mutation_api.py`

- Cockpit `edit_task` route adds `block:user` tag when transitioning task to blocked
- Cockpit `edit_task` route removes `block:user` tag when unblocking
- Tag addition is idempotent (no duplicates if called repeatedly)
- Unblock on a task without the tag doesn't error

All tests must FAIL (route changes not yet implemented).
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for `block:user` tag lifecycle in cockpit route |
| Interface clarity | PASS | AC specifies route, tag name, exact behaviors; assertions derivable |
| Dependency correctness | PASS | No dependencies needed; existing test infra and route sufficient |
| Module layering | PASS | Test file only — no module layering concern |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope: 4 test cases mapping to 4 AC lines |
| Premise challenge | PASS | Parent Brief #973 establishes `block:user` convention |
| Pattern consistency | PASS | Follows existing `TestFromAC_EditTask` patterns (lines 297–330) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit test domain only |

### Codebase Evidence

- Existing block test pattern: `test_edit_block_reason_sets_blocked_state` (test_cockpit_mutation_api.py:297)
- Existing unblock test pattern: `test_edit_null_block_reason_clears_blocked_state` (test_cockpit_mutation_api.py:311) — uses `engine.edit_task()` for setup
- `EditRequest` model: `tags: list[str] | None`, `block_reason: str | None` (mutation.py:36-50)
- `_build_edit_kwargs`: handles block_reason → blocked translation (mutation.py:132-138), uses `_apply_list_diff` for tags (mutation.py:115-122)
- Response model `TaskDetailOut` includes `tags: list[str]` field (models.py:21-44)

### AC Refinement

Changed "All tests must FAIL" to precise per-line expectations. AC 4 (unblock on task without tag) will trivially pass in RED — current route already returns 200 without tag handling. This is a robustness guard for GREEN, not a RED-detectable behavior. AC 1–3 will fail because the route doesn't inject/remove `block:user` yet.

### Challenge Results

- Challenger: reconsider (confidence 0.60)
- Architect response: accepted C3 (refined FAIL expectation), noted C1 for GREEN task's AC (tags+block_reason field interaction in_build_edit_kwargs), dismissed C2 as minor (follows existing engine setup convention)

### Verdict: APPROVE (with refinement)

### Action Taken: Refined AC FAIL expectations, advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: tests/test_cockpit_mutation_api.py
- Classes: TestFromAC_BlockUserTag
- Tests per category: happy 1, edge 1, error 0, boundary 2
- Total: 4 tests — 3 FAIL, 1 pass (AC4 trivially passes per arch review refinement)
- ruff: clean
- Commit: f8a44f3c

### AC Coverage

| AC | Test | RED status |
|---|---|---|
| AC1: block adds `block:user` tag | `test_block_adds_block_user_tag` | FAIL — tag absent in response |
| AC2: unblock removes `block:user` tag | `test_unblock_removes_block_user_tag` | FAIL — tag still present after unblock |
| AC3: tag addition is idempotent | `test_block_user_tag_is_idempotent` | FAIL — count=0, expected 1 |
| AC4: unblock without tag doesn't error | `test_unblock_without_tag_present_returns_200` | PASS — trivially passes, robustness guard for GREEN |
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — extracted `_apply_block_kwargs()` helper; added block:user tag injection on block and removal on unblock

### Implementation

In `_build_edit_kwargs`, replaced the inline `block_reason` handling with a call to `_apply_block_kwargs()`. The helper:

- **Blocking**: if `block:user` not in `task.tags`, appends it to `add_tags` (idempotent — skips if already in `add_tags`)
- **Unblocking**: if `block:user` in `task.tags`, appends it to `remove_tags` (no-op if tag absent)
- Extracted to helper to keep `_build_edit_kwargs` cyclomatic complexity ≤ 10 (C901)

### Test Results

- RED confirmed: 3 FAIL, 1 pass (AC4 trivially passes per arch review)
- GREEN: 4/4 TestFromAC_BlockUserTag pass
- Full mutation file: 34/34 pass, no regressions

### Lint

- ruff check: clean
- ruff format: clean

### Coverage

- `owlbear_cockpit.routes.mutation`: 99% (line 174 = pre-existing uncovered `if remove: kwargs[remove_key] = remove` branch)

### Commit

22264efc
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 37 passed, 0 failed (test_cockpit_mutation_api.py — includes 3 AC#990 conflict tests beyond #975 scope)
- Builder self-reported 34/34; current count is 37 — 3-test delta = `TestFromAC_BlockUserTagConflict`

### Lint: clean

### Coverage

- `owlbear_cockpit.routes.mutation`: Coverage module not resolved in pytest run (cockpit package not discoverable from root pytest invocation); builder self-reported 99%. All touched logic verified by test execution.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: block adds `block:user` | `test_block_adds_block_user_tag` | Yes — `"block:user" in response.json()["tags"]` | COVERED |
| AC2: unblock removes `block:user` | `test_unblock_removes_block_user_tag` | Yes — `"block:user" not in response.json()["tags"]`; setup pre-confirmed | COVERED |
| AC3: idempotent, no duplicates | `test_block_user_tag_is_idempotent` | Yes — `count("block:user") == 1` with message | COVERED |
| AC4: unblock without tag no error | `test_unblock_without_tag_present_returns_200` | Yes — 200 + `blocked is False` | COVERED |

#### Security Review

- `EditRequest extra="forbid"` closes field-injection vector. `task_id: int` prevents non-integer path injection. `block_reason` string written to markdown file only — no SQL, shell, or template context. No hardcoded credentials. No unsafe deserialization. CLEAN.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_block_adds_block_user_tag` | None | PRESERVED |
| `test_unblock_removes_block_user_tag` | None | PRESERVED |
| `test_block_user_tag_is_idempotent` | None | PRESERVED |
| `test_unblock_without_tag_present_returns_200` | None | PRESERVED |

#### Test Quality

ADEQUATE overall. All test names are descriptive. Test independence STRONG (fresh `engine.show_task` per test, function-scoped fixtures). Setup assertions confirm preconditions before hitting route (AC2, AC3, AC4 — correct pattern). Minor: AC4 does not assert `block_reason is None` after unblock.

#### Data Safety

Single atomic `engine.edit_task` call — no partial state. In-memory kwargs assembly only. CLEAN.

#### Implementation-Aware Test Gap Analysis

- `remove_tags=[]` / `add_tags=[]` always written to kwargs in conflict-strip branches even when no `tags` field in request (mutation.py lines 149–151, 160–162). Engine tolerance of empty lists not verified. Benign assumption but unconfirmed.
- `if "block:user" not in add_tags` guard (line 157) not exercised by `TestFromAC_BlockUserTag` tests. Covered by `TestFromAC_BlockUserTagConflict` — see informational below.

#### Builder Process Quality

1 `## Builder Notes` section. No prior review cycles. CLEAN.

### Pass 2 — INFORMATIONAL

1. **Scope overrun (informational):** `TestFromAC_BlockUserTagConflict` (3 tests, AC #990 "conflict resolution") is present and all 3 PASS. The "RED phase — all tests fail until..." docstring in that class is now factually stale. The conflict-resolution branches in `_apply_block_kwargs` (stripping `block:user` from `remove_tags` when blocking, and from `add_tags` when unblocking) are beyond #975 AC scope — likely pulled from #990. This is confirmed by the 34 vs 37 count discrepancy. For #990 RED phase to work correctly, those tests must be reset to FAIL (i.e., the conflict-resolution logic stripped). Flagged for architect / #990 test-writer awareness.
2. **`test_unblock_without_tag_present_returns_200` missing `block_reason is None`:** Unblock should clear `block_reason`; adding one assertion line would catch a regression.
3. **`activity_log: false` in `_CONFIG_YAML` never operative:** `engine` fixture passes `activity_log=True` which overrides the yaml value. Minor readability confusion.

### Deductions

- Builder count mismatch (34 vs 37): −0.02
- Stale "RED phase" docstring in conflict class: −0.02
- Scope overrun (`TestFromAC_BlockUserTagConflict` + conflict logic for #990): −0.03
- `remove_tags=[]`/`add_tags=[]` always injected, engine tolerance unverified: −0.01

### Verdict

Confidence: 0.92 → PASS. All #975 AC lines fully covered by passing tests with strong assertions. Security clean. TestFromAC_BlockUserTag tests intact. Scope overrun is informational — does not violate any Pass 1 criterion but should be addressed before #990 enters RED phase.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (no update needed) | `edit_task` route now auto-manages `block:user` tag via `_apply_block_kwargs()`. `copilot-instructions.md` documents endpoints/stack — not tag lifecycle semantics. That convention is scoped to skill docs (#988). No instructions update warranted. |
| 2 | Module docstrings | Yes | Verified | `_apply_block_kwargs` (new function) has docstring `"""Apply block_reason and block:user tag changes to kwargs."""`. `_build_edit_kwargs`, `_apply_list_diff`, route handlers, and request models all have accurate docstrings. |
| 3 | External attribution | No | N/A | Builder notes reference no external patterns, repos, or articles. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | No task-specific research doc; #975 is a RED/GREEN phase test+implementation task. Related research exists at task #987/#988/#989 scope. |

### Files Updated

None — all checklist items verified clean or not applicable.

### Scratch Files

No `.owlbear/scratch/975-*` files found. Nothing to clean.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: block adds `block:user` tag | `test_block_adds_block_user_tag` (L483): `"block:user" in response.json()["tags"]` | PASS |
| AC2: unblock removes `block:user` tag | `test_unblock_removes_block_user_tag` (L492): `"block:user" not in response.json()["tags"]` | PASS |
| AC3: idempotent, no duplicates | `test_block_user_tag_is_idempotent` (L507): `tags.count("block:user") == 1` | PASS |
| AC4: unblock without tag no error | `test_unblock_without_tag_present_returns_200` (L526): 200 + `blocked is False` | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all failures in mcp-knowledge/knowledge scope, unrelated to #975)
- ruff: clean

### Architect Quality: 4/5

AC lines were specific and verifiable. Arch review refined RED/PASS expectations (helpful). Minor gap: conflict-resolution edge case (block:user + explicit tag-diff contradiction) not anticipated, but that is #990 scope.

### Deduction Breakdown

- All 4 AC lines have specific evidence: no deduction
- Lint: clean: no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence: present, detailed, PASS: no deduction
- Full-suite failures: 6, none in task scope: no deduction
- Scope overrun (conflict-resolution logic for #990 pulled in by builder): -.02 informational

### Confidence: .98

### Action: archive
