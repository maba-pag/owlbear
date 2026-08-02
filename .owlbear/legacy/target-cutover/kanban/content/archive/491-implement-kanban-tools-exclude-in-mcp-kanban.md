---
id: 491
title: Implement KANBAN_TOOLS_EXCLUDE in mcp-kanban server
status: archived
priority: medium
created: 2026-03-31 06:22:24.604127+02:00
updated: 2026-03-31 16:31:28.195935+02:00
started: 2026-03-31 16:31:14.271717+02:00
completed: 2026-03-31 16:31:14.271717+02:00
tags:
- scope:mcp
- type:build
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Add _apply_tool_exclusions(server: FastMCP) -> set[str] helper in server.py that reads KANBAN_TOOLS_EXCLUDE env var
- [ ] Call server.remove_tool(name) for each comma-separated tool name (strip whitespace)
- [ ] Called inside app_lifespan before yield, matching the KANBAN_BIN pattern
- [ ] Invalid/unknown tool names silently ignored (try/except around remove_tool)
- [ ] Default (no env var set): all 7 tools registered (backwards-compatible)
- [ ] Tests: exclude one tool, exclude multiple, exclude none, invalid name (follow existing test_server.py mock patterns)
- [ ] Update skills/mcp-kanban/SKILL.md with Configuration section documenting KANBAN_TOOLS_EXCLUDE
- [ ] Update docs/setup-guide.md or .vscode/mcp.json example with env usage

See docs/research/kanban-tools-exclude-config.md for design details.

[[2026-03-31]] Tue 11:06
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A — T1 autonomous (no competing approaches, no arch change)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _apply_tool_exclusions(server, ...) helper | Clear signature, correct location | Refined: added explicit FastMCP param and return type |
| server.remove_tool(name) per comma-sep name | Matches FastMCP public API (v1.26) | Refined: specified call site in app_lifespan |
| Called inside app_lifespan before yield | Follows KANBAN_BIN env-read pattern | Added (was implicit in research doc) |
| Invalid names silently ignored | try/except around remove_tool | OK — ToolError on unknown name |
| Default: all 7 tools registered | Backwards-compatible | OK |
| Tests: 4 categories | Sufficient coverage for helper | OK — test-writer uses test_server.py patterns |
| Update SKILL.md | Docs update scoped to mcp-kanban | OK |
| Update setup-guide or mcp.json example | Docs update | OK |

### Architecture Notes
Follows existing pattern: KANBAN_BIN is read in app_lifespan, not at module level. Tool exclusion goes in the same lifespan, before yield, after binary discovery. FastMCP.remove_tool is the stable public API (verified in v1.26.0 source). Helper is sync, pure, and directly testable without async context. Existing test_server.py mocks Path.exists and _run_kanban — new tests should mock server.remove_tool or inspect the tool registry directly.

### Changes Made
- Refined AC: explicit function signature, call site, test pattern reference
- Preserved research doc reference

### Dependencies
- None — FastMCP remove_tool already available in installed SDK

[[2026-03-31]] Tue 14:03
## Test-Writer Notes
- Test file: tests/test_kanban_tools_exclude_491.py
- Classes: TestFromAC_ApplyToolExclusions, TestFromAC_LifespanToolExclusion
- Tests per category: happy 4, edge 3, error 2, boundary 2
- Total: 15 tests, all FAIL (ImportError on _apply_tool_exclusions) [check]
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| _apply_tool_exclusions reads KANBAN_TOOLS_EXCLUDE | test_exclude_single_tool_calls_remove_tool_once | happy |
| remove_tool per comma-sep name | test_exclude_multiple_tools_calls_remove_tool_for_each | happy |
| Whitespace stripped | test_whitespace_stripped_from_tool_names | edge |
| Invalid names silently ignored | test_invalid_tool_name_does_not_raise | error |
| Invalid + valid mixed | test_invalid_name_mixed_with_valid_still_excludes_valid | error |
| Default (no env var): no removals | test_no_env_var_remove_tool_never_called, test_lifespan_default_no_tool_removals | happy |
| Empty env var: no removals | test_empty_env_var_remove_tool_never_called | edge |
| Returns set[str] | test_returns_set_type, test_returns_empty_set_when_no_env_var | happy |
| All 7 names accepted | test_all_seven_tool_names_accepted | boundary |
| Trailing comma ignored | test_trailing_comma_ignored | boundary |
| app_lifespan calls _apply_tool_exclusions before yield | test_lifespan_calls_apply_tool_exclusions | happy |
| app_lifespan passes server arg | test_lifespan_passes_server_to_apply_tool_exclusions | happy |
| app_lifespan with env var removes tool | test_lifespan_removes_tool_when_env_var_set | happy |

