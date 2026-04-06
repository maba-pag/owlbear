---
id: 665
title: 'Test: type:user-action in NON_IMPL_TAGS gate sets'
status: in-progress
priority: nice-to-have
created: 2026-04-06T16:46:57.2190253+02:00
updated: 2026-04-06T18:51:34.3279321+02:00
tags:
    - phase-3
    - ' scope:orchestrator'
    - ' type:test'
parent: 661
class: standard
---

## Objective\nWrite failing tests asserting type:user-action is recognized in both NON_IMPL_TAGS gate sets.\n\n## Acceptance Criteria\n- [ ] Test asserts "type:user-action" is in _NON_IMPL_TAGS frozenset (gates.py)\n- [ ] Test asserts "type:user-action" is in _PICK_NON_IMPL_TAGS frozenset (server.py)\n- [ ] Test that check_tdd() returns True for in-progress task tagged type:user-action without Test-Writer Notes\n- [ ] Test that _check_pick_gates() returns True for in-progress task tagged type:user-action without Test-Writer Notes\n- [ ] All tests FAIL before implementation (TDD RED)\n\n## Context\nExtends existing test patterns in tests/test_tdd_gate_non_impl_630.py.\n\n## Files Affected\n- tests/test_user_action_non_impl_661.py (new)

[[2026-04-06]] Mon 17:57
## Research
- Research doc: .owlbear/research/user-action-non-impl-tags-tests.md
- Sources: 5 studied, 3 high-relevance (gates.py, server.py, test_tdd_gate_non_impl_630.py)
- Recommendation: Follow #630 test pattern exactly — 4 tests covering membership + behavioral assertions (confidence: .95)
- Follow-up tasks created: none (implementation task #662 already exists)
- Decision requests: none (T1 — test task, direct pattern extension)

### Key findings
- `type:user-action` confirmed absent from both `_NON_IMPL_TAGS` (gates.py L24) and `_PICK_NON_IMPL_TAGS` (server.py L531)
- Tests will correctly FAIL in TDD RED phase
- Test file: `tests/test_user_action_non_impl_661.py` — reuses helpers/imports from #630 pattern

[[2026-04-06]] Mon 18:06
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task: 4 test categories covering 2 frozensets and 2 gate functions |
| Interface clarity | PASS | Each AC line specifies exact import, assertion, and expected return value |
| Dependency correctness | PASS | No depends_on — correct, this is the first task in Chain A (#665 -> #662 -> #666) |
| Module layering | PASS | Tests import from owlbear.planner.gates and owlbear_mcp_kanban.server — standard test pattern |
| TDD compliance | PASS | This IS the TDD RED task; tagged type:test |
| KISS/YAGNI | PASS | 4 AC lines producing ~7 tests, mirrors #630 pattern exactly |
| Premise challenge | PASS | Parent #661 research confirms type:user-action absent from both frozensets; tests will correctly FAIL |
| Pattern consistency | PASS | Follows test_tdd_gate_non_impl_630.py structure: same helpers, same import pattern, same test class naming |
| Security surface | PASS | No system boundaries affected; test file only |
| Single domain | PASS | Logical domain = non-impl gating; crosses orchestrator/mcp-kanban packages but this is the established #630 pattern for testing paired frozensets |

### Failure Mode Map
Not applicable (test task).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| "type:user-action" in _NON_IMPL_TAGS (gates.py) | Precise, directly testable via import + `in` operator | None |
| "type:user-action" in _PICK_NON_IMPL_TAGS (server.py) | Precise, directly testable | None |
| check_tdd() returns True for tagged in-progress task | Precise: status=in-progress, tag=type:user-action, no TW notes, assert True | None |
| _check_pick_gates() returns True for tagged in-progress task | Testable via pick_tasks public interface (established pattern) | None |
| All tests FAIL before implementation (TDD RED) | Standard TDD RED requirement, verifiable by runner | None |

### Notes
- Test file `tests/test_user_action_non_impl_661.py` already exists (written during parent #661 test-writer phase). Test-writer for #665 can validate and write pass-through notes.
- AC line 4 references private `_check_pick_gates()` but testing through public `pick_tasks` is both correct and the established pattern from #630. No AC rewrite needed — intent is unambiguous.
- Implementation task #662 depends on this task per the planning dependency chain.

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current agent list
- Architect response: proceeded without challenge; low-risk test task following exact established pattern

### Verdict: APPROVE
### Action Taken: Advanced #665 backlog -> todo. AC verified against codebase (gates.py L24-26, server.py L531-533, test_tdd_gate_non_impl_630.py). All 5 AC lines precise and testable. type:test tag present — no non-impl tag addition needed.

[[2026-04-06]] Mon 18:51
## Test-Writer Notes
- Test file: `tests/test_user_action_non_impl_661.py` (pre-existing — written during parent #661 test-writer phase; validated and confirmed for this task)
- Classes: `TestFromAC_UserActionNonImplFrozensets`, `TestFromAC_CheckTDD_UserActionExemption`, `TestFromAC_PickTasksUserActionExemption`
- Tests per category:
  - Membership / frozenset (happy): 2
  - Behavioral / check_tdd (happy + edge + boundary): 3
  - Behavioral / pick_tasks dispatch (happy + combined tag): 2
- Total: **7 tests, all FAIL** (confirmed via pytest)
- Ruff: all checks passed
- AC coverage:

| AC Line | Test(s) |
|---------|---------|
| "type:user-action" in _NON_IMPL_TAGS (gates.py) | test_type_user_action_in_non_impl_tags_gates |
| "type:user-action" in _PICK_NON_IMPL_TAGS (server.py) | test_type_user_action_in_pick_non_impl_tags_server |
| check_tdd() returns True for in-progress + type:user-action (no TW notes) | test_user_action_tag_in_progress_no_tdd_notes_passes, test_user_action_combined_with_scope_tag_passes, test_user_action_only_tag_empty_body_in_progress_passes |
| _check_pick_gates() returns True via pick_tasks for in-progress + type:user-action (no TW notes) | test_user_action_in_progress_no_tdd_notes_included_in_dispatch, test_user_action_combined_with_scope_tag_included_in_dispatch |
| All tests FAIL before implementation | CONFIRMED — 7/7 FAIL |
