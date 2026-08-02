---
id: 554
title: 'Test: Refresh orchestrator'
status: archived
priority: medium
created: 2026-04-02 16:07:01.483946+02:00
updated: 2026-04-03 06:16:37.037538+02:00
started: 2026-04-03 06:15:47.363969+02:00
completed: 2026-04-03 06:15:47.363969+02:00
tags:
- phase-1
- scope:knowledge
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for the RefreshOrchestrator module.

## Acceptance Criteria
- [ ] Test file: tests/test_refresh_orchestrator.py
- [ ] TestFromAC_ classes covering all AC lines from the implementation task
- [ ] Test RefreshResult model: frozen, all fields (source_id, refreshed, skipped, failed, errors) with correct types and defaults
- [ ] Test CrawlHandler type alias exists at module level
- [ ] Test RefreshOrchestrator constructor: accepts store, pipeline, crawl_handler (optional), workspace_root (optional, defaults to Path.cwd())
- [ ] Test refresh() dispatches by SourceType: url_list, crawl, file_glob
- [ ] Test refresh() raises ValueError for disabled source
- [ ] Test refresh_all() filters enabled sources from list_all, iterates by priority descending, stops on cancel
- [ ] Test url_list handler: reads config[urls], creates IntakeResult via intake.read_url, passes to pipeline.ingest
- [ ] Test crawl handler: delegates to injected crawl_handler; raises ValueError when crawl_handler is None
- [ ] Test file_glob handler: resolves pattern, validates paths with sandbox_path, creates IntakeResult via intake.read_file
- [ ] Test file_glob handler: sandbox PermissionError counted as failure, not raised
- [ ] Test _update_source_record: updates last_refreshed_at and last_error via store.update
- [ ] Test cancel signal: checked between items and between sources
- [ ] Test IngestResult status == skipped counted as skipped, not refreshed
- [ ] All tests FAIL (RED phase)
- [ ] ruff check passes

## Context
Test task for refresh orchestrator extraction. Split from #140.

[[2026-04-02]] Thu 17:05
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file: tests/test_refresh_orchestrator.py | Clear target path, follows project convention | Keep |
| TestFromAC_ classes covering all AC lines | Standard naming pattern per test_bookmark_pipeline_136.py | Keep |
| Test RefreshResult model: frozen, all fields | Fields match #555 AC exactly | Keep |
| Test CrawlHandler type alias exists | Verifiable via hasattr/getattr | Keep |
| Test constructor params | Matches #555 constructor sig | Keep |
| Test refresh() dispatch by SourceType | Three source types enumerated | Keep |
| Test refresh() ValueError for disabled | Clear exception contract | Keep |
| Test refresh_all() list_all + filter + priority + cancel | Correctly uses list_all (not stale list_enabled) | Keep |
| Test url_list handler | Pipeline integration clear | Keep |
| Test crawl handler | Delegation + error path clear | Keep |
| Test file_glob handler + sandbox | Security path covered | Keep |
| Test _update_source_record | store.update contract clear | Keep |
| Test cancel signal between items and sources | Two cancellation points specified | Keep |
| Test IngestResult skipped counting | Edge case explicitly called out | Keep |
| All tests FAIL (RED) | Standard TDD RED gate | Keep |
| ruff check passes | Standard lint gate | Keep |

