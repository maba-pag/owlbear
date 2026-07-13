---
id: 665
title: 'Test: type:user-action in NON_IMPL_TAGS gate sets'
status: archived
priority: medium
created: 2026-04-06T16:46:57.2190253+02:00
updated: 2026-04-06T23:58:16.467589+02:00
started: 2026-04-06T23:58:16.467589+02:00
completed: 2026-04-06T23:58:16.467589+02:00
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

[[2026-04-06]] Mon 22:32
## Builder Notes
- Files changed: `tests/test_user_action_non_impl_661.py` (1 file, committed ab700c4)
- Implementation already present: `type:user-action` in `_NON_IMPL_TAGS` (gates.py) and `_PICK_NON_IMPL_TAGS` (server.py) was committed in 6ee05d3
- Test results: **7 passed** (all TestFromAC_* tests green)
  - TestFromAC_UserActionNonImplFrozensets: 2 tests
  - TestFromAC_CheckTDD_UserActionExemption: 3 tests
  - TestFromAC_PickTasksUserActionExemption: 2 tests
- Lint: ruff clean on gates.py and test file; pre-existing PLR0915/RUF059 in server.py (unrelated, not in task scope)
- Coverage: 7/7 tests pass targeting frozenset membership and gate function behavior
- No TestFromAC_* classes modified
- Retry context: tests were already failing (RED confirmed); implementation was committed in prior session; this builder pass confirmed GREEN and committed test file

[[2026-04-06]] Mon 23:31
## Review Evidence

### Tests
pytest: **7 passed, 0 failed** (quality-runner, independent run)
- `TestFromAC_UserActionNonImplFrozensets`: 2 ✓
- `TestFromAC_CheckTDD_UserActionExemption`: 3 ✓
- `TestFromAC_PickTasksUserActionExemption`: 2 ✓

### Lint
ruff exit 1 — violations in `server.py` only:
- L337 PLR0915 "Too many statements" — pre-existing, not in task scope
- L398 RUF059 "Unpacked variable never used" — pre-existing, not in task scope
Test file `test_user_action_non_impl_661.py`: **clean** ✓

### Coverage
- `owlbear.planner.gates`: 67% (below 90% threshold)
- `owlbear_mcp_kanban.server`: 28% (below 90% threshold)

Note: Both modules are large production files. The task's implementation contribution was two frozenset string additions. All AC-targeted code paths (frozenset membership + gate function behavior) are directly exercised by the 7 tests. Below-threshold numbers reflect large untested surfaces in pre-existing code, not gaps in new code. Deduction: −0.03.

### AC Compliance

| AC Line | Test(s) | Assertion | Status |
|---------|---------|-----------|--------|
| "type:user-action" in `_NON_IMPL_TAGS` (gates.py) | `test_type_user_action_in_non_impl_tags_gates` | `assert "type:user-action" in _NON_IMPL_TAGS` | PASS — confirmed at gates.py L27 |
| "type:user-action" in `_PICK_NON_IMPL_TAGS` (server.py) | `test_type_user_action_in_pick_non_impl_tags_server` | `assert "type:user-action" in _PICK_NON_IMPL_TAGS` | PASS — confirmed at server.py L534 |
| `check_tdd()` returns True for in-progress + `type:user-action`, no TW notes | 3 tests (basic, combined tags, minimal body) | `assert check_tdd(task) is True` | PASS |
| `_check_pick_gates()` returns True via `pick_tasks` for in-progress + `type:user-action`, no TW notes | 2 tests (basic, combined tags) | `assert {id} in ids` (dispatch list) | PASS |
| All tests FAIL before implementation (TDD RED) | Confirmed in test-writer notes; GREEN now | — | PASS |

### TestFromAC_* Integrity
- No TestFromAC_* classes modified or removed. All 3 classes retained, 7 tests intact. ✓

### Implementation Verification
- `gates.py` L24–28: `_NON_IMPL_TAGS` frozenset contains `"type:user-action"` ✓
- `server.py` L531–535: `_PICK_NON_IMPL_TAGS` frozenset contains `"type:user-action"` ✓

### Assertion Quality
All assertions are strong and would fail on a broken implementation:
- Frozenset membership: direct `in` check on imported frozenset — fails if string absent
- `check_tdd(task) is True`: strict identity check — fails if gate returns False or truthy non-bool
- `assert {id} in ids`: fails if task excluded from dispatch (gate incorrectly blocks)

### Deductions
| Item | Deduction |
|------|-----------|
| Module coverage below 90% threshold (pre-existing code, not new code gap) | −0.03 |

### Verdict
Confidence: **0.95** → **PASS**

[[2026-04-06]] Mon 23:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (no update needed) | `type:user-action` added to `_NON_IMPL_TAGS` (gates.py L27) and `_PICK_NON_IMPL_TAGS` (server.py L534). `copilot-instructions.md` has no tag/gate tables. `agent-common.instructions.md` L33 already documents NON_IMPL_TAGS pass-through. `r-project-standards` L83–84 and `r-pipeline-protocol` L226–241 already cover `type:user-action` fully. All docs accurate. |
| 2 | Module docstrings | Yes | N/A (no update needed) | `gates.py` — `check_tdd()`, `check_clarity()`, `check_gates()` docstrings accurate; module docstring describes gate 4 correctly without enumerating specific tags. `server.py` — `_check_pick_gates()` docstring accurate. No changes required. |
| 3 | External attribution | No | N/A | Pattern follows internal `test_tdd_gate_non_impl_630.py`. No external repos or articles used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/user-action-non-impl-tags-tests.md` exists and is linked from task body. Follow-up tasks: none needed (impl task #662 already existed). |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/665-*` files found)

[[2026-04-06]] Mon 23:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| "type:user-action" in _NON_IMPL_TAGS (gates.py) | gates.py L27 confirmed; test_type_user_action_in_non_impl_tags_gates PASSED | PASS |
| "type:user-action" in _PICK_NON_IMPL_TAGS (server.py) | server.py L534 confirmed; test_type_user_action_in_pick_non_impl_tags_server PASSED | PASS |
| check_tdd() returns True for in-progress + type:user-action, no TW notes | 3 tests passed (basic, combined tags, minimal body) | PASS |
| _check_pick_gates() returns True via pick_tasks for in-progress + type:user-action, no TW notes | 2 async tests passed (basic, combined tags) | PASS |
| All tests FAIL before implementation (TDD RED) | Confirmed in test-writer notes: 7/7 FAIL; now all GREEN | PASS |

### Test Results
- pytest (task-scoped): 7 passed, 0 failed
- pytest (full suite): 1 collection error in test_planner_gates.py (pre-existing from task #207, imports check_atomicity which no longer exists in gates.py; NOT in #665 scope)
- ruff: clean on test file

### Reviewer Evidence
Detailed PASS at .95 confidence. Thorough AC compliance table, assertion quality analysis, TestFromAC integrity check. Trusted code-level findings.

### Architect Quality: 4/5
All 5 AC lines precise and directly testable. Minor gap: no explicit edge case AC, but intent was clear and test-writer filled boundary cases naturally (empty body, combined tags). Follows established #630 pattern exactly.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 5 verified)
- Lint violations: 0 (clean)
- AC quality score 4 (above 3): 0
- Missing reviewer evidence: 0 (present and detailed)
- Full-suite failures in task scope: 0 (collection error is pre-existing, out of scope)

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ab700c4 | test | tests/test_user_action_non_impl_661.py | #665 |
| 47cef01 | chore | kanban task file, activity.jsonl | #665 |
