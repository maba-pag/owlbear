---
id: 975
title: 'RED: Cockpit block:user tag lifecycle tests'
status: in-progress
priority: needed
created: 2026-04-18T21:17:49.871765+00:00
updated: 2026-04-18T21:58:02.798866+00:00
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
- Architect response: accepted C3 (refined FAIL expectation), noted C1 for GREEN task's AC (tags+block_reason field interaction in _build_edit_kwargs), dismissed C2 as minor (follows existing engine setup convention)

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