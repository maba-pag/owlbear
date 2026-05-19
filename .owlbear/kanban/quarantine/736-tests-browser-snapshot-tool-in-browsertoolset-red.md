---
id: 736
title: 'Tests: browser_snapshot tool in BrowserToolset (RED phase for #727)'
status: archived
priority: important
created: 2026-03-10T20:12:11.0632312+01:00
updated: 2026-03-13T12:25:26.8843401+01:00
started: 2026-03-13T10:52:19.6921508+01:00
completed: 2026-03-13T12:25:26.8843401+01:00
tags:
    - phase-browser
    - scope:core
    - browser
    - test
class: standard
---

**Source:** docs/research/browser-snapshot-tool.md

RED-phase tests for #727. Follow existing test patterns in test_browser_toolset.py.

**Mock pattern note:** Unlike other tool wrappers that delegate to action functions (e.g., `browser_navigate`), `_snapshot` delegates directly to `self._manager.snapshot(filter=...)`. Mock `_manager.snapshot` as `AsyncMock` returning `list[AXNodeInfo]` stubs (see #726 AC for the dataclass: id, role, name, description, properties).

**AC:**

- [ ] `EXPECTED_TOOL_NAMES` updated to include `browser_snapshot` (7 entries); existing registration/backward-compat assertions updated from 6 to 7
- [ ] Test `browser_snapshot` registered in BrowserToolset (7 tools total)
- [ ] Test `_snapshot` wrapper delegates to `self._manager.snapshot(filter=...)`  mock `_manager.snapshot` as `AsyncMock`, call with explicit filter (e.g. `filter='full'`), assert mock called with `filter='full'`
- [ ] Test default `filter='interactive'` when no filter param passed  call `_snapshot()` with no args, assert mock called with `filter='interactive'`
- [ ] Test output formatting: `_manager.snapshot()` returns `list[AXNodeInfo]`; wrapper formats each node as `[{id}] {role}: {name}` joined by newlines; assert exact string match for 2-3 canned nodes
- [ ] Test tool description contains token-cost guidance: assert description string includes `interactive`, `full`, and at least one approximate token count (e.g. `~3600`)
- [ ] All new + modified tests FAIL (RED phase  `_snapshot` method and `browser_snapshot` registration do not yet exist)

[[2026-03-10]] Tue 20:46

## Architecture Review

**Verdict:** APPROVED (with refinements applied)

### AC Assessment

| AC Line (original) | Assessment | Action |
|---------------------|------------|--------|
| Test browser_snapshot registered (7 tools total) | Clear, verifiable | Kept |
| Test _snapshot delegates to BrowserManager.snapshot(filter=...) | Correct intent, but mock target not specified (manager method vs action function) | Refined: explicit mock pattern note added; test mocks `self._manager.snapshot` |
| Test default filter='interactive' | Clear, verifiable | Kept |
| Test output '[id] role: name' per line | Ambiguous: doesn't clarify that wrapper formats `list[AXNodeInfo]` from manager | Refined: wrapper receives `list[AXNodeInfo]`, formats to string; test uses canned nodes |
| Test tool description contains token-cost guidance | No specific assertion strings | Refined: check for `interactive`, `full`, and `~3600` |
| EXPECTED_TOOL_NAMES updated (7 entries) | Clear | Kept; clarified that existing assertions also update from 6 to 7 |
| All tests FAIL (RED phase) | Standard RED gate | Kept |

### Architecture Notes

- **Mock pattern divergence:** `_snapshot` delegates to `self._manager.snapshot()` (manager method), unlike other wrappers that delegate to action functions. AC now documents this so the test-writer uses the correct mock target (`_manager.snapshot` as AsyncMock, not `@patch` on an action function).
- **Dependency fix:** Removed `depends_on: [726]`. RED-phase tests mock the manager so they don't need `BrowserManager.snapshot()` implemented. This unblocks #735 and #736 test writers to work in parallel.
- **Pattern consistency:** Test structure follows existing `test_browser_toolset.py` classes (`TestBrowserToolsetRegistration`, `TestBrowserToolsetDelegation`).
- **Single domain:** Browser tools test file  no cross-domain concerns.

### Changes Made

- Removed dependency on #726 (`--remove-dep 726`)
- Rewrote task body with 7 precise, verifiable AC lines
- Added mock pattern note explaining manager-method delegation vs action-function delegation
- Moving to `todo`

### Dependencies

- Removed: #726 (not needed  tests mock the manager)
- Verified: #727 still depends on #736 (test-first TDD)
- No circular dependencies

[[2026-03-10]] Tue 20:46

## Architecture Review

**Verdict:** APPROVED (with refinements applied)

### AC Assessment

| AC Line (original) | Assessment | Action |
|---------------------|------------|--------|
| Test browser_snapshot registered (7 tools total) | Clear, verifiable | Kept |
| Test _snapshot delegates to BrowserManager.snapshot(filter=...) | Correct intent, but mock target not specified (manager method vs action function) | Refined: explicit mock pattern note added; test mocks `self._manager.snapshot` |
| Test default filter='interactive' | Clear, verifiable | Kept |
| Test output '[id] role: name' per line | Ambiguous: doesn't clarify that wrapper formats `list[AXNodeInfo]` from manager | Refined: wrapper receives `list[AXNodeInfo]`, formats to string; test uses canned nodes |
| Test tool description contains token-cost guidance | No specific assertion strings | Refined: check for `interactive`, `full`, and `~3600` |
| EXPECTED_TOOL_NAMES updated (7 entries) | Clear | Kept; clarified that existing assertions also update from 6 to 7 |
| All tests FAIL (RED phase) | Standard RED gate | Kept |

### Architecture Notes

- **Mock pattern divergence:** `_snapshot` delegates to `self._manager.snapshot()` (manager method), unlike other wrappers that delegate to action functions. AC now documents this so the test-writer uses the correct mock target (`_manager.snapshot` as AsyncMock, not `@patch` on an action function).
- **Dependency fix:** Removed `depends_on: [726]`. RED-phase tests mock the manager so they don't need `BrowserManager.snapshot()` implemented. This unblocks #735 and #736 test writers to work in parallel.
- **Pattern consistency:** Test structure follows existing `test_browser_toolset.py` classes (`TestBrowserToolsetRegistration`, `TestBrowserToolsetDelegation`).
- **Single domain:** Browser tools test file  no cross-domain concerns.

### Changes Made

- Removed dependency on #726 (`--remove-dep 726`)
- Rewrote task body with 7 precise, verifiable AC lines
- Added mock pattern note explaining manager-method delegation vs action-function delegation
- Moving to `todo`

### Dependencies

- Removed: #726 (not needed  tests mock the manager)
- Verified: #727 still depends on #736 (test-first TDD)
- No circular dependencies

[[2026-03-13]] Fri 08:36

## Test-Writer Notes

- Test file: tests/test_browser_toolset.py
- Classes: TestFromAC_BrowserSnapshotDelegation, TestFromAC_BrowserSnapshotOutput, TestFromAC_BrowserSnapshotDescription
- Tests per category: happy 12, edge 1, error 0, boundary 2
- Total: 15 tests (12 new + 3 modified existing), all FAIL
- ruff: clean
- AC coverage:
  - EXPECTED_TOOL_NAMES 7 entries: test_registers_seven_tools, test_tool_names_match, test_default_toolset_registers_seven_tools
  - Registration 7 tools: test_registers_seven_tools, test_tool_names_match
  - _snapshot delegates filter=...: test_snapshot_delegates_with_explicit_filter, test_snapshot_delegates_with_text_filter
  - Default filter=interactive: test_snapshot_default_filter_interactive
  - Output formatting: test_snapshot_output_formatting_multiple_nodes, test_snapshot_output_single_node, test_snapshot_output_empty_list
  - Description token-cost: test_description_contains_interactive, test_description_contains_full, test_description_contains_interactive_token_count, test_description_contains_text_token_count, test_description_contains_full_token_count, test_description_mentions_text_filter
  - All FAIL: 15 failed, 33 passed (existing)

[[2026-03-13]] Fri 09:14

## Builder Notes

- Files changed: src/owlbear/tools/browser/toolset.py
- Tests: 48 passed (33 existing + 15 new), coverage 96% on tools/browser/toolset.py
- Lint: ruff clean
- Implementation: Added `_snapshot` wrapper method delegating to `self._manager.snapshot(filter=...)`, registered `browser_snapshot` as 7th tool with token-cost description, updated docstrings from 6 to 7 tools
- Evidence: 15 FAILED -> 48 passed, ruff All checks passed

[[2026-03-13]] Fri 10:20

## Review Evidence

### Test Results

- pytest (scoped): 48 passed, 0 failed
- pytest (full suite): 2329 passed, 18 failed (all pre-existing  regex module, IngestPipeline API, _chat_loop import, line-count assertion, httpx timeout  zero browser toolset failures)

### Lint Results

- ruff: All checks passed

### Coverage

- tools/browser/toolset.py: 96% (missing L221 content-guard branch + L244-245 _snapshot manager-None guard  both acceptable)

### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Delegation: assert_awaited_once_with(filter=exact_value); Output: exact string match; Description: specific substring checks |
| Negative/error paths | ADEQUATE | Empty list edge case covered; manager-None guard existing in other tests |
| Mutation reasoning | STRONG | Changing default filter, format string, or delegation target would all be caught by specific assertions |
| Test independence | STRONG | Each test creates own toolset/page/mocks, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario+expected (e.g. test_snapshot_default_filter_interactive) |

### Security Review

- No hardcoded secrets
- No injection vectors (filter param passed through to manager)
- No path traversal, insecure deserialization, or log leakage
- No new dependencies added

### Test Writer vs Builder Comparison

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_BrowserSnapshotDelegation::test_snapshot_delegates_with_explicit_filter | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDelegation::test_snapshot_default_filter_interactive | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDelegation::test_snapshot_delegates_with_text_filter | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotOutput::test_snapshot_output_formatting_multiple_nodes | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotOutput::test_snapshot_output_single_node | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotOutput::test_snapshot_output_empty_list | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_contains_interactive | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_contains_full | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_contains_interactive_token_count | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_contains_text_token_count | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_contains_full_token_count | No change (new addition) | PRESERVED |
| TestFromAC_BrowserSnapshotDescription::test_description_mentions_text_filter | No change (new addition) | PRESERVED |
| (existing) test_registers_six_tools  test_registers_seven_tools | Renamed, assert 67 | STRENGTHENED (per AC) |
| (existing) test_default_toolset_registers_six_tools  _seven_ | Renamed, asserts EXPECTED_TOOL_NAMES (now 7) | STRENGTHENED (per AC) |
| (existing) EXPECTED_TOOL_NAMES | Added browser_snapshot (7 entries) | STRENGTHENED (per AC) |

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| EXPECTED_TOOL_NAMES updated to 7 entries; existing assertions from 67 | Diff: EXPECTED_TOOL_NAMES frozenset has 7 entries; test_registers_seven_tools asserts len==7 | test_registers_seven_tools, test_tool_names_match, test_default_toolset_registers_seven_tools | PASS |
| Test browser_snapshot registered (7 tools total) | test_registers_seven_tools: len(tools)==7; test_tool_names_match: set match includes browser_snapshot | test_registers_seven_tools, test_tool_names_match | PASS |
| Test _snapshot delegates to self._manager.snapshot(filter=...) | test_snapshot_delegates_with_explicit_filter: assert_awaited_once_with(filter='full') | test_snapshot_delegates_with_explicit_filter, test_snapshot_delegates_with_text_filter | PASS |
| Test default filter='interactive' | test_snapshot_default_filter_interactive: assert_awaited_once_with(filter='interactive') | test_snapshot_default_filter_interactive | PASS |
| Test output formatting: [id] role: name joined by newlines | test_snapshot_output_formatting_multiple_nodes: exact string match for 3 nodes; single_node and empty_list edge cases | test_snapshot_output_formatting_multiple_nodes, test_snapshot_output_single_node, test_snapshot_output_empty_list | PASS |
| Test description contains interactive, full, ~3600 | Six description tests check for interactive, full, text, ~3600, ~800, ~10500 | TestFromAC_BrowserSnapshotDescription (6 tests) | PASS |
| All tests FAIL (RED) then PASS (GREEN) | Test-writer: 15 failed; Builder: 48 passed (33+15) | Full suite confirms | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-13]] Fri 10:51