[[2026-03-31]] Tue 14:22
## Builder Notes
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py, skills/mcp-kanban/SKILL.md, docs/setup-guide.md
- Tests: 15 passed (test_kanban_tools_exclude_491.py) + 4 pre-existing server tests, 19 total
- Lint: ruff clean
- Coverage: _apply_tool_exclusions fully covered by 15 tests; overall server.py 34% due to pre-existing uncovered tool handlers
- Fixes applied: PLW2901 (loop var rename raw/tool_name), S110 (noqa)

[[2026-03-31]] Tue 15:21
## Review Evidence

### Test Results
- pytest (tests/test_kanban_tools_exclude_491.py): 15 passed, 0 failed
- Pre-existing failures in packages/mcp-kanban/tests/test_server.py: 2 failures (test_move_task_success_passes_args, test_pick_task_success_passes_args) -- these are RED-phase tests for task #489 (move/pick JSON output), unrelated to #491

### Lint Results
- ruff check packages/mcp-kanban/ tests/test_kanban_tools_exclude_491.py: All checks passed!

### Coverage
- _apply_tool_exclusions: All branches manually verified covered (no-env-var, empty, single, multiple, whitespace-strip, trailing-comma, exception-swallow, mixed-valid-invalid)
- app_lifespan call site: covered by TestFromAC_LifespanToolExclusion (3 tests)

### Pass 1 -- CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| _apply_tool_exclusions helper | test_exclude_single_tool_calls_remove_tool_once | Yes -- assert_called_once_with | COVERED |
| remove_tool per comma-sep name | test_exclude_multiple_tools_calls_remove_tool_for_each | Yes -- call_count==3, exact name set | COVERED |
| Whitespace stripped | test_whitespace_stripped_from_tool_names | Yes -- no spaces in called_names | COVERED |
| Called in app_lifespan before yield | test_lifespan_calls_apply_tool_exclusions | Yes -- assert_called_once() | COVERED |
| Invalid names silently ignored | test_invalid_tool_name_does_not_raise | Yes -- must not raise | COVERED |
| Default no env var: no removals | test_no_env_var_remove_tool_never_called | Yes -- assert_not_called | COVERED |
| Returns set[str] | test_returns_set_type, test_returns_empty_set_when_no_env_var | Yes -- isinstance + exact == set() | COVERED |
| All 7 names accepted | test_all_seven_tool_names_accepted | Yes -- call_count==7 | COVERED |
| Trailing comma ignored | test_trailing_comma_ignored | Yes -- empty string not in called_names | COVERED |
| SKILL.md Configuration section | setup-guide.md + SKILL.md verified (see AC Compliance) | N/A (doc artifact) | COVERED |

#### Security Review
- No hardcoded secrets
- No injection: env var read with os.environ.get, passed to SDK remove_tool API only
- No path traversal
- No insecure deserialization
- Exception swallow (BLE001, S110) is intentional per AC, suppressed with noqa
- No secret leakage in logs or errors
- No new dependencies
- Result: No security issues found

#### Test Integrity (TestFromAC comparison)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ApplyToolExclusions::test_exclude_single_tool_calls_remove_tool_once | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_exclude_multiple_tools_calls_remove_tool_for_each | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_no_env_var_remove_tool_never_called | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_empty_env_var_remove_tool_never_called | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_whitespace_stripped_from_tool_names | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_invalid_tool_name_does_not_raise | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_invalid_name_mixed_with_valid_still_excludes_valid | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_returns_set_type | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_returns_empty_set_when_no_env_var | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_all_seven_tool_names_accepted | No change | PRESERVED |
| TestFromAC_ApplyToolExclusions::test_trailing_comma_ignored | No change | PRESERVED |
| TestFromAC_LifespanToolExclusion::test_lifespan_calls_apply_tool_exclusions | No change | PRESERVED |
| TestFromAC_LifespanToolExclusion::test_lifespan_passes_server_to_apply_tool_exclusions | No change | PRESERVED |
| TestFromAC_LifespanToolExclusion::test_lifespan_default_no_tool_removals | No change | PRESERVED |
| TestFromAC_LifespanToolExclusion::test_lifespan_removes_tool_when_env_var_set | No change | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG -- specific call_count, exact name sets, assert_called_once_with
- Negative/error-path coverage: STRONG -- invalid names, empty env, no env, trailing comma all tested
- Manual mutation reasoning: STRONG -- changing remove_tool call would fail multiple tests
- Test independence: STRONG -- each test uses fresh _make_mock_server()
- Descriptive names: STRONG

#### Data Safety
- No shared mutable state, no LLM output, no transactions, no unbounded input
- Result: No data safety issues

