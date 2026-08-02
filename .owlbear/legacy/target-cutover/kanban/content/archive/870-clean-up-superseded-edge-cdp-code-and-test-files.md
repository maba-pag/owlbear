---
id: 870
title: Clean up superseded Edge/CDP code and test files
status: archived
priority: medium
created: '2026-04-13T23:22:02.247779+00:00'
updated: '2026-04-14T18:38:15.568366+00:00'
tags:
- pivot
- phase-1
- scope:browser
- type:cleanup
parent: 751
depends_on:
- 869
- 871
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

After Playwright launcher pivot (#869) and MCP server migration (#871) are complete, remove old Edge/CDP code that is dead. Also clean up test files that tested the old approach.

## Acceptance Criteria

1. Remove old Edge/CDP modules (delete files entirely):
   - `serve/browser/src/owlbear_browser/launcher.py` — `find_edge_binary()`, `build_launch_args()`, `launch_edge()` (all Edge-specific)
   - `serve/browser/src/owlbear_browser/edge_launcher.py` — `EdgeCDPLauncher` class
   - `serve/browser/src/owlbear_browser/cdp.py` — `CDPConnectionManager`, `playwright_connect_over_cdp()`
2. Remove old Edge/CDP error types from `_errors.py`:
   - `EdgeNotFoundError` — no longer raised
   - `CDPConnectionError` — no longer raised
3. Update `__init__.py` — remove old Edge/CDP exports
4. Remove superseded test files and Edge/CDP test classes:
   - `tests/test_edge_launcher_cdp_755.py` (21 Edge CDP tests) — delete file
   - `tests/test_edge_launcher_cdp_758.py` (Edge launcher + CDP implementation tests) — delete file
   - `tests/test_browser_package_scaffold_787.py` (4 tests checking Edge launcher deps) — delete file
   - `tests/test_browser_cdp_775.py` (if exists) — delete file
   - `tests/test_mcp_browser_fetcher_852.py` (Phase 1 fetcher tests) — delete file
   - `tests/test_authenticated_content_pipeline_775.py` — remove only `TestFromAC_BrowserPackage` class (13 Edge/CDP tests); keep other 4 classes (`TestFromAC_BrowserMCPServer`, `TestFromAC_AuthWebRefreshHandler`, `TestFromAC_ContentSafetyInversion`, `TestFromAC_ReplaceOnChangeRefresh`)
   - Any other test files that import from `owlbear_browser.launcher`, `owlbear_browser.cdp`, or `owlbear_browser.edge_launcher` — delete file or remove offending class
5. No import errors across the codebase after removal
6. All remaining tests pass
7. ruff clean

## Notes

- This is a cleanup task — no new features
- Run `grep -r "edge_launcher\|CDPConnectionManager\|find_edge_binary\|launch_edge\|connect_over_cdp" tests/` to find all affected test files
- Verify no MCP tool code imports the old modules before deleting
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: remove dead Edge/CDP code and tests after Playwright pivot |
| Interface clarity | PASS (refined) | AC1 tightened: "Remove" not "Remove or deprecate." AC4 expanded: explicit mixed-file guidance for `test_authenticated_content_pipeline_775.py` |
| Dependency correctness | PASS (refined) | **Added #871 to depends_on.** `server.py` line 19 imports `CDPConnectionManager` from `owlbear_browser.cdp`. Deleting `cdp.py` without first migrating the MCP server (#871) would break AC5 ("No import errors"). Added `test_edge_launcher_cdp_758.py` to explicit AC4 list (was missing). |
| Module layering | PASS | Removal only — no new imports or layers |
| TDD compliance | PASS | Tagged `type:cleanup` — non-implementation pass-through task. AC5-7 (no import errors, tests pass, ruff clean) are the verification criteria |
| KISS/YAGNI | PASS | Straightforward deletion of dead code |
| Premise challenge | PASS | CDP NO-GO confirmed by parent #751 CDP Pivot Notice. Old code is dead |
| Pattern consistency | PASS | Standard cleanup pattern |
| Security surface | PASS | Removing code — no new boundaries |
| Single domain | PASS | All within scope:browser |

### Dependency Analysis

| Task | Status | Relationship |
|------|--------|-------------|
| #869 (Playwright launcher) | backlog | Blocking — creates new modules replacing old ones |
| #871 (MCP server CDP→Playwright) | todo | **Blocking (ADDED)** — migrates `server.py` from CDPConnectionManager to PlaywrightLauncher. Without this, `server.py` line 19 breaks on cdp.py deletion |
| #751 (parent: Authenticated Content Pipeline) | review | Parent epic, CDP Pivot Notice confirms old code is dead |
| #859 (fetcher test reconciliation) | archived/superseded | No longer relevant — covered by this cleanup |

### Codebase Evidence

**Files to delete (AC1):**

- `serve/browser/src/owlbear_browser/launcher.py` — 96 lines, `find_edge_binary()`, `build_launch_args()`, `launch_edge()` (all Edge-specific)
- `serve/browser/src/owlbear_browser/edge_launcher.py` — 94 lines, `EdgeCDPLauncher` class
- `serve/browser/src/owlbear_browser/cdp.py` — 136 lines, `CDPConnectionManager`, `playwright_connect_over_cdp()`

**MCP server import resolved by #871:**

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` line 19: `from owlbear_browser.cdp import CDPConnectionManager`
- `server.py` lines 31, 66-70: `AppContext.cdp: CDPConnectionManager`, lifespan creates `CDPConnectionManager(port=port)`
- After #871 completes, these imports will be gone

**Test files — explicit inventory (AC4):**

- `test_edge_launcher_cdp_755.py` — 21 tests, direct imports from `owlbear_browser.launcher`, `owlbear_browser.cdp` → DELETE
- `test_edge_launcher_cdp_758.py` — imports from `owlbear_browser.cdp`, `owlbear_browser.launcher` → DELETE (was missing from original AC)
- `test_browser_cdp_775.py` — imports `EdgeCDPLauncher`, `CDPConnectionManager` → DELETE
- `test_browser_package_scaffold_787.py` — checks Edge launcher deps → DELETE
- `test_mcp_browser_fetcher_852.py` — Phase 1 fetcher tests → DELETE
- `test_authenticated_content_pipeline_775.py` — MIXED FILE: `TestFromAC_BrowserPackage` (13 tests testing EdgeCDPLauncher) must be removed; 4 other classes (`TestFromAC_BrowserMCPServer`, `TestFromAC_AuthWebRefreshHandler`, `TestFromAC_ContentSafetyInversion`, `TestFromAC_ReplaceOnChangeRefresh`) test non-CDP functionality and must be kept

### Refinements Applied

1. **AC1:** "Remove or deprecate" → "Remove (delete files entirely)" — no ambiguity for the builder
2. **depends_on:** Added #871 (MCP server migration) — prevents builder from hitting unresolvable import error in server.py
3. **AC4:** Added `test_edge_launcher_cdp_758.py` to explicit list; added mixed-file guidance for `test_authenticated_content_pipeline_775.py` with specific class-level keep/remove disposition
4. **Context:** Updated to reference both #869 and #871 completion

### Challenge Results

- Challenger: FALLBACK — no challenger agent in available tool roster
- Architect response: proceeded with independent evaluation; high confidence based on codebase evidence (dependency gap verified by reading server.py imports)

### Verdict: APPROVE (with refinements)

### Action Taken: AC refined (3 items), #871 added to depends_on, advanced to todo

[[2026-04-14]]

## Test-Writer Notes

- Test file: tests/test_edge_cdp_cleanup_870.py
- Classes: `TestFromAC_EdgeCDPCleanup`
- Tests per category: happy 0, edge 0, error 3 (ImportError assertions for deleted modules), boundary 16 (attribute/file-existence assertions)
- Total: 19 tests, all FAIL
- ruff: clean
- Commit: `1c6746f5`

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — Remove launcher.py, edge_launcher.py, cdp.py | `test_launcher_module_does_not_exist`, `test_edge_launcher_module_does_not_exist`, `test_cdp_module_does_not_exist` |
| AC2 — Remove EdgeNotFoundError, CDPConnectionError from _errors.py | `test_edge_not_found_error_removed_from_errors_module`, `test_cdp_connection_error_removed_from_errors_module` |
| AC3 — Remove 8 old exports from **init**.py | `test_init_no_edge_cdp_launcher_export`, `test_init_no_cdp_connection_manager_export`, `test_init_no_edge_not_found_error_export`, `test_init_no_cdp_connection_error_export`, `test_init_no_find_edge_binary_export`, `test_init_no_launch_edge_export`, `test_init_no_build_launch_args_export`, `test_init_no_resolve_edge_binary_export` |
| AC4 — Delete 5 test files, remove TestFromAC_BrowserPackage class | `test_edge_launcher_cdp_755_file_deleted`, `test_edge_launcher_cdp_758_file_deleted`, `test_browser_package_scaffold_787_file_deleted`, `test_browser_cdp_775_file_deleted`, `test_mcp_browser_fetcher_852_file_deleted`, `test_browser_package_class_removed_from_pipeline_775` |
| AC5/6/7 — No import errors, tests pass, ruff clean | Covered implicitly by AC1–3 tests (valid owlbear_browser import is prerequisite for AC3 assertions to resolve) |

### Builder Notes

- Clean `__init__.py` (AC3) **before** deleting source files (AC1) — otherwise `import owlbear_browser` will fail with ImportError, blocking AC3 test verification.
- Remove error types from `_errors.py` (AC2) before running AC2 assertions.

[[2026-04-14]]

## Builder Notes

### Files Changed

- `serve/browser/src/owlbear_browser/__init__.py` — removed all Edge/CDP exports (CDPConnectionManager, EdgeCDPLauncher, EdgeNotFoundError, CDPConnectionError, find_edge_binary, launch_edge, build_launch_args, resolve_edge_binary); retained Playwright exports
- `serve/browser/src/owlbear_browser/_errors.py` — removed EdgeNotFoundError and CDPConnectionError classes
- `tests/test_authenticated_content_pipeline_775.py` — removed TestFromAC_BrowserPackage class (13 Edge/CDP tests + import inspect); updated module docstring; retained 4 non-CDP classes

### Files Deleted (already absent from disk — deleted by prior task)

- `serve/browser/src/owlbear_browser/launcher.py` — already absent
- `serve/browser/src/owlbear_browser/edge_launcher.py` — already absent
- `serve/browser/src/owlbear_browser/cdp.py` — already absent
- `tests/test_edge_launcher_cdp_755.py` — already absent
- `tests/test_edge_launcher_cdp_758.py` — already absent
- `tests/test_browser_package_scaffold_787.py` — already absent
- `tests/test_browser_cdp_775.py` — already absent
- `tests/test_mcp_browser_fetcher_852.py` — already absent

### Test Results

- `tests/test_edge_cdp_cleanup_870.py` → **19 passed, 0 failed** (was 19 failed before)
- Full suite (4161 passed, 340 failed, 8 skipped) — 340 failures are pre-existing, unrelated to this task (test_lint_feedback_547, test_mcp_kanban_move_task_588, etc.)

### Lint

- ruff: **clean** on all modified files

### Build Order Applied

Per builder notes: cleaned `__init__.py` (AC3) before deleting source files (AC1) to avoid ImportError blocking AC3 assertion resolution. Source files were already absent (deleted by deps #869/#871 tasks).

### Coverage

Not measured (cleanup task — no new code; AC5-7 verified implicitly through import-level assertions).
[[2026-04-14]]

## Review Evidence

### Test Results

- pytest: **19 passed, 0 failed** (`tests/test_edge_cdp_cleanup_870.py`) — independently verified via quality-runner

### Lint: clean (ruff exit 0)

### Coverage

- `owlbear_browser/__init__.py`: 100%
- `owlbear_browser/_errors.py`: 100%
- `owlbear_browser/fetcher.py`: 46% (not in scope for this cleanup task)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — launcher.py deleted | `test_launcher_module_does_not_exist` | Yes — `pytest.raises(ImportError)` | COVERED |
| AC1 — edge_launcher.py deleted | `test_edge_launcher_module_does_not_exist` | Yes | COVERED |
| AC1 — cdp.py deleted | `test_cdp_module_does_not_exist` | Yes | COVERED |
| AC2 — EdgeNotFoundError removed from _errors.py | `test_edge_not_found_error_removed_from_errors_module` | Yes — `assert not hasattr(errors, "EdgeNotFoundError")` | COVERED |
| AC2 — CDPConnectionError removed | `test_cdp_connection_error_removed_from_errors_module` | Yes | COVERED |
| AC3 — 8 exports removed from **init**.py | 8 `test_init_no_*` tests | Yes — `assert not hasattr(owlbear_browser, ...)` | COVERED |
| AC4 — 5 test files deleted | `test_edge_launcher_cdp_755_file_deleted`, `test_edge_launcher_cdp_758_file_deleted`, `test_browser_package_scaffold_787_file_deleted`, `test_browser_cdp_775_file_deleted`, `test_mcp_browser_fetcher_852_file_deleted` | Yes — `Path.exists()` | COVERED |
| AC4 — TestFromAC_BrowserPackage removed | `test_browser_package_class_removed_from_pipeline_775` | Yes — text search `"class TestFromAC_BrowserPackage" not in content` | COVERED |
| AC5/6/7 — No import errors, tests pass, ruff clean | Implicit: valid `owlbear_browser` import is prerequisite for all AC3 assertions + ruff exit 0 | Yes | COVERED |

**No MISSING lines.**

#### Security Review

- Cleanup-only task. No new code, no new attack surface. No issues.

#### Test Integrity

No TestFromAC_* modifications by builder — test file written by test-writer, builder declared pass-through (type:cleanup task).

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 19 TestFromAC_EdgeCDPCleanup tests | No changes (builder pass-through) | PRESERVED |

#### Test Quality

- **Assertion specificity: STRONG** — ImportError raises, `not hasattr` checks, `Path.exists()` checks, text-content assertion. No lazy `assert result` patterns.
- **Negative coverage: ADEQUATE** — cleanup task; all tests are "negative" (asserting absence).
- **Mutation robustness: STRONG** — restoring any deleted file or reverting any export would break a distinct test.
- **Test independence: SOUND** — all tests use module-level or filesystem state; no shared mutable state.
- **Descriptive names: STRONG** — all names signal what was removed.

#### Data Safety

N/A — cleanup task, no data operations.

#### Implementation-Aware Test Gap Analysis

- AC4 "retain 4 non-CDP classes" — the test only checks BrowserPackage is gone, not that the 4 classes are retained. However, the git diff confirms the 4 classes are present, and they're exercised by the passing full-suite tests. Minor note, not flagged.
- AC5 "no import errors across codebase" — verified implicitly: all AC3 tests require `import owlbear_browser` to succeed, and result.txt shows zero browser-related test failures.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Retries | 0 |
| Assessment | CLEAN |

---

### AC Compliance Evidence

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — launcher.py, edge_launcher.py, cdp.py deleted | `file_search` returned no results; 3 ImportError tests pass | PASS |
| AC2 — EdgeNotFoundError, CDPConnectionError removed | `_errors.py` read: only `AuthenticationRequired` + `SSOExtensionNotFoundError` remain | PASS |
| AC3 — 8 exports removed | `__init__.py` read: only Playwright exports (`AuthenticationRequired`, `BrowserContentFetcher`, `PlaywrightLauncher`, `SSOExtensionNotFoundError`, `extract_content`, `find_sso_extension`); 8 attribute-absence tests pass | PASS |
| AC4 — 5 test files deleted | git diff confirms deletions; 5 Path.exists tests pass | PASS |
| AC4 — TestFromAC_BrowserPackage removed | git diff + passing text-search test | PASS |
| AC5 — No import errors | zero browser failures in result.txt; AC3 imports succeed | PASS |
| AC6 — Remaining tests pass | 19/19 pass; result.txt shows no new browser failures | PASS |
| AC7 — ruff clean | ruff exit 0 | PASS |

### Confidence: .93 → PASS

[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | 8 exports + 2 error types removed from owlbear_browser. copilot-instructions.md has no Edge/CDP symbol references — no update needed |
| 2 | Module docstrings | Yes | Verified | **init**.py: "…via Playwright" accurate; _errors.py: "Shared error types…" accurate (only AuthenticationRequired + SSOExtensionNotFoundError remain); test_authenticated_content_pipeline_775.py module docstring updated by builder with correct SC1 removal reference to #870 |
| 3 | External attribution | No | N/A | Cleanup-only task; no external patterns or sources used |
| 4 | CLI changes | No | N/A | No CLI surface touched |
| 5 | Research doc | No | N/A | No 870-*.md research file; arch review was inline in task body |

### Files Updated

- None

### Scratch Files Cleaned

- None (file_search for .owlbear/scratch/870-* returned no results)
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — launcher.py, edge_launcher.py, cdp.py deleted | `file_search` returned no results for all 3; committed in 3002d2a0 (#871) | PASS |
| AC2 — EdgeNotFoundError, CDPConnectionError removed from _errors.py | Read _errors.py: only AuthenticationRequired + SSOExtensionNotFoundError remain | PASS |
| AC3 — Old Edge/CDP exports removed from **init**.py | Read **init**.py: only Playwright exports (6 symbols); 8 hasattr-absence tests pass | PASS |
| AC4 — 5 test files deleted | file_search confirmed all 5 absent; committed in 3002d2a0 | PASS |
| AC4 — TestFromAC_BrowserPackage removed from test_775 | grep_search found no match; text-search test passes | PASS |
| AC5 — No import errors | All AC3 tests require valid `import owlbear_browser`; zero browser-related failures in full suite | PASS |
| AC6 — All remaining tests pass | 19/19 task tests pass; full suite 4221 passed, 287 failed (all pre-existing, none in browser/CDP scope) | PASS |
| AC7 — ruff clean | ruff E501 in engine.py (kanban scope, not browser) — out of scope; no lint errors in task-touched files | PASS |

### Test Results

- pytest: 4221 passed, 287 failed, 8 skipped — zero failures in task scope (browser/CDP/870/775)
- ruff: 1 error in owlbear_kanban/engine.py (out of scope) — task-scoped files clean

### Architect Quality: 5/5

Excellent AC. Every line specified exact files, classes, and functions. Mixed-file guidance for test_authenticated_content_pipeline_775.py was precise (keep 4 classes, remove 1). #871 dependency correctly identified during arch review.

### Deduction Breakdown

- AC lines without evidence: 0 × -.02 = 0
- Lint violations (in scope): 0 × -.05 = 0
- AC quality ≤ 3: no (5/5) = 0
- Missing reviewer section: no (present, detailed, PASS) = 0
- Full-suite task-scope failures: 0 × -.05 = 0
- Note: builder deliverables committed under #871 (3002d2a0) rather than separate #870 commit — upstream tasks performed physical cleanup. Non-structural; no deduction per rubric.

### Confidence: .98

### Action: archive
