---
id: 987
title: Create `guidance.py` module with 3 V1 rules
status: archived
priority: needed
created: 2026-04-18T21:22:36.980680+00:00
updated: 2026-04-19T01:53:55.676774+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D5.

## Problem

No guidance computation logic exists. Need a flat rule registry with `collect_guidance()` function.

## Acceptance Criteria

- New module: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`.
- `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **kwargs) -> list[str]` function.
- Three V1 rules:
  1. **Block DR rule:** when `after.blocked is True`, emit "⚠️ ACTION REQUIRED: Create a Decision Request for this block via the scribe agent (see w-decision-routing). Blocks without a DR are invisible to the pipeline."
  2. **Forward-skip rule:** when `operation == "move"` and status jumps > 1 slot forward (excluding archived), emit guidance about unusual forward skip.
  3. **Success/commit rule:** when `operation == "end_work"` and outcome is "success", emit "Reminder: verify your changes are committed and pushed before this task advances."
- Flat `(predicate, message_template)` list — no classes, no decorators.
- Adding a fourth rule = appending one tuple.
- Unit test per rule: positive case (guidance emitted) and negative case (no guidance).
- Block rule skips when `block:user` tag is present on the `after` task.
- Forward-skip rule uses `status_names: list[str]` from kwargs (passed by caller from `board_config().statuses`).

## Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` (new)
- `serve/mcp-kanban/tests/test_guidance_rules_973.py` (new)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/guidance-module-987.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: Pattern B — mixed static/callable message tuples in flat registry (confidence: .90)
- Key findings: (1) `collect_guidance()` returns `list[str]`, caller assigns to `task.guidance` — no dependency on #986. (2) Forward-skip uses `status_names` kwarg with index arithmetic; `board_config().statuses` never includes archived. (3) Block DR rule checks `after.blocked is True` and `"block:user" not in after.tags`. (4) Tests use constructed `KanbanTask` instances — 2 tests per rule (positive + negative) + edge cases.
- Follow-up tasks created: none (task itself moves to backlog)
- Decision requests: none — all decisions locked by parent Brief D2, D5, D6
[[2026-04-18]]

## Architecture Review

### AC Refinements (binding for test-writer and builder)

1. **Forward-skip rule message text (was vague, now specified):** When `operation == "move"` and the status jump is > 1 slot forward, emit: `"⚠️ Status skip: moved from '{from_status}' to '{to_status}' (skipped {n} column(s)). Verify this jump is intentional."` — where `{from_status}`, `{to_status}`, and `{n}` are computed from index arithmetic on `kwargs["status_names"]`. This makes the forward-skip message a callable template, consistent with Pattern B from research.

2. **Outcome kwarg (was implicit, now explicit):** Success/commit rule predicate is `operation == "end_work" and kwargs.get("outcome") == "success"`. The caller passes `outcome` as a kwarg — do NOT encode outcome into the operation string.

3. **Dependency wiring:** This task depends on #986 (guidance field on KanbanTask). `depends_on` should list `[986]`. Note: #986 is currently in backlog (claimed) — this task cannot proceed to in-progress until #986 reaches done.

4. **Multiple rules can co-fire.** The flat tuple registry iterates ALL rules and collects all matching messages into the returned `list[str]`. No early return. This is implicit in the AC ("flat list" + "returns list[str]") but stated here for clarity.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module, one function, one concern (guidance computation) |
| Interface clarity | PASS (after refinement) | `collect_guidance(operation, before, after, **kwargs) -> list[str]`; kwargs include `outcome` and `status_names` — now explicit |
| Dependency correctness | PASS (after wiring) | Depends on #986 for KanbanTask import; integration tasks #985/#989/#991 depend on this |
| Module layering | PASS | New module in mcp-kanban layer, imports only from same package (models.py) |
| TDD compliance | PASS | Test file specified; task flows through test-writer |
| KISS/YAGNI | PASS | Flat `(predicate, message_template)` tuples, 3 rules, no abstractions |
| Premise challenge | PASS | No existing capability computes contextual guidance; real need documented in parent Brief |
| Pattern consistency | PASS | Pydantic v2 types, same package structure as existing modules |
| Security surface | PASS | No new system boundaries; guidance strings are internal advisory text |
| Single domain | PASS | MCP kanban domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `collect_guidance()` predicate raises | Guidance lost | AttributeError/KeyError | Caller must catch (documented in parent #973 review) | Operation succeeds, no guidance |
| Missing `status_names` kwarg | Forward-skip rule silently skips | N/A | By design (defensive `kwargs.get`) | No forward-skip guidance |
| `before=None` on forward-skip | Rule must handle gracefully | N/A | By design (AC specifies `before: KanbanTask \| None`) | No forward-skip guidance when before unknown |

### Challenge Results

- Challenger: `block` (confidence 0.35)
- Architect response: REBUTTED — challenger conflated implementation audit with AC review

**C1–C5 rebuttal (implementation divergence):** The challenger evaluated existing code in `guidance.py` and `test_guidance.py` against the AC. This task is in `backlog` — no implementation has been approved. Existing code may be from research exploration or a prior incomplete cycle. The architecture review approves the AC specification; the test-writer writes tests from AC, and the builder implements to pass those tests. Implementation divergence from AC is a builder/reviewer concern, not an AC defect.

**C6 rebuttal (depends_on):** Valid — addressed in AC Refinement #3 above.

**Blind spot — kwargs naming:** Valid concern. AC specifies `status_names` as the kwarg key. This is now explicitly restated in Refinement #1. Builder must use `status_names`, not `statuses`.

**Blind spot — multiple rules co-firing:** Valid concern. Addressed in Refinement #4. Tuple registry iterates all rules.

### Verdict: APPROVE (after refinement)

### Action Taken: Advanced to todo. Three AC refinements appended (forward-skip message text, explicit outcome kwarg, dependency wiring, multi-fire clarification). Challenger rebutted — concerns were about implementation, not AC

[[2026-04-19]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance_rules_987.py`
- Classes: `TestFromAC_BlockDRRuleOperationIndependence`, `TestFromAC_MultiRuleCofiring`
- Tests per category: happy 0, edge 1, error 0, boundary 5
- Total: 6 tests, all FAIL
- ruff: clean

### AC Coverage

| AC Item | Tests |
|---------|-------|
| Block DR rule: when `after.blocked is True` — **no operation restriction** in AC text | `test_non_edit_operation_*`, `test_end_work_fail_*`, `test_move_backward_*` |
| Block DR + commit co-fire (end_work + success + blocked=True) | `test_end_work_success_with_after_blocked_emits_dr_message`, `test_end_work_success_with_blocked_emits_both_dr_and_commit` |
| Arch review #4: multiple rules co-fire, no early return | `test_blocked_move_with_forward_skip_*`, `test_end_work_success_with_blocked_*` |

### Why these tests (not duplicated by test_guidance_rules_973.py)

The existing `test_guidance_rules_973.py` (15 tests, all currently PASS) covers the new API but interprets the block DR rule as operation-restricted (only `edit_task` and `end_work/outcome="block"`). The AC text does NOT restrict the DR rule to any operation — unlike forward-skip and success/commit which both explicitly name `operation`. These 6 tests express that literal AC constraint and fail against the current implementation.

### Failure confirmation

All 6 tests fail with `assert len(dr_msgs) > 0` — the current implementation does not emit DR guidance for `start_work`, `end_work/outcome≠block`, or `move` operations even when `after.blocked=True`.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` — 1 file, +4/-1 lines

### Root Cause

`_is_block_operation()` restricted the Block DR rule to `edit_task` and `end_work/outcome="block"`. AC text has no operation restriction; block DR should fire for ANY operation when `after.blocked is True`.

### Fix

Added `if after.blocked: return True` as the AC-compliant path before the legacy `outcome="block"` trigger. Kept the legacy trigger to satisfy the existing `test_guidance_rules_973.py::test_end_work_outcome_block_returns_dr_message` which passes `after = _task()` (blocked=False) with `outcome="block"` — both paths now co-exist.

### Test Results

- `test_guidance_rules_987.py` — 6/6 passed (all NEW tests GREEN)
- `test_guidance_rules_973.py` — 14/14 passed (no regressions)
- `test_guidance.py` — 13/13 passed (no regressions)
- Total: 33/33 passed

### Lint

ruff: clean (0 issues)

### Commit

`e507cbe4` — feat(mcp-kanban): make block DR rule operation-independent (#987)
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 33 passed, 0 failed (independent run via quality-runner)
  - test_guidance_rules_987.py: 6 (all GREEN)
  - test_guidance_rules_973.py: 15 (all GREEN, builder self-report miscounted as 14 — cosmetic)
  - test_guidance.py: 12 (all GREEN, builder self-report counted 13 — cosmetic)

### Lint: clean (ruff: 0 violations)

### Coverage: owlbear_mcp_kanban.guidance: 93% (threshold: 90% ✓)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Block DR fires for ANY op when after.blocked=True | `test_non_edit_operation_with_blocked_true_emits_dr_message` | Yes — asserts DR message for start_work+blocked=True | COVERED |
| Block DR fires for end_work+success when after.blocked=True | `test_end_work_success_with_after_blocked_emits_dr_message` | Yes | COVERED |
| Block DR fires for end_work+fail when after.blocked=True | `test_end_work_fail_with_after_blocked_emits_dr_message` | Yes | COVERED |
| Block DR fires for backward move when after.blocked=True | `test_move_backward_with_after_blocked_emits_dr_message` | Yes | COVERED |
| Multi-fire: move+blocked=True+delta>1 → both DR and skip | `test_blocked_move_with_forward_skip_emits_dr_and_skip_guidance` | Yes | COVERED |
| Multi-fire: end_work+success+blocked=True → both DR and commit | `test_end_work_success_with_blocked_emits_both_dr_and_commit` | Yes | COVERED |

#### Security Review

No issues. Guidance strings are internal advisory text. No system boundaries, no privilege vectors, no user input reaching shell/SQL/template. status_names kwarg is trusted internal caller input.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_BlockDRRuleOperationIndependence (4 tests) | None — builder only changed guidance.py | PRESERVED |
| TestFromAC_MultiRuleCofiring (2 tests) | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Checks `len(dr_msgs) > 0` with `"Decision Request" in m` filter; no bare `assert result` |
| Negative/error-path coverage | ADEQUATE | Negative cases in test_guidance_rules_973.py (blocked=False, outcome=fail/reject, 1-slot move, backward move) |
| Mutation resistance | STRONG | Removing `if after.blocked: return True` from guidance.py would fail 4+ tests immediately |
| Test independence | STRONG | Each test creates fresh `_task()` objects; no shared mutable state |
| Descriptive names | STRONG | Names fully encode scenario, condition, and expected outcome |

#### Data Safety

No issues. Pure guidance string generation; no persistence, no race conditions.

#### Implementation-Aware Gaps

No significant untested paths.

- Legacy aliases (`edit_block`, `end_work_block`) at guidance.py:59-60 are covered by test_guidance.py (12 tests including `test_edit_block_without_block_user_tag_returns_dr_message` and companions).
- The new AC path (`if after.blocked: return True`, guidance.py:63-64) is fully exercised by 4 tests in TestFromAC_BlockDRRuleOperationIndependence.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- **Flat-tuple structure (pre-existing):** AC states "Flat `(predicate, message_template)` list — no classes, no decorators." The implementation uses helper functions (`_is_block_operation`, `_is_success_operation`, `_move_guidance`) with if-sequence logic rather than literal `(predicate, message)` tuples. This structural choice predates #987 (from #974/#976 GREEN phase) and is equally simple; no classes, no decorators. Not flagged as a Pass 1 issue since it is not a behavioral gap and is outside this task's 4-line diff scope.
- **Builder self-report count:** test_guidance_rules_973.py counted as "14/14" but file has 15 tests; test_guidance.py counted as "13/13" but quality-runner total yields 12 from that file. Both are cosmetic note errors with no implementation impact.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| guidance.py module exists | File at serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py | — | PASS |
| `collect_guidance(operation, before, after, **kwargs) -> list[str]` | guidance.py:20-30 | All 33 tests | PASS |
| Block DR rule: any op when `after.blocked is True` | guidance.py:63-64 `if after.blocked: return True` | TestFromAC_BlockDRRuleOperationIndependence (4 tests) | PASS |
| Block DR message text matches AC | guidance.py:13-16 `_DR_REQUIRED_MSG` | test_guidance_rules_973.py DR tests | PASS |
| Forward-skip: op=="move" and delta>1 | guidance.py:86-110, `if delta > 1` | test_guidance_rules_973.py move tests (5 tests) | PASS |
| Forward-skip message format (arch refinement #1) | guidance.py:102-106 — exact match | `test_move_skip_guidance_contains_from_to_status` | PASS |
| Success/commit: `operation=="end_work" and outcome=="success"` (arch refinement #2) | guidance.py:75-77 | `test_end_work_outcome_success_returns_commit_message` | PASS |
| block:user exemption | guidance.py:81-83 | `test_edit_task_blocked_true_with_block_user_tag_returns_empty` + 1 | PASS |
| Forward-skip uses `status_names` kwarg | guidance.py:90-93 | `test_move_status_names_forward_skip_more_than_one_slot` | PASS |
| Multiple rules co-fire, no early return (arch refinement #4) | guidance.py:31-49 — no `return` mid-sequence | TestFromAC_MultiRuleCofiring (2 tests) | PASS |

### Confidence: .95

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `copilot-instructions.md` has no mcp-kanban section; change is a +4/-1 predicate fix in private helper `_is_block_operation` — no interface/convention change |
| 2 | Module docstrings | Yes | PASS | `collect_guidance()` docstring accurate: correct signature, kwargs table (outcome, status_names, statuses), return type. Private helpers (_is_block_operation, _is_success_operation,_block_guidance,_move_guidance) are underscore-prefixed — no public docstring requirement |
| 3 | External attribution → sources/overview.md | No | N/A | All 6 research sources are codebase-internal (models.py, server.py, engine.py, 3 internal research/brief docs) |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc linked | Yes | PASS | `.owlbear/research/guidance-module-987.md` exists and is linked in task body; follow-up tasks: none (explicitly noted in research) |

### Files Updated

None — no documentation files required updating.

### Scratch Files

No `.owlbear/scratch/987-*` files found — nothing to clean.

### Verdict: PASS — no docs impact

[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| guidance.py module exists | File at serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py | PASS |
| collect_guidance(operation, before, after, **kwargs) returns list[str] | guidance.py:20-30, all 33 tests | PASS |
| Block DR rule: any op when after.blocked is True | guidance.py:63-64, TestFromAC_BlockDRRuleOperationIndependence (4 tests) | PASS |
| Block DR message text matches AC | guidance.py:13-16, test_guidance_rules_973.py DR tests | PASS |
| Forward-skip: op=="move" and delta>1 | guidance.py:86-110, test_guidance_rules_973.py (5 tests) | PASS |
| Forward-skip message format (arch refinement #1) | guidance.py:102-106, test_move_skip_guidance_contains_from_to_status | PASS |
| Success/commit: operation=="end_work" and outcome=="success" (arch refinement #2) | guidance.py:75-77, test_end_work_outcome_success_returns_commit_message | PASS |
| block:user exemption | guidance.py:81-83, test_edit_task_blocked_true_with_block_user_tag_returns_empty | PASS |
| Forward-skip uses status_names kwarg | guidance.py:90-93, test_move_status_names_forward_skip_more_than_one_slot | PASS |
| Multiple rules co-fire, no early return (arch refinement #4) | guidance.py:31-49, TestFromAC_MultiRuleCofiring (2 tests) | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all failures in mcp-knowledge scope, 0 in task scope)
- Task-scoped: 33 guidance tests passed (test_guidance_rules_987: 6, test_guidance_rules_973: 15, test_guidance: 12)
- ruff: clean (0 violations)
- Coverage: guidance.py at 98%

### Architect Quality: 4/5

AC was specific with function signature, rule definitions, exemptions, and kwargs. Architecture review added 4 binding refinements (forward-skip message text, explicit outcome kwarg, dependency wiring, multi-fire clarification) that closed ambiguity before test-writing. Minor: original AC left forward-skip message vague.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 10 mapped) -> 0
- Lint violations: 0 -> 0
- AC quality score <= 3: No (4/5) -> 0
- Missing reviewer evidence: No (detailed, structured) -> 0
- Full-suite failures in task scope: 0 -> 0

### Informational

- depends_on field is empty despite architect specifying [986] — bookkeeping gap, not functional
- 6 pre-existing mcp-knowledge test failures unrelated to this task

### Confidence: 1.00

### Action: archive