#### Implementation-Aware Gap Analysis
- All branches of _apply_tool_exclusions covered: early return, empty-string filter, strip, remove_tool success, exception swallow
- Minor informational gap: no test verifies the returned set CONTAINS excluded names (e.g., result == {list_tasks}) -- only type and empty case tested. App_lifespan ignores return value so this cannot mask a runtime bug.
- Builder process quality: CLEAN (single Builder Notes entry, no retries)

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| _apply_tool_exclusions(server: FastMCP) -> set[str] helper in server.py | server.py line 62: def _apply_tool_exclusions(server: FastMCP) -> set[str] | PASS |
| server.remove_tool(name) per comma-sep name (strip whitespace) | server.py lines 65-78; test_exclude_multiple_tools and test_whitespace_stripped pass | PASS |
| Called inside app_lifespan before yield | server.py line ~87: _apply_tool_exclusions(_server) before yield; test_lifespan_calls_apply_tool_exclusions passes | PASS |
| Invalid names silently ignored (try/except around remove_tool) | server.py line 76: except Exception: pass noqa BLE001 S110; test_invalid_tool_name_does_not_raise passes | PASS |
| Default (no env var): all 7 tools registered | test_no_env_var_remove_tool_never_called + test_lifespan_default_no_tool_removals both pass | PASS |
| Tests: exclude one, multiple, none, invalid (existing patterns) | 15 tests pass across TestFromAC_ApplyToolExclusions + TestFromAC_LifespanToolExclusion | PASS |
| Update skills/mcp-kanban/SKILL.md with Configuration section | SKILL.md: Configuration section added with KANBAN_TOOLS_EXCLUDE table row and usage docs | PASS |
| Update docs/setup-guide.md with env usage | setup-guide.md lines 153, 163: KANBAN_TOOLS_EXCLUDE in JSON example and variable table | PASS |

### Verdict: PASS
Confidence: .95

All AC lines verified with specific evidence. Implementation follows existing KANBAN_BIN pattern. Tests are complete, well-structured, and adversarially sound. ruff clean. Pre-existing failures in test_server.py are RED-phase tests for unrelated task #489 and were present before this builder's commit (f6c0155).

[[2026-03-31]] Tue 16:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _apply_tool_exclusions helper | server.py L62: correct signature | PASS |
| remove_tool per comma-sep name | server.py L65-78, tests confirm | PASS |
| Called in app_lifespan before yield | server.py L96: before yield | PASS |
| Invalid names silently ignored | except Exception: pass, test passes | PASS |
| Default no env var: all 7 tools | test_no_env_var passes | PASS |
| Tests: 4 categories | 15/15 pass | PASS |
| SKILL.md Configuration section | SKILL.md L46-56: table + section | PASS |
| setup-guide.md env usage | L153, L163: JSON example + table | PASS |

### Test Results
- pytest (task scope): 15 passed, 0 failed
- pytest (full suite): 2213 passed, 140 failed (all pre-existing, none in #491 scope)
- ruff: All checks passed

### AC Quality: 5/5
AC was specific with explicit function signature, call site, error handling, test categories, and doc targets. No builder improvisation needed.

### Deduction breakdown: none (all AC verified, reviewer evidence thorough, lint clean, no task-scope failures)
### Confidence: .98
### Action: archive

### Upstream gap
Test file (test_kanban_tools_exclude_491.py) was not committed by test-writer. Committed by auditor as orphaned deliverable.

[[2026-03-31]] Tue 16:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _apply_tool_exclusions helper | server.py L62: correct signature | PASS |
| remove_tool per comma-sep name | server.py L65-78, tests confirm | PASS |
| Called in app_lifespan before yield | server.py L96: before yield | PASS |
| Invalid names silently ignored | except Exception: pass, test passes | PASS |
| Default no env var: all 7 tools | test_no_env_var passes | PASS |
| Tests: 4 categories | 15/15 pass | PASS |
| SKILL.md Configuration section | SKILL.md L46-56: table + section | PASS |
| setup-guide.md env usage | L153, L163: JSON example + table | PASS |

### Test Results
- pytest (task scope): 15 passed, 0 failed
- pytest (full suite): 2213 passed, 140 failed (all pre-existing, none in #491 scope)
- ruff: All checks passed

### AC Quality: 5/5
AC was specific with explicit function signature, call site, error handling, test categories, and doc targets. No builder improvisation needed.

### Deduction breakdown: none (all AC verified, reviewer evidence thorough, lint clean, no task-scope failures)
### Confidence: .98
### Action: archive

### Upstream gap
Test file (test_kanban_tools_exclude_491.py) was not committed by test-writer. Committed by auditor as orphaned deliverable.

[[2026-03-31]] Tue 16:31
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f6c0155 | feat | server.py, SKILL.md, setup-guide.md | #491 |
| 0c79943 | test | test_kanban_tools_exclude_491.py | #491 |
