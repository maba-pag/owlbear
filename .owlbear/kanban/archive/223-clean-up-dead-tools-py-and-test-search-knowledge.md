---
id: 223
title: Clean up dead tools.py and test_search_knowledge.py in mcp-knowledge
status: archived
priority: medium
created: 2026-03-30 16:48:43.763424+02:00
updated: 2026-04-03 03:00:20.745260+02:00
started: 2026-03-30 20:46:51.745746+02:00
completed: 2026-04-03 02:59:31.217061+02:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
- chore
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Remove superseded code from packages/mcp-knowledge/.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py deleted (standalone search_knowledge superseded by server.py v2 API)
- [ ] packages/mcp-knowledge/tests/test_search_knowledge.py deleted (tests the deleted tools.py module)
- [ ] No imports of owlbear_mcp_knowledge.tools remain in the codebase
- [ ] All remaining mcp-knowledge tests pass

## Context
tools.py was built during #72 pipeline using asyncio.to_thread(query_for_context). Task #152 rewrote search_knowledge in server.py to use await qs.query() with StructuredSearchResult output. tools.py is no longer registered on the FastMCP server and has no callers.
See docs/research/search-knowledge-tool-impl.md section 6 (Supersession Notice).

[[2026-04-02]] Thu 22:45
## Review Evidence

**Reviewer:** reviewer | **Date:** 2026-04-02

