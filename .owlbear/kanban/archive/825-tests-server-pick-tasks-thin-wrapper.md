---
id: 825
title: Tests — Server pick_tasks thin wrapper
status: archived
priority: medium
created: '2026-04-10T21:23:15.034176+00:00'
updated: '2026-04-12T16:18:34.742518+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 824
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify server `pick_tasks` MCP tool calls `pick_dispatchable()` from engine
- Tests verify no inline gating logic remains in `server.py`
- Tests verify `pick_tasks` response format unchanged (dispatch wrapper with task details)
- Tests verify existing `pick_tasks` MCP contract preserved
- Tests fail RED before slimming

## Context

Phase 3, step 3. Depends on #824 (dispatch.py created).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/server-pick-tasks-thin-wrapper-tests.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: 14 tests across 4 classes in test_server_pick_tasks_thin_wrapper_825.py (confidence: 0.88)
  - AC1 delegation: 4 RED tests using patch("owlbear_mcp_kanban.server.pick_dispatchable")
  - AC2 no inline gating: 3 RED tests using hasattr checks for _check_pick_gates and 6 _PICK_* constants
  - AC3 response format: 4 PASS tests as regression guards
  - AC4 MCP contract: 3 PASS tests as regression guards
- RED failure modes: AC1 raises AttributeError (server has no pick_dispatchable import); AC2 asserts fail (constants still present)
- Follow-up tasks: none needed (task is already decomposed in chain #823-#826)
- Decision requests: none
[[2026-04-12]]
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | Pure test task — RED tests for server pick_tasks thin wrapper |\n| Interface clarity | PASS | AC defines what to test; research doc specifies mock targets, RED/PASS classification, and failure modes |\n| Dependency correctness | PASS | Depends on #824 (dispatch.py). Correct — ensures pick_dispatchable exists for test reference. RED tests fail with AttributeError regardless. |\n| Module layering | PASS | Tests only import server module and mock at module boundary |\n| TDD compliance | PASS | This IS the RED phase test task preceding #826 GREEN slimming |\n| KISS/YAGNI | PASS | 14 tests across 4 classes is proportional to 5 AC lines |\n| Premise challenge | PASS | Required by Phase 3 O3 outcome — dispatch extraction from server |\n| Pattern consistency | PASS | Follows test_kanban_mcp_migration.py patterns (engine-based AppContext, _make_mcp_ctx helpers) |\n| Security surface | N/A | Test task, no new system boundaries |\n| Single domain | PASS | scope:mcp-kanban only |\n\n### Codebase Evidence\n- server.py L323-397: contains _check_pick_gates, _PICK_AC_PATTERN, _PICK_CLARITY_STATUSES, _PICK_NON_IMPL_TAGS, _PICK_PRIORITY_RANK, _PICK_STATUS_RANK, _PICK_MAX_PRIORITY_RANK, _PICK_MAX_STATUS_RANK — 8 symbols targeted by AC2 hasattr checks\n- dispatch.py does not exist yet in owlbear_kanban — confirms RED state for AC1\n- Existing test helpers in test_kanban_mcp_migration.py L595-834 validate engine-based pick_tasks delegation pattern\n- test_tool_annotations_494.py provides _get_tool_annotations helper for AC4 contract tests\n\n### AC Notes\n- AC5 \"Tests fail RED before slimming\" — AC1 (delegation) and AC2 (no inline gating) fail RED; AC3 (response format) and AC4 (MCP contract) pass as regression guards. Research doc section 3.1 clarifies this categorization.\n- AC1 \"from engine\" wording: pick_dispatchable is a standalone function in owlbear_kanban.dispatch that takes engine as parameter. Tested via patch(\"owlbear_mcp_kanban.server.pick_dispatchable\"). Clear from research.\n\n### Challenge Results\n- Challenger: FALLBACK — challenger subagent not in available agent list\n- Architect response: Proceeded with APPROVE based on thorough AC assessment and codebase verification\n\n### Verdict: APPROVE\n### Action Taken: Advanced to todo. AC is precise and verifiable. Research doc provides detailed 14-test specification with clear RED/PASS classification. Dependency chain #823-#824-#825-#826 is correctly ordered.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_server_pick_tasks_thin_wrapper_825.py
- Classes: TestFromAC_PickTasksDelegation, TestFromAC_NoInlineGating, TestFromAC_PickTasksResponseFormat, TestFromAC_PickTasksMCPContract
- Tests per category: happy 4, edge 0, error 3, boundary 0 (RED phase); regression guards 7 (PASS)
- Total: 14 tests — 7 FAIL RED, 7 PASS (regression guards)
- ruff: clean
- Commit: 1e435518 on dev

AC coverage:
| AC | Tests | RED/PASS | Failure mode |
|----|-------|----------|--------------|
| AC1: delegates to pick_dispatchable | 4 | RED | AttributeError (no import in server.py) |
| AC2: no inline gating constants | 3 | RED | AssertionError (symbols still present) |
| AC3: response format preserved | 4 | PASS | regression guard |
| AC4: MCP contract preserved | 3 | PASS | regression guard |
| AC5: tests fail RED | all 7 RED confirmed | ✅ | — |
[[2026-04-12]]
## Builder Notes

### Files Changed
- None — no code changes. This is a RED test task; tests were committed by test-writer at 1e435518.

### RED State Verification
Ran `uv run pytest tests/test_server_pick_tasks_thin_wrapper_825.py -v --tb=short --override-ini=addopts=`

**Results: 7 failed, 7 passed (exit code 1) — exactly as designed.**

| Class | Tests | RED/PASS | Confirmed |
|-------|-------|----------|-----------|
| TestFromAC_PickTasksDelegation | 4 | RED | ✅ All 4 fail with AttributeError: server module does not have the attribute 'pick_dispatchable' |
| TestFromAC_NoInlineGating | 3 | RED | ✅ All 3 fail with AssertionError (_check_pick_gates/_PICK_* still present) |
| TestFromAC_PickTasksResponseFormat | 4 | PASS | ✅ All 4 pass as regression guards |
| TestFromAC_PickTasksMCPContract | 3 | PASS | ✅ All 3 pass as regression guards |

### Lint Status
`uv run ruff check tests/test_server_pick_tasks_thin_wrapper_825.py` → **All checks passed!** (exit code 0)

### AC Coverage Evidence
- **AC1 (delegates to pick_dispatchable):** 4 RED tests confirm server.py lacks `pick_dispatchable` import — AttributeError on patch target ✅
- **AC2 (no inline gating):** 3 RED tests confirm `_check_pick_gates`, `_PICK_PRIORITY_RANK`/`_PICK_STATUS_RANK`, `_PICK_AC_PATTERN`/`_PICK_CLARITY_STATUSES`/`_PICK_NON_IMPL_TAGS` still present in server.py ✅
- **AC3 (response format):** 4 PASS regression guards verify dispatch dict structure with current implementation ✅
- **AC4 (MCP contract):** 3 PASS regression guards verify registration, readOnlyHint, idempotentHint ✅
- **AC5 (tests fail RED before slimming):** 7 RED confirmed ✅

### Note for #826 Builder
Task #826 research notes that AC3 tests at `test_dispatch_entries_have_task_id_and_status` and `test_task_id_is_integer` will break after the thin wrapper refactor because the new `pick_dispatchable` reads from `engine._tasks_dir.glob("*.md")` rather than `engine.list_tasks()`. The #826 builder must add `patch("owlbear_mcp_kanban.server.pick_dispatchable")` to those tests per #826 AC6 (already documented in #826 research §3.3 and architecture review).
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest: 7 passed, 7 failed (exit code 1) — exactly as designed for RED phase
- Failures confirmed by independent run:
  - AC1 (4): `AttributeError: module 'owlbear_mcp_kanban.server' does not have attribute 'pick_dispatchable'`
  - AC2 (3): `AssertionError: _check_pick_gates must be removed / _PICK_PRIORITY_RANK must be removed / _PICK_AC_PATTERN must be removed`

### Lint
clean: true (0 violations on test file)

### Coverage
owlbear_mcp_kanban.server: 46% (expected — RED test task adds no new execution paths)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: delegates to pick_dispatchable | 4 RED tests in TestFromAC_PickTasksDelegation | Yes — AttributeError until import exists; then assert_called_once/call_args assertions enforce call contract | COVERED |
| AC2: no inline gating in server.py | 3 RED tests in TestFromAC_NoInlineGating | Yes — 6 specific symbols checked; fail immediately if any remain | COVERED |
| AC3: response format unchanged | 4 PASS tests in TestFromAC_PickTasksResponseFormat | Yes — exact key-set assertion `== {"task_id", "status"}`; exact value check for empty case | COVERED |
| AC4: MCP contract preserved | 3 PASS tests in TestFromAC_PickTasksMCPContract | Yes — registration by name; readOnlyHint=True; idempotentHint=True | COVERED |
| AC5: tests fail RED before slimming | 7 RED confirmed by independent run | Observable — 7 failures, correct failure modes | COVERED |

#### Security Review
No issues — test-only file. No system boundaries, user input, or secrets.

#### Test Integrity
Builder made zero code changes (RED task — no implementation). No TestFromAC modifications to compare. N/A.

#### Test Quality
| Class | Dimension | Rating | Notes |
|-------|-----------|--------|-------|
| TestFromAC_PickTasksDelegation | Assertion specificity | ADEQUATE | assert_called_once + call_args kwargs checks are specific; engine parameter not verified (see Pass 2) |
| TestFromAC_PickTasksDelegation | Test independence | STRONG | No shared mutable state |
| TestFromAC_NoInlineGating | Assertion specificity | STRONG | Exact hasattr checks on 6 named symbols |
| TestFromAC_PickTasksResponseFormat | Assertion specificity | STRONG | Exact key-set comparison `== {"task_id", "status"}`; exact empty-result equality |
| TestFromAC_PickTasksMCPContract | Assertion specificity | STRONG | Registration + annotation attribute checks |

Overall: ADEQUATE–STRONG across all classes. No WEAK ratings.

#### Data Safety, Necessity: N/A (test task, no new production code)

#### Builder Process Quality: CLEAN (1 builder notes section, no retries)

### Pass 2 — INFORMATIONAL

**6.3 Minor test gap — engine not verified in AC1 delegation tests:** All 4 AC1 tests patch `pick_dispatchable` and verify `limit`/`tag` kwargs but none assert that `app_ctx.engine` is passed as the first positional arg. A builder could call `pick_dispatchable(limit=limit, tag=tag)` (omitting the engine) and all 4 tests would pass. Architecture review interprets "from engine" in AC1 as "from owlbear_kanban.dispatch module," so this is LAX not MISSING. #826 builder should note this risk.

**Known Forward-Break:** `test_dispatch_entries_have_task_id_and_status` and `test_task_id_is_integer` (AC3 guards) rely on `engine.list_tasks()` via inline gating. After #826 thin-wrapper, these will fail until patched per #826 AC6. Documented in builder notes and #826 research §3.3. Expected and pre-approved.

### Deductions
- Engine parameter unverified in AC1 tests (LAX, no compensating test): −0.02

### Verdict
Confidence: 0.95 → **PASS**
Action: advance to docs
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure test task — zero production code changes; builder notes confirm "no code changes" |
| 2 | Module docstrings | No | N/A | No production `.py` files created or modified; only test file added at commit 1e435518 |
| 3 | External attribution | No | N/A | Research doc notes all 4 high-relevance sources are codebase-internal (test_kanban_mcp_migration.py, test_tool_annotations_494.py, server.py, dispatch.py) |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/server-pick-tasks-thin-wrapper-tests.md` exists and linked in task body; follow-up tasks none needed per research (chain #823–#826 already decomposed) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/825-*` files found)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delegates to pick_dispatchable | 4 RED tests (TestFromAC_PickTasksDelegation) — all fail with AttributeError: server module lacks pick_dispatchable import | PASS |
| AC2: no inline gating in server.py | 3 RED tests (TestFromAC_NoInlineGating) — fail with AssertionError: _check_pick_gates, _PICK_PRIORITY_RANK, _PICK_AC_PATTERN still present | PASS |
| AC3: response format unchanged | 4 PASS regression guards (TestFromAC_PickTasksResponseFormat) — dispatch dict structure, key-set, integer task_id, empty-board | PASS |
| AC4: MCP contract preserved | 3 PASS regression guards (TestFromAC_PickTasksMCPContract) — registration, readOnlyHint, idempotentHint | PASS |
| AC5: tests fail RED before slimming | 7 RED / 7 PASS confirmed by independent run | PASS |

