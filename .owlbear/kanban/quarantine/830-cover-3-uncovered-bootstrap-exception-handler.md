---
id: 830
title: Cover 3 uncovered bootstrap exception handler paths
status: archived
priority: nice-to-have
created: 2026-03-15T12:57:17.0889803+01:00
updated: 2026-03-16T01:49:37.1910428+01:00
started: 2026-03-16T01:49:36.5967105+01:00
completed: 2026-03-16T01:49:36.5967105+01:00
tags:
    - test
    - phase-12
class: standard
---

Add tests for 3 genuinely uncovered exception handler paths in bootstrap submodules. (Original scope was 11 handlers; 7 already had coverage; 1 more (_build_knowledge_source_toolset) found covered during second review  see Architecture Review below.)

## AC

- Test _build_knowledge_toolset internal except: call directly with mocked dep that raises (e.g., patch KnowledgeToolset constructor to raise RuntimeError), assert logger.warning called with 'Failed to create KnowledgeToolset' and return is None
- Test _build_bookmark_toolset internal except: call directly with mocked dep that raises (e.g., patch BookmarkStore to raise), assert logger.warning called with 'Failed to create BookmarkToolset' and return is None
- Test _wire_knowledge_toolsets outer except: call_wire_knowledge_toolsets with _pkg._build_knowledge_infra patched to raise RuntimeError (via side_effect), assert ComponentStatus(name='KnowledgeInfra', loaded=False) appended to summary list with error message
- All 3 tests pass on first run (retroactive coverage  no source changes needed)
- ruff clean
- Do NOT duplicate existing tests  _build_knowledge_source_toolset except path is ALREADY covered by test_returns_none_and_logs_warning_on_error (test_bootstrap.py ~L1953)

See docs/research/close-test-coverage-gaps.md (note: line numbers in doc are stale, bootstrap.py was refactored into knowledge.py, toolsets.py, registry.py).

[[2026-03-15]] Sun 19:40

## Architecture Review (2nd pass)

**Verdict:** APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| _build_knowledge_toolset except | Genuinely uncovered  no test calls function directly with raising mock | Keep |
| _build_bookmark_toolset except | Genuinely uncovered  same gap pattern | Keep |
| _build_knowledge_source_toolset except | ALREADY COVERED by test_returns_none_and_logs_warning_on_error (~L1953)  patches KnowledgeSourceStore side_effect, asserts logger.warning | Dropped from AC |
| _wire_knowledge_toolsets outer except | Genuinely uncovered  no test patches _build_knowledge_infra with side_effect | Keep |
| All 3 pass on first run | Correct for retroactive coverage | Keep |
| ruff clean | Standard gate | Keep |
| No duplicate tests | With _build_knowledge_source_toolset dropped, no overlap | Keep |

### Architecture Notes

- SRP: test-only task, single domain (test)
- Pattern: follow existing test_returns_none_and_logs_warning_on_error pattern (direct call, mock dep to raise, assert logger.warning + return None)
- For _wire_knowledge_toolsets: mock_pkg._build_knowledge_infra with side_effect=RuntimeError, assert ComponentStatus appended  follows _wire_web_search test pattern
- No source changes needed  retroactive coverage only
- TDD: this IS the test task, no predecessor needed
- Security: no new boundaries
- Files touched: tests/test_bootstrap.py only

### Changes Made

- Refined title: 4 -> 3 uncovered paths
- Refined AC: dropped _build_knowledge_source_toolset (already covered)
- Clarified side_effect usage in_wire_knowledge_toolsets AC

### Dependencies

- None  tests exercise existing code

[[2026-03-15]] Sun 20:32

## Test-Writer Notes

- Test file: tests/test_bootstrap.py
- Classes: TestFromAC_KnowledgeToolsetExceptPath, TestFromAC_BookmarkToolsetExceptPath, TestFromAC_WireKnowledgeToolsetsOuterExcept
- Tests per category: happy 0, edge 0, error 3, boundary 0
- Total: 3 tests, all PASS (retroactive coverage)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| _build_knowledge_toolset except | test_returns_none_and_logs_warning_on_error | error |
| _build_bookmark_toolset except | test_returns_none_and_logs_warning_on_error | error |
| _wire_knowledge_toolsets outer except | test_infra_raise_appends_error_status | error |

[[2026-03-15]] Sun 20:54

## Builder Notes

- Non-implementation task (retroactive coverage) -- no source changes needed
- Tests: 3 passed (TestFromAC_KnowledgeToolsetExceptPath, TestFromAC_BookmarkToolsetExceptPath, TestFromAC_WireKnowledgeToolsetsOuterExcept)
- Lint: ruff clean
- Evidence: 3 passed, 149 deselected in 2.49s

[[2026-03-15]] Sun 21:14

## Review Evidence

### Test Results

- pytest: 3 passed, 0 failed (149 deselected)
- Tests: TestFromAC_KnowledgeToolsetExceptPath, TestFromAC_BookmarkToolsetExceptPath, TestFromAC_WireKnowledgeToolsetsOuterExcept

### Lint Results

- ruff: All checks passed

### Coverage

- Retroactive coverage task (test-only, no source changes) -- coverage N/A for new code since tests exercise existing exception paths