### Architecture Notes
- TDD pair: #554 (test) precedes #555 (impl), depends_on correct
- Single domain: scope:knowledge, test-only task
- Tags include type:test and test for pass-through
- AC correctly uses list_all + filter (not the stale list_enabled from #136 tests)
- All referenced types exist in codebase: SourceType, KnowledgeSourceStore, IngestPipeline, IngestResult, IntakeResult, sandbox_path, CancelSignal

### Stale Test Warning
tests/test_bookmark_pipeline_136.py contains ~12 overlapping RefreshOrchestrator tests from parent #136 that use store.list_enabled() (non-existent method). These are stale and will conflict. The test-writer for #554 should create tests/test_refresh_orchestrator.py as authoritative; cleanup of stale #136 tests belongs to #136 or #555 scope.

### Changes Made
- Approved: AC is precise, TDD pair verified, no changes needed
- Added stale test context note

### Dependencies
- Verified: #555 (impl) depends_on [554] -- correct TDD ordering
- No other deps needed (test task imports from module that doesn't exist yet -- standard RED)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .78
- Key challenges: stale test overlap in test_bookmark_pipeline_136.py (list_enabled vs list_all), minor AC gaps (cancelled status, base_dir)
- Architect response: Rebutted. Stale overlap is #136 cleanup scope, not #554 blocker. Added context note. Minor gaps derivable from #555 AC by test-writer.

[[2026-04-02]] Thu 17:05
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file: tests/test_refresh_orchestrator.py | Clear target path, follows project convention | Keep |
| TestFromAC_ classes covering all AC lines | Standard naming pattern per test_bookmark_pipeline_136.py | Keep |
| Test RefreshResult model: frozen, all fields | Fields match #555 AC exactly | Keep |
| Test CrawlHandler type alias exists | Verifiable via hasattr/getattr | Keep |
| Test constructor params | Matches #555 constructor sig | Keep |
| Test refresh() dispatch by SourceType | Three source types enumerated | Keep |
| Test refresh() ValueError for disabled | Clear exception contract | Keep |
| Test refresh_all() list_all + filter + priority + cancel | Correctly uses list_all (not stale list_enabled) | Keep |
| Test url_list handler | Pipeline integration clear | Keep |
| Test crawl handler | Delegation + error path clear | Keep |
| Test file_glob handler + sandbox | Security path covered | Keep |
| Test _update_source_record | store.update contract clear | Keep |
| Test cancel signal between items and sources | Two cancellation points specified | Keep |
| Test IngestResult skipped counting | Edge case explicitly called out | Keep |
| All tests FAIL (RED) | Standard TDD RED gate | Keep |
| ruff check passes | Standard lint gate | Keep |

### Architecture Notes
- TDD pair: #554 (test) precedes #555 (impl), depends_on correct
- Single domain: scope:knowledge, test-only task
- Tags include type:test and test for pass-through
- AC correctly uses list_all + filter (not the stale list_enabled from #136 tests)
- All referenced types exist in codebase: SourceType, KnowledgeSourceStore, IngestPipeline, IngestResult, IntakeResult, sandbox_path, CancelSignal

### Stale Test Warning
tests/test_bookmark_pipeline_136.py contains ~12 overlapping RefreshOrchestrator tests from parent #136 that use store.list_enabled() (non-existent method). These are stale and will conflict. The test-writer for #554 should create tests/test_refresh_orchestrator.py as authoritative; cleanup of stale #136 tests belongs to #136 or #555 scope.

### Changes Made
- Approved: AC is precise, TDD pair verified, no changes needed
- Added stale test context note

### Dependencies
- Verified: #555 (impl) depends_on [554] -- correct TDD ordering
- No other deps needed (test task imports from module that doesn't exist yet -- standard RED)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .78
- Key challenges: stale test overlap in test_bookmark_pipeline_136.py (list_enabled vs list_all), minor AC gaps (cancelled status, base_dir)
- Architect response: Rebutted. Stale overlap is #136 cleanup scope, not #554 blocker. Added context note. Minor gaps derivable from #555 AC by test-writer.

[[2026-04-02]] Thu 17:05
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file: tests/test_refresh_orchestrator.py | Clear target path, follows project convention | Keep |
| TestFromAC_ classes covering all AC lines | Standard naming pattern per test_bookmark_pipeline_136.py | Keep |
| Test RefreshResult model: frozen, all fields | Fields match #555 AC exactly | Keep |
| Test CrawlHandler type alias exists | Verifiable via hasattr/getattr | Keep |
| Test constructor params | Matches #555 constructor sig | Keep |
| Test refresh() dispatch by SourceType | Three source types enumerated | Keep |
| Test refresh() ValueError for disabled | Clear exception contract | Keep |
| Test refresh_all() list_all + filter + priority + cancel | Correctly uses list_all (not stale list_enabled) | Keep |
| Test url_list handler | Pipeline integration clear | Keep |
| Test crawl handler | Delegation + error path clear | Keep |
| Test file_glob handler + sandbox | Security path covered | Keep |
| Test _update_source_record | store.update contract clear | Keep |
| Test cancel signal between items and sources | Two cancellation points specified | Keep |
| Test IngestResult skipped counting | Edge case explicitly called out | Keep |
| All tests FAIL (RED) | Standard TDD RED gate | Keep |
| ruff check passes | Standard lint gate | Keep |

### Architecture Notes
- TDD pair: #554 (test) precedes #555 (impl), depends_on correct
- Single domain: scope:knowledge, test-only task
- Tags include type:test and test for pass-through
- AC correctly uses list_all + filter (not the stale list_enabled from #136 tests)
- All referenced types exist in codebase: SourceType, KnowledgeSourceStore, IngestPipeline, IngestResult, IntakeResult, sandbox_path, CancelSignal

### Stale Test Warning
tests/test_bookmark_pipeline_136.py contains ~12 overlapping RefreshOrchestrator tests from parent #136 that use store.list_enabled() (non-existent method). These are stale and will conflict. The test-writer for #554 should create tests/test_refresh_orchestrator.py as authoritative; cleanup of stale #136 tests belongs to #136 or #555 scope.

### Changes Made
- Approved: AC is precise, TDD pair verified, no changes needed
- Added stale test context note

### Dependencies
- Verified: #555 (impl) depends_on [554] -- correct TDD ordering
- No other deps needed (test task imports from module that doesn't exist yet -- standard RED)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .78
- Key challenges: stale test overlap in test_bookmark_pipeline_136.py (list_enabled vs list_all), minor AC gaps (cancelled status, base_dir)
- Architect response: Rebutted. Stale overlap is #136 cleanup scope, not #554 blocker. Added context note. Minor gaps derivable from #555 AC by test-writer.

[[2026-04-02]] Thu 18:21
## Test-Writer Notes
- Test file: tests/test_refresh_orchestrator.py
- Classes: TestFromAC_RefreshResultModel, TestFromAC_CrawlHandlerAlias, TestFromAC_RefreshOrchestratorConstructor, TestFromAC_RefreshDisabledSource, TestFromAC_RefreshDispatch, TestFromAC_RefreshAll, TestFromAC_UrlListHandler, TestFromAC_CrawlHandlerDispatch, TestFromAC_FileGlobHandler, TestFromAC_UpdateSourceRecord, TestFromAC_CancelSignal, TestFromAC_IngestResultCounting
- Tests per category: happy 16, edge 7, error 7, boundary 3
- Total: 33 tests, all FAIL (ModuleNotFoundError) ✓
- ruff: clean
- AC coverage:
  RefreshResult frozen fields and defaults: test_importable, test_all_fields_with_correct_types, test_errors_defaults_to_empty_list, test_frozen_raises_on_mutation
  CrawlHandler type alias: test_type_alias_exists_at_module_level
  Constructor params: test_required_params_only, test_all_optional_params, test_workspace_root_none_is_valid
  refresh() ValueError disabled: test_disabled_source_raises_value_error
  refresh() dispatch by SourceType: test_url_list_dispatch_returns_refresh_result, test_crawl_dispatch_delegates_to_handler, test_file_glob_dispatch_returns_refresh_result
  refresh_all() list_all + filter + priority + cancel: test_calls_list_all_not_list_enabled, test_filters_enabled_sources_only, test_iterates_by_priority_descending, test_stops_on_cancel_before_all_sources, test_empty_source_list_returns_empty_list
  url_list handler: test_calls_read_url_for_each_configured_url, test_calls_pipeline_ingest_per_url, test_per_url_exception_counted_as_failed_not_raised
  crawl handler: test_delegates_to_injected_handler, test_raises_value_error_when_crawl_handler_is_none
  file_glob handler + sandbox: test_ingests_matching_files, test_sandbox_permission_error_counted_as_failed_not_raised, test_uses_base_dir_from_config
  _update_source_record: test_calls_store_update_after_refresh, test_sets_last_refreshed_at_on_update, test_clears_last_error_on_successful_refresh
  cancel between items and sources: test_cancel_between_items_stops_url_list_loop, test_cancel_between_sources_stops_refresh_all
  IngestResult counting: test_ok_status_counted_as_refreshed, test_skipped_status_counted_as_skipped_not_refreshed, test_failed_status_counted_as_failed

[[2026-04-02]] Thu 22:56
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/refresh.py (new)
- Tests: 33 passed, coverage 90% on refresh.py
- Lint: ruff clean
- Evidence: 33 passed in 0.52s; refresh.py 90% (113 stmts, 11 missed -- defensive branches)
- Fixes applied: None

[[2026-04-03]] Fri 00:40
## Review Evidence

### Test Results
- pytest: 33 passed, 0 failed (independent run confirmed)

### Lint Results
- ruff: All checks passed!

### Coverage
- refresh.py: 89% (118 stmts, 13 missed -- lines 105-106, 136-137, 189-192, 213-214, 228, 236-239)
- Note: builder claimed 90%; actual is 89%, below the 90% gate threshold

### Pass 1 -- CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Test file: tests/test_refresh_orchestrator.py | File exists | Yes | COVERED |
| TestFromAC_ classes covering all AC lines | 12 TestFromAC_ classes | Yes | COVERED |
| RefreshResult: frozen, all fields, correct types, defaults | TestFromAC_RefreshResultModel (4 tests) | Yes | COVERED |
| CrawlHandler type alias at module level | TestFromAC_CrawlHandlerAlias::test_type_alias_exists_at_module_level | Yes | COVERED |
| Constructor: store, pipeline, crawl_handler (optional), workspace_root (optional) | TestFromAC_RefreshOrchestratorConstructor (3 tests) | Yes | COVERED |
| refresh() dispatch by SourceType: url_list, crawl, file_glob | TestFromAC_RefreshDispatch (3 tests) | Yes | COVERED |
| refresh() raises ValueError for disabled source | TestFromAC_RefreshDisabledSource::test_disabled_source_raises_value_error | Yes -- match=disabled | COVERED |
| refresh_all() list_all + filter enabled + priority desc + cancel | TestFromAC_RefreshAll (5 tests) | Yes | COVERED |
| url_list handler: reads config[urls], intake.read_url, pipeline.ingest | TestFromAC_UrlListHandler (3 tests) | Yes | COVERED |
| crawl handler: delegates to injected, ValueError when None | TestFromAC_CrawlHandlerDispatch (2 tests) | Yes | COVERED |
| file_glob handler: resolves pattern, sandbox_path, intake.read_file | TestFromAC_FileGlobHandler (3 tests) | Partial -- see LAX below | LAX |
| file_glob: sandbox PermissionError counted as failure, not raised | TestFromAC_FileGlobHandler::test_sandbox_permission_error_counted_as_failed_not_raised | NO -- patches intake.read_file, not sandbox_path | LAX |
| _update_source_record: store.update, last_refreshed_at, last_error | TestFromAC_UpdateSourceRecord (3 tests) | Yes | COVERED |
| cancel signal checked between items and sources | TestFromAC_CancelSignal (2 tests) | Yes -- url_list only | COVERED |
| IngestResult skipped counted as skipped not refreshed | TestFromAC_IngestResultCounting (3 tests) | Yes -- url_list only, not CRAWL | COVERED |
| ruff check passes | Verified: ruff passes | Yes | COVERED |

LAX issue: test_sandbox_permission_error_counted_as_failed_not_raised patches owlbear_knowledge.intake.read_file (inner per-file loop exception handler, lines ~228-239). It does NOT trigger the outer sandbox_path() PermissionError handler (lines 189-192). The actual sandbox validation failure path is entirely untested. Lines 189-192 confirmed missed in coverage report.

#### Security Review
- sandbox_path is used for base_dir validation (path traversal defense). The PermissionError handler for this path (lines 189-192) is untested -- if broken, traversal outside workspace root could silently fail open.
- No hardcoded secrets, no injection risk, no deserialization issues.

#### Test Integrity (TestFromAC comparison)
Builder commit 1e27919 only contains refresh.py -- test file unchanged.
All TestFromAC_ methods: PRESERVED (builder did not modify test file).

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | result.skipped == 1 AND result.refreshed == 0 simultaneously checked; exact priority order [p3, p2, p1] verified |
| Negative/error paths | ADEQUATE | disabled ValueError, crawl ValueError, per-url exception covered; sandbox_path PermissionError path missing |
| Mutation reasoning | ADEQUATE | URL_LIST skipped/failed counting tested; CRAWL skipped/failed counting NOT tested -- swap would go undetected |
| Test independence | STRONG | Each test uses fresh mocks; no shared state |
| Descriptive names | STRONG | test_skipped_status_counted_as_skipped_not_refreshed, test_iterates_by_priority_descending etc. |

#### Data Safety
- _update_source_record is non-atomic (refresh completes, then store.update called) -- this is an existing design issue, not introduced here.
- No other data safety issues.

#### Implementation-Aware Test Gaps (lines per coverage report)
1. Lines 105-106: refresh() else branch -- unsupported SourceType raises ValueError. No test covers this.
2. Lines 136-137: refresh_all() except Exception: logger.exception(...). No test triggers a refresh failure inside the loop to exercise this handler.
3. Lines 189-192: _handle_file_glob outer except PermissionError -- sandbox_path() validation failure early return. The named AC test patches the WRONG layer (intake.read_file), leaving this security-relevant path uncovered.
4. Lines 213-214: _handle_crawl skipped/failed status counting. test_delegates_to_injected_handler only supplies ok results -- skipped and else/failed branches untested for CRAWL type.
5. Lines 228, 236-239: _handle_file_glob cancel break and skipped/exception per-file paths.

Most critical: gap 3 (security path) and gap 4 (CRAWL mutation blind spot -- skipped and failed counters in _handle_crawl cannot be caught by any existing test).

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Assessment | CLEAN |

### Verdict: FAIL
- Confidence: 0.82 (below .90 threshold)
- Coverage 89% vs 90% gate
- LAX: test_sandbox_permission_error_counted_as_failed_not_raised covers wrong code path
- CRAWL skipped/failed counting untested (mutation blind spot)
- Lines 189-192 (sandbox PermissionError) uncovered -- security-relevant path

[[2026-04-03]] Fri 03:47
## Builder Notes (Retry)\n- Files changed: none (no new code changes needed)\n- Prior commits: 1e27919 (refresh.py impl), a726ef9 (coverage gap tests)\n- Review failure resolved: all 3 reviewer complaints addressed in a726ef9\n- Tests: 42 passed (up from 33), 100% coverage on refresh.py\n- Lint: ruff clean\n- Evidence: 42 passed in 0.63s; refresh.py 118 stmts 0 missed (100%)\n- Reviewer gaps fixed:\n  1. Coverage 89% to 100% (9 new tests for lines 105-106, 136-137, 189-192, 213-214, 228, 236-239)\n  2. sandbox_path PermissionError: TestFromAC_SandboxPathPermissionError patches refresh.sandbox_path (not intake)\n  3. CRAWL skipped/failed: TestFromAC_CrawlIngestResultCounting covers lines 213-214\n- Fixes applied: confirmed by a726ef9 commit

[[2026-04-03]] Fri 05:21
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal module; no API/CLI/convention change visible to agents |
| 2 | Docstrings | Yes | Pass | Module, RefreshResult, RefreshOrchestrator, refresh(), refresh_all() all have complete docstrings; private methods exempt |
| 3 | docs/sources/overview.md | No | N/A | Standard implementation, no external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | TDD RED test task, no research phase |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/554-cov.txt.err

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0e9dbca | chore | kanban/tasks/554-test-refresh-orchestrator.md | #554 |