### Test Results
- pytest (task-scoped): 7 failed, 7 passed — exactly as designed for RED phase
- pytest (full suite, excluding 2 pre-existing collection errors): 309 failed, 4063 passed, 8 skipped — all 309 failures are pre-existing (AppContext API changes, missing lint-changed.ps1, analysis model changes, browser ctx refactor, etc.); zero failures attributable to #825
- ruff: clean (0 violations on serve/ and tests/)

### Architect Quality: 4/5
AC was specific, well-structured, and correctly categorized RED vs PASS tests. Research doc provided detailed 14-test specification with clear failure modes. Minor gap: AC1 "from engine" wording is ambiguous — could mean "from engine module" or "passing engine parameter." Reviewer identified this as LAX (engine parameter not verified in delegation tests). This is a minor upstream gap, not a blocker.

### Deduction Breakdown
- All 5 AC lines have specific evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5 (> 3): no deduction
- Reviewer evidence: detailed, PASS verdict with .95 confidence: no deduction
- Full-suite: 0 failures in #825 scope: no deduction
- Research doc was uncommitted (researcher gap) — committed as leftover: no deduction (resolved)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1e435518 | test | tests/test_server_pick_tasks_thin_wrapper_825.py | #825 |
| 730ad4dd | chore | .owlbear/research/server-pick-tasks-thin-wrapper-tests.md, .owlbear/kanban/tasks/825-*.md | #825 |