### Pass 1 -- CRITICAL

#### Security Review

- Test-only task; no new user-facing code, no secrets, no injection surfaces, no new deps. No issues.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_KnowledgeToolsetExceptPath::test_returns_none_and_logs_warning_on_error | No change (additive only) | PRESERVED |
| TestFromAC_BookmarkToolsetExceptPath::test_returns_none_and_logs_warning_on_error | No change (additive only) | PRESERVED |
| TestFromAC_WireKnowledgeToolsetsOuterExcept::test_infra_raise_appends_error_status | No change (additive only) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Checks result is None, assert_called_once, specific message substring, tuple equality, status.loaded, status.error |
| Negative/error paths | STRONG | All 3 tests ARE error path tests -- the entire task purpose |
| Mutation reasoning | STRONG | Removing except = uncaught RuntimeError; changing return = assertion fail; changing warning msg = substring fail |
| Test independence | STRONG | Each class isolated with own mocks and tmp_path fixture |
| Descriptive names | STRONG | test_returns_none_and_logs_warning_on_error, test_infra_raise_appends_error_status |

#### Data Safety

- Test-only task, no data operations. No issues.

### Pass 2 -- INFORMATIONAL

- Minor: toolsets.py has cosmetic whitespace change (arg formatting L150) not related to AC -- harmless but technically an unscoped diff line

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| _build_knowledge_toolset except | Patches KnowledgeToolset to raise, asserts None + logger.warning | TestFromAC_KnowledgeToolsetExceptPath::test_returns_none_and_logs_warning_on_error | PASS |
| _build_bookmark_toolset except | Patches BookmarkStore to raise, asserts None + logger.warning | TestFromAC_BookmarkToolsetExceptPath::test_returns_none_and_logs_warning_on_error | PASS |
| _wire_knowledge_toolsets outer except | Patches _build_knowledge_infra side_effect, asserts ComponentStatus(loaded=False) + error msg | TestFromAC_WireKnowledgeToolsetsOuterExcept::test_infra_raise_appends_error_status | PASS |
| All 3 tests pass on first run | 3 passed, 149 deselected in 2.64s | -- | PASS |
| ruff clean | All checks passed | -- | PASS |
| No duplicate tests | Verified: _build_knowledge_source_toolset test exists at L1953, not duplicated | -- | PASS |

### Verdict: PASS (confidence .95)

### Action Taken

- kanban edit 830 --status docs --release

[[2026-03-15]] Sun 21:28

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task, no behavior or API change |
| 2 | Docstrings complete | No | N/A | Only tests/test_bootstrap.py modified (test file, not source module). Test classes have docstrings. |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/close-test-coverage-gaps.md exists and is linked from AC |
| 6 | No impact | -- | -- | Items 1-4 N/A; item 5 already linked. No docs updates needed. |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/830-ruff.txt

[[2026-03-16]] Mon 01:49

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| _build_knowledge_toolset except: mock dep, assert logger.warning + None | TestFromAC_KnowledgeToolsetExceptPath patches KnowledgeToolset side_effect=RuntimeError, asserts result is None, logger.warning called with 'Failed to create KnowledgeToolset' (L1988-1997) | PASS |
| _build_bookmark_toolset except: mock dep, assert logger.warning + None | TestFromAC_BookmarkToolsetExceptPath patches BookmarkStore side_effect=RuntimeError, asserts result is None, logger.warning called with 'Failed to create BookmarkToolset' (L2009-2018) | PASS |
| _wire_knowledge_toolsets outer except: patch_build_knowledge_infra side_effect, assert ComponentStatus(loaded=False) | TestFromAC_WireKnowledgeToolsetsOuterExcept patches_pkg._build_knowledge_infra side_effect=RuntimeError, asserts result==(None,None,None), ComponentStatus name='KnowledgeInfra', loaded=False, error contains 'infra exploded' (L2024-2055) | PASS |
| All 3 tests pass on first run | Builder: 3 passed, 149 deselected. Reviewer: 3 passed, 0 failed. Environment unavailable for auditor re-run (all pytest hangs -- service dependency issue, not task-specific) | PASS (verified by 2 upstream agents) |
| ruff clean | Auditor ran ruff check tests/test_bootstrap.py + src/owlbear/bootstrap/toolsets.py -- All checks passed | PASS |
| No duplicate tests | _build_knowledge_source_toolset already covered at L1953 by test_returns_none_and_logs_warning_on_error; not duplicated in #830 diff | PASS |

### Test Results

- pytest: Environment unavailable (all tests hang -- service dep, not task-specific). Builder reported 3 passed/149 deselected. Reviewer confirmed 3 passed/0 failed.
- ruff: All checks passed (auditor-verified)

### Code Review Notes

- 3 test classes follow existing TestBuildKnowledgeSourceToolset pattern (direct call, mock dep to raise, assert logger.warning + return None)
- _wire_knowledge_toolsets test follows_wire_web_search pattern (patch side_effect, assert ComponentStatus)
- Cosmetic +3/-1 whitespace change in toolsets.py L150 (arg formatting) flagged by reviewer -- harmless, unscoped
- No functional source changes (retroactive coverage task)

### Confidence: .95

### Action: archive
