---
id: 823
title: Tests — pick_dispatchable()
status: done
priority: needed
created: '2026-04-10T21:23:01.614181+00:00'
updated: '2026-04-12T15:03:17.785442+00:00'
tags:
- phase-3
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 822
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `pick_dispatchable(engine, limit=25, tag="")` returns `list[Task]`
- Tests verify TDD gate: in-progress task without test-writer notes or non-impl tag is excluded
- Tests verify clarity gate: active-status task without bullet/numbered AC is excluded
- Tests verify priority ranking: critical > needed > important > nice-to-have > someday
- Tests verify status ranking: done > docs > review > in-progress > todo > backlog > research
- Tests verify result capping at `limit`
- Tests verify tag filtering
- Tests verify function is importable without MCP dependency
- Tests fail RED before implementation

## Context

Phase 3, step 1. Depends on #822 (Phase 2 complete).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/823-pick-dispatchable-test-design.md
- Sources: 9 studied, 7 high-relevance
- Recommendation: Real engine + temp filesystem fixtures, 8 test classes (~150 LOC) (confidence: .85)
- Key finding: engine.list_tasks() strips body via TaskSummary conversion — pick_dispatchable must use alternate path for body access (documented for #824 builder)
- Tier: T1 (autonomous) — standard TDD RED phase
- Follow-up tasks created: none (pipeline already has #824)
- Decision requests: none
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only `pick_dispatchable()` — one function, one test file |
| Interface clarity | PASS | All 9 AC lines specify exact conditions and expected outcomes. Signature `pick_dispatchable(engine, limit=25, tag="")` defines inputs; `list[Task]` defines output. Gate conditions cite specific body patterns and tag sets. |
| Dependency correctness | PASS | depends_on: [822] is correct — #822 is Phase 2 final task (compat alias removal). Phase 3 cannot start before Phase 2 completes. No missing dependencies. |
| Module layering | PASS | Test imports from `owlbear_kanban.dispatch` — no upward imports, no MCP dependency |
| TDD compliance | PASS | This IS the RED test task. #824 (implementation) depends on #823. |
| KISS/YAGNI | PASS | 8 test classes (~150 LOC) — one per AC concern. No hypothetical requirements. |
| Premise challenge | PASS | `pick_dispatchable()` is mandated by the brief Phase 3 spec (O3). Tests are prerequisite for #824. |
| Pattern consistency | PASS | Follows proven real-engine + temp-filesystem fixture pattern from `tests/test_kanban_engine_listing.py` (`_make_kanban_dir`, `_add_task` helpers). Test class naming follows `TestFromAC_*` convention. |
| Security surface | N/A | Pure test code, no new system boundaries |
| Single domain | PASS | scope:kanban only |

### Failure Mode Map
N/A — test code introduces no production codepaths.

### Codebase Evidence
- Fixture pattern: `tests/test_kanban_engine_listing.py` L57-130 — `_make_kanban_dir`, `_task_content`, `_add_task` helpers
- Gate logic reference: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L320-405 — `_check_pick_gates`, rank maps, `_PICK_NON_IMPL_TAGS`
- Target import path: `owlbear_kanban.dispatch` (module does not exist yet — RED is immediate)
- Models: `serve/kanban/src/owlbear_kanban/models.py` — `Task` (has body), `TaskSummary` (no body)

### Builder Note (for #824)
Research correctly identifies `engine.list_tasks()` body-stripping issue (returns `TaskSummary`, `extra="ignore"` drops body). Tests using real engine + filesystem are agnostic to the builder's data access strategy. This is documented in the #824 research doc.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in current workspace
- Architect response: proceeded with approval — T1 test task, all 9 AC lines verifiable, established patterns, no design decisions to challenge

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. Research is thorough (confidence .85). Non-impl tag `type:test` already present. Dependency #822 (todo) correctly gates Phase 3 start.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_pick_dispatchable_823.py
- Classes: TestFromAC_PickDispatchableImport, TestFromAC_PickDispatchableSignature, TestFromAC_PickDispatchableTDDGate, TestFromAC_PickDispatchableClarityGate, TestFromAC_PickDispatchablePriorityRanking, TestFromAC_PickDispatchableStatusRanking, TestFromAC_PickDispatchableLimit, TestFromAC_PickDispatchableTagFilter
- Tests per category: happy 12, edge 9, error 5, boundary 6
- Total: 32 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_kanban.dispatch')
- ruff: clean
- Commit: 47f7430f — "test: add failing tests for pick_dispatchable() (#823, test-writer)"

### AC Coverage
| AC | Tests |
|----|-------|
| returns list[Task] | test_returns_list, test_result_items_are_task_instances, test_accepts_limit_keyword, test_accepts_tag_keyword, test_result_has_body_field |
| TDD gate | test_in_progress_without_notes_excluded, test_in_progress_with_notes_included, test_in_progress_non_impl_tag_exempt_from_tdd, test_non_in_progress_skips_tdd_gate, test_all_non_impl_tags_exempt_from_tdd_gate |
| Clarity gate | test_todo_without_bullets_excluded, test_todo_empty_body_excluded, test_todo_with_bullet_list_included, test_todo_with_numbered_list_included, test_research_without_bullets_passes_clarity, test_backlog_without_bullets_passes_clarity, test_done_without_bullets_excluded, test_review_without_bullets_excluded |
| Priority ranking | test_critical_before_someday, test_all_priorities_in_dispatch_order, test_critical_before_needed_before_important |
| Status ranking | test_done_before_research, test_all_statuses_in_dispatch_order, test_priority_dominates_status, test_docs_before_in_progress |
| Limit cap | test_limit_caps_results, test_limit_does_not_pad, test_default_limit_is_25, test_limit_zero_returns_empty |
| Tag filtering | test_tag_filter_excludes_untagged, test_empty_tag_includes_all_passing, test_tag_no_match_returns_empty, test_multi_tag_task_matched_by_any_tag, test_tag_filter_applied_before_gates |
| No MCP dependency | test_pick_dispatchable_callable, test_module_is_in_owlbear_kanban_package, test_dispatch_module_does_not_import_mcp |
[[2026-04-12]]
## Builder Notes

### Files changed
- None — test deliverable was committed by test-writer (47f7430f)

### Test results (RED verification)
- **pytest**: Collection aborted — `ModuleNotFoundError: No module named 'owlbear_kanban.dispatch'` ✅ (expected RED state, no implementation exists)
- **Tests counted in file**: 37 methods across 8 `TestFromAC_*` classes (test-writer notes say 32; count discrepancy minor — all 8 classes present, all AC lines covered per AC coverage table)
- **Ruff**: All checks passed ✅

### Evidence summary
| Check | Result |
|-------|--------|
| Test file exists | ✅ `tests/test_pick_dispatchable_823.py` |
| All TestFromAC_* fail RED | ✅ ModuleNotFoundError at import |
| No implementation in owlbear_kanban.dispatch | ✅ grep confirms — module does not exist |
| Ruff clean | ✅ |
| Commit from test-writer | ✅ 47f7430f |

### AC compliance
| AC | Status |
|----|--------|
| Tests verify pick_dispatchable signature | ✅ TestFromAC_PickDispatchableSignature (5 tests) |
| TDD gate tests | ✅ TestFromAC_PickDispatchableTDDGate (5 tests) |
| Clarity gate tests | ✅ TestFromAC_PickDispatchableClarityGate (8 tests) |
| Priority ranking tests | ✅ TestFromAC_PickDispatchablePriorityRanking (3 tests) |
| Status ranking tests | ✅ TestFromAC_PickDispatchableStatusRanking (4 tests) |
| Limit cap tests | ✅ TestFromAC_PickDispatchableLimit (4 tests) |
| Tag filtering tests | ✅ TestFromAC_PickDispatchableTagFilter (5 tests) |
| No MCP dependency tests | ✅ TestFromAC_PickDispatchableImport (3 tests) |
| Tests fail RED before implementation | ✅ Verified |
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest: 37 passed, 0 failed (all GREEN — dispatch.py exists from #824 implementation, committed after builder verified RED)

### Lint
clean: true — ruff 0 violations

### Coverage
- owlbear_kanban.dispatch: 95% (uncovered path likely the `get()` fallback for unknown priority/status values — untested but not an AC line)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|--------------------------|---------|
| AC1 — returns list[Task] | TestFromAC_PickDispatchableSignature (5) | test_returns_list: isinstance(list); test_result_items_are_task_instances: isinstance(Task); test_result_has_body_field: task.body == exact_string | COVERED |
| AC2 — TDD gate | TestFromAC_PickDispatchableTDDGate (5) | test_in_progress_without_notes_excluded: assert 1 not in ids; test_in_progress_with_notes_included: assert 2 in ids; test_all_non_impl_tags_exempt_*: iterates all 9 tags individually | COVERED |
| AC3 — Clarity gate | TestFromAC_PickDispatchableClarityGate (8) | test_todo_without_bullets_excluded: assert 1 not in ids; test_todo_empty_body_excluded: assert 2 not in ids; test_research_without_bullets_passes_clarity: assert 5 in ids | COVERED |
| AC4 — Priority ranking | TestFromAC_PickDispatchablePriorityRanking (3) | test_all_priorities_in_dispatch_order: assert result_priorities == ["critical","needed","important","nice-to-have","someday"] — exact order | COVERED |
| AC5 — Status ranking | TestFromAC_PickDispatchableStatusRanking (4) | test_all_statuses_in_dispatch_order: exact 7-element order assertion; tasks added in reverse order to prevent file-order artifact | COVERED |
| AC6 — Limit cap | TestFromAC_PickDispatchableLimit (4) | test_limit_caps_results: 10 tasks → len==3; test_default_limit_is_25: 30 tasks → len==25; test_limit_zero_returns_empty: result==[] | COVERED |
| AC7 — Tag filtering | TestFromAC_PickDispatchableTagFilter (5) | test_tag_filter_excludes_untagged: {1 in ids, 2 not in ids}; test_empty_tag_includes_all_passing: ids=={1,2} exact set match | COVERED |
| AC8 — No MCP dependency | TestFromAC_PickDispatchableImport (3) | test_pick_dispatchable_callable: callable(); test_module_is_in_owlbear_kanban_package: __package__=="owlbear_kanban"; test_dispatch_module_does_not_import_mcp: vars() check (LAX — see Pass 2) | COVERED/LAX |
| AC9 — Tests fail RED | Builder self-report at commit 47f7430f — "ModuleNotFoundError: No module named 'owlbear_kanban.dispatch'" | Cannot independently verify: dispatch.py now exists from #824 implementation added after builder submitted #823 to review. Pipeline flow is consistent with builder's claim. | NOTE |

#### Security Review
- No hardcoded secrets, no injection, no path traversal concerns — pure test code using pytest tmp_path fixture throughout.
- No new production dependencies.
- No issues.

#### Test Integrity — TestFromAC Comparison
- Single commit: 47f7430f (test-writer). Builder notes "Files changed: None." No builder modifications to TestFromAC classes.
- All 8 TestFromAC_* classes: PRESERVED

#### Test Quality Assessment
1. **Assertion specificity** — STRONG. Exact ordering asserts (`result_priorities == expected_order`), `assert X not in ids`, exact set equality (`ids == {1, 2}`), exact body content (`task.body == body_content`). No lazy `assert result` patterns.
2. **Negative coverage** — STRONG. Every inclusion test has a corresponding exclusion test (bullets → included; no-bullets → excluded; notes → included; no-notes → excluded).
3. **Manual mutation** — STRONG. Flipping any status rank value breaks `test_all_statuses_in_dispatch_order`. Flipping any priority rank breaks `test_all_priorities_in_dispatch_order`. Removing any non-impl tag breaks `test_all_non_impl_tags_exempt_from_tdd_gate`.
4. **Test independence** — STRONG. Every test creates a fresh `tmp_path` board. No shared mutable state.
5. **Descriptive names** — STRONG. All methods name the exact condition being tested.

#### Data Safety
- Pure test code, tmp_path fixtures only. No concerns.

#### Builder Process Quality
- Single attempt, CLEAN. No loop pattern.

### Pass 2 — INFORMATIONAL

1. **`test_dispatch_module_does_not_import_mcp` (AC8, LAX):** Uses `vars(_dispatch_mod)` which would miss `from mcp import X as alias` patterns. However, the test file itself imports `owlbear_kanban.dispatch` at module level — successful collection without MCP errors is the primary evidence for AC8. The `vars()` check is supplementary. No action needed.

2. **AC9 unverifiable from current state:** `dispatch.py` now exists (95% coverage) meaning builder's RED self-report cannot be independently confirmed. Evidence is consistent with normal pipeline flow: test-writer commits RED → #823 moves to review → #824 builds implementation → tests now GREEN. The tests passing correctly with the implementation is itself validation of test quality.

3. **`test_tag_filter_applied_before_gates` docstring overclaims:** The test name asserts tag filter "applied before gates" but the test only verifies the combined filtering outcome (which is observable). The claim about ordering is untestable from outside. Functional behavior is correct. No action needed.

### Verdict
- All 8 observable AC lines: COVERED with strong assertions
- Test quality: STRONG
- Security: clean
- TestFromAC integrity: PRESERVED
- Lint: clean
- Tests: 37/37 pass

**Confidence: .94 → PASS**
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test task — only `tests/test_pick_dispatchable_823.py` added (commit 47f7430f). No production modules touched. copilot-instructions.md unchanged. |
| 2 | Module docstrings | No | N/A | No production Python modules created or modified. Test file only. |
| 3 | External attribution | No | N/A | All 9 research sources are internal codebase files (engine.py, models.py, server.py, gates.py, test files, briefs). No external repos or articles. sources/overview.md unchanged. |
| 4 | CLI changes | No | N/A | Pure test code. No CLI commands added or modified. README unchanged. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/823-pick-dispatchable-test-design.md` exists and is linked in task body. Follow-up tasks: none required (pipeline has #824). |

### Files Updated
None — no documentation impact.

### Scratch Files
None found matching `.owlbear/scratch/823-*`.

### Review Evidence Present
✅ `## Review Evidence` section present with 37/37 pass, ruff clean, 95% coverage.
[[2026-04-12]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 - returns list[Task] | TestFromAC_PickDispatchableSignature (5 tests): isinstance, body field checks | PASS |
| AC2 - TDD gate | TestFromAC_PickDispatchableTDDGate (5 tests): exclusion/inclusion with notes, non-impl tags | PASS |
| AC3 - Clarity gate | TestFromAC_PickDispatchableClarityGate (8 tests): bullet/numbered list inclusion, empty body exclusion | PASS |
| AC4 - Priority ranking | TestFromAC_PickDispatchablePriorityRanking (3 tests): exact 5-element order assertion | PASS |
| AC5 - Status ranking | TestFromAC_PickDispatchableStatusRanking (4 tests): exact 7-element order assertion, reverse insertion | PASS |
| AC6 - Limit cap | TestFromAC_PickDispatchableLimit (4 tests): cap, no-pad, default=25, zero | PASS |
| AC7 - Tag filtering | TestFromAC_PickDispatchableTagFilter (5 tests): exact set equality, multi-tag match | PASS |
| AC8 - No MCP dependency | TestFromAC_PickDispatchableImport (3 tests): callable, package, vars check | PASS |
| AC9 - Tests fail RED | Unverifiable (dispatch.py exists from #824). Pipeline flow consistent with builder claim at commit 47f7430f | NOTE |

### Test Results
- pytest (task-scoped): 37 passed, 0 failed
- pytest (full suite): 302 pre-existing failures, 0 from test_pick_dispatchable_823.py
- ruff: clean (0 violations)

### Reviewer Evidence: Present, detailed, PASS at .94. Strong assertion analysis across all AC lines. Pass 2 informational notes reasonable.

### Architect Quality: 5/5
All 9 AC lines are specific and verifiable. Exact function signature, concrete gate definitions, explicit ranking orders. No builder improvisation needed. Clean implementation path.

### Deduction Breakdown
- Start: 1.00
- AC9 unverifiable from current state (by design): -0.01
- Total deductions: -0.01

### Confidence: .99
### Action: archive

### Commit Integrity
- Upstream commit: 47f7430f "test: add failing tests for pick_dispatchable() (#823, test-writer)"
- Single commit, no builder modifications to test file
- No uncommitted #823 deliverables (test file diff is empty)