## Docs Gate

[[2026-03-13]] Fri 10:52

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Browser row already mentions 'a11y snapshot via CDP getFullAXTree' â€” no new behavior/convention |
| 2 | Docstrings complete | Yes | Pass | Module docstring lists 7 tools incl browser_snapshot; class docstring says 'all 7';_snapshot has docstring |
| 3 | sources/overview.md | No | N/A | 3 browser-snapshot entries already present (browser-use, Stagehand, Playwright CDP) from research phase |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/browser-snapshot-tool.md exists; linked in task body |
| 6 | No impact | N/A | -- | Items 2 and 5 apply |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/736-* files found)

[[2026-03-13]] Fri 12:25

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| EXPECTED_TOOL_NAMES updated (7 entries); existing assertions 6->7 | L24-33: frozenset has 7 entries incl browser_snapshot; test_registers_seven_tools asserts len==7; test_default_toolset_registers_seven_tools checks set | PASS |
| Test browser_snapshot registered (7 tools total) | test_registers_seven_tools + test_tool_names_match confirm 7 tools with browser_snapshot present | PASS |
| _snapshot delegates to self._manager.snapshot(filter=...) | test_snapshot_delegates_with_explicit_filter: assert_awaited_once_with(filter='full'); test_snapshot_delegates_with_text_filter: filter='text' | PASS |
| Default filter='interactive' | test_snapshot_default_filter_interactive: calls _snapshot() no args, asserts filter='interactive' | PASS |
| Output formatting [id] role: name per line | test_snapshot_output_formatting_multiple_nodes: exact match '[2] button: Submit\n[3] link: Home\n[7] textbox: Email'; single_node + empty_list edges | PASS |
| Description contains interactive, full, ~3600 | 6 tests check interactive, full, text, ~3600, ~800, ~10500 in description string | PASS |
| All tests FAIL (RED) -> PASS (GREEN) | Test-writer: 15 failed; Builder: 48 passed; Auditor verified 48 passed | PASS |

### Test Results

- pytest (scoped): 48 passed, 0 failed in 1.36s
- pytest (full suite): 3183 passed, 39 failed (all pre-existing: regex module, IngestPipeline API, Entity importance, _chat_loop import, role policies, httpx timeout, bootstrap lines  zero browser failures)
- ruff: All checks passed

### Confidence: .97

### Action: archive