### Test Results
- pytest packages/mcp-knowledge/tests/: 21 failed, 120 passed
- All 21 failures are pre-existing RED tests in test_outputschema_541.py (task #541 TDD phase)
- Failure isolation confirmed: all 21 failures reference TestFromAC_ classes in test_outputschema_541.py only

### Lint Results
- ruff check packages/mcp-knowledge/: All checks passed!

### Coverage
- Not applicable (deletion-only task, no new Python code)

### Pass 1 - CRITICAL

#### No TestFromAC classes (non-impl deletion task) - Steps 6.0 and 6.2 skipped

#### Security Review
- No new code introduced (pure deletion)
- No security issues found

#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: tools.py deleted | Test-Path 'packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py' = False; git commit 2ad91cd | PASS |
| AC2: test_search_knowledge.py deleted | Test-Path 'packages/mcp-knowledge/tests/test_search_knowledge.py' = False; git commit 2ad91cd | PASS |
| AC3: No imports of owlbear_mcp_knowledge.tools remain | grep_search found 6 remaining imports in tests/test_bookmark_pipeline_136.py (lines 715, 723, 743, 761, 778, 792). Builder claimed 'all 14 references were in test_search_knowledge.py' - FALSE | FAIL |
| AC4: Remaining mcp-knowledge tests pass | 120 passed, 21 pre-existing RED fails (test_outputschema_541.py) | PASS |

#### AC3 Detail
Builder self-report: 'all 14 references to owlbear_mcp_knowledge.tools were in test_search_knowledge.py (now deleted)' - INACCURATE.

6 remaining imports exist in tests/test_bookmark_pipeline_136.py:
- L715: from owlbear_mcp_knowledge.tools import AppContext
- L723: from owlbear_mcp_knowledge.tools import AppContext
- L743: from owlbear_mcp_knowledge.tools import AppContext, bookmark_source
- L761: from owlbear_mcp_knowledge.tools import AppContext, bookmark_source
- L778: from owlbear_mcp_knowledge.tools import AppContext, list_bookmarks
- L792: from owlbear_mcp_knowledge.tools import AppContext, list_bookmarks

These are local imports in TestFromAC_MCPBookmarkTools tests (task #136 RED phase). They now fail with 'ModuleNotFoundError: No module named owlbear_mcp_knowledge.tools'. Confirmed pre-existing: tests/test_bookmark_pipeline_136.py MCPBookmarkTools tests were already failing before commit 2ad91cd (the functions bookmark_source and list_bookmarks were never in tools.py). Task #520 was created to address #136 stale references to tools.py.

Mitigation note: pre-existing failures, no new regression, #520 tracks resolution. However AC3 is literally unmet.

#### Additional Checks
- __init__.py: clean (no tools references)
- __main__.py: clean (no tools references)
- __all__ in server.py: not affected by deletion

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 (no retries) |
| Approach variation | N/A |
| Assessment | CLEAN |

### Informational (Pass 2)
- Builder self-report on AC3 was inaccurate ('all 14 references' claimed, 6 remain)
- The broader test suite (tests/ directory) was not run; only packages/mcp-knowledge/tests/ was tested by builder

### Verdict: FAIL (.93 confidence)
AC3 not met: 6 imports of owlbear_mcp_knowledge.tools remain in tests/test_bookmark_pipeline_136.py.
Builder must remove or update these imports so that the literal AC 'No imports remain in the codebase' is satisfied.
Mitigation path: since test_bookmark_pipeline_136.py references bookmark_source/list_bookmarks that never existed in tools.py, these are orphaned RED-phase imports for task #136. Builder should update the imports to point to the future server.py location (matching task #520's AC), or task #223's AC should be updated to exclude test files owned by other tasks.

[[2026-04-02]] Thu 23:53
## Test-Writer Notes
- Test file: tests/test_cleanup_tools_223.py
- Classes: TestFromAC_ToolsCleanup
- Tests per category: happy 0, edge 0, error 0, boundary 0 (deletion/cleanup task)
- Total: 3 tests, all FAIL
- ruff: clean
- State note: tools.py EXISTS in working tree (prior builder commit may have been reverted); test_search_knowledge.py is already deleted.
- AC coverage:
  - AC1 (tools.py deleted): test_tools_py_source_file_absent, test_tools_module_not_importable (2 tests, both FAIL)
  - AC2 (test_search_knowledge.py deleted): already satisfied, test passes trivially, omitted per RED-phase rule
  - AC3 (no imports remain): test_no_codebase_imports_of_tools_module (1 test, FAILS with 8 occurrences in test_bookmark_pipeline_136.py)
  - AC4 (tests pass): smoke passes trivially, omitted per RED-phase rule

[[2026-04-03]] Fri 01:54
[[2026-04-03]] Fri 01:52
## Review Evidence (Round 2)

**Reviewer:** reviewer | **Date:** 2026-04-03

### Test Results
- pytest tests/test_cleanup_tools_223.py: 3 passed, 0 failed
- pytest packages/mcp-knowledge/tests/ (excl. test_outputschema_541.py): 119 passed, 0 failed
- test_outputschema_541.py: 4 pre-existing RED failures (task #541, unchanged from prior review)

### Lint Results
- ruff check packages/mcp-knowledge/ tests/test_cleanup_tools_223.py: All checks passed!

### Coverage
- Not applicable (deletion-only task, no new Python code introduced)

### Pass 1 - CRITICAL

#### 6.0 TestFromAC Coverage (test_cleanup_tools_223.py)
| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|------------------------|---------|
| AC1: tools.py deleted | test_tools_py_source_file_absent, test_tools_module_not_importable | Yes - file-existence + ImportError checks | COVERED |
| AC3: no imports remain | test_no_codebase_imports_of_tools_module | Yes - regex-scans all .py files | COVERED |

#### 6.1 Security Review
- No new code introduced (deletion + import path corrections)
- No security issues found

#### 6.2 TestFromAC Comparison
Builder modified TestFromAC_MCPBookmarkTools (task #136) in tests/test_bookmark_pipeline_136.py.
These were NOT in the task-writer's tests for #223 - they are task #136 RED-phase tests.
Previous reviewer explicitly instructed: update imports to server.py to satisfy AC3.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_app_context_has_bookmark_pipeline_field | import: .tools to .server; assertion unchanged | UPDATED (import correction, not weakened) |
| test_app_context_has_bookmark_store_field | import: .tools to .server; assertion unchanged | UPDATED |
| test_bookmark_source_function_registered | module checked: tools_mod to server_mod; same hasattr assertion | UPDATED |
| test_list_bookmarks_function_registered | module checked: tools_mod to server_mod; same hasattr assertion | UPDATED |
| test_bookmark_source_calls_pipeline_process | import: .tools to .server; test body unchanged | UPDATED |
| test_bookmark_source_reason_is_optional | import: .tools to .server; test body unchanged | UPDATED |
| test_list_bookmarks_calls_store_list | import: .tools to .server; test body unchanged | UPDATED |
| test_list_bookmarks_tag_and_min_score_optional | import: .tools to .server; test body unchanged | UPDATED |

Note: TestFromAC_MCPBookmarkTools tests still FAIL (RED-phase for #136 - expected; functions not yet in server.py). Pre-existing before 2ad91cd per prior review.

#### 6.3 Test Quality
| Dimension | Rating |
|-----------|--------|
| Assertion specificity | STRONG - file-existence, ImportError, regex-scan |
| Negative/error-path coverage | STRONG - tests designed to catch partial cleanup |
| Mutation resistance | STRONG - test_no_codebase_imports re-scans full tree on each run |
| Test independence | STRONG - no shared state |
| Descriptive names | STRONG |

#### 6.7 Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder commits | 2 (2ad91cd first, 7cefe9c second) |
| Approach variation | Yes - second commit fixed stale imports as directed |
| Assessment | FRICTION (informational only) |

Note: builder's second commit has no ## Builder Notes section in task body.

#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: tools.py deleted | Test-Path False; test_tools_py_source_file_absent PASS; test_tools_module_not_importable PASS; git commit 7cefe9c | PASS |
| AC2: test_search_knowledge.py deleted | Test-Path False; confirmed absent | PASS |
| AC3: No imports of owlbear_mcp_knowledge.tools remain | grep clean; test_no_codebase_imports_of_tools_module PASS; test_bookmark_pipeline_136.py now uses server imports | PASS |
| AC4: Remaining mcp-knowledge tests pass | 119 passed; RED-phase pre-existing failures unchanged (4 in test_outputschema_541.py) | PASS |

### Verdict: PASS (.93 confidence)
All 4 AC lines verified with evidence. The single FAIL from round 1 (AC3 stale imports) is resolved.

[[2026-04-03]] Fri 02:01
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure deletion chore; no behavior/API change; no hits for tools.py in copilot-instructions.md |
| 2 | Docstrings | No | N/A | tools.py deleted (no new modules); test imports corrected only |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used in this cleanup task |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Updated | docs/research/search-knowledge-tool-impl.md line 118 stale ('cleanup task created' -  now states 'deleted in #223'); committed 4981614 |

### Files Updated
- docs/research/search-knowledge-tool-impl.md (supersession notice updated)

### Scratch Files Cleaned
- None (no scratch files found for #223)

[[2026-04-03]] Fri 03:00
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c91c63f | test | tests/test_cleanup_tools_223.py | #223 |
| 2ad91cd | chore | deleted tools.py, test_search_knowledge.py | #223 |
| 7cefe9c | chore | deleted tools.py, fixed test_bookmark_pipeline_136.py | #223 |
| 4981614 | docs | docs/research/search-knowledge-tool-impl.md | #223 |
| b9457a6 | chore | kanban/tasks/223-*.md | #223 |
