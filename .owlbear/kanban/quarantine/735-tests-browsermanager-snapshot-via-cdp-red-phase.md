---
id: 735
title: 'Tests: BrowserManager.snapshot() via CDP (RED phase for #726)'
status: archived
priority: important
created: 2026-03-10T19:57:37.5624368+01:00
updated: 2026-03-11T09:49:10.2635382+01:00
started: 2026-03-11T08:46:46.0941889+01:00
completed: 2026-03-11T09:49:10.2635382+01:00
tags:
    - phase-browser
    - scope:core
    - browser
    - test
class: standard
---

**Source:** docs/research/a11y-snapshot.md

RED-phase tests for #726. Mock CDPSession.send() with canned AXNode responses.

**AC:**

- [ ] Test snapshot(filter='full') returns list[AXNodeInfo] with all non-ignored nodes
- [ ] Test snapshot(filter='interactive') returns only focusable/actionable nodes
- [ ] Test snapshot(filter='text') returns only StaticText + heading nodes
- [ ] Test CDP session is created and detached per call (no leaked sessions)
- [ ] Test works in both launch and CDP modes (mock both paths)
- [ ] Test AXNodeInfo frozen dataclass has fields: id (int), role (str), name (str), description (str), properties (dict)
- [ ] All tests FAIL (RED phase  implementation does not yet exist)

[[2026-03-10]] Tue 20:45

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Test filter='full' returns all non-ignored nodes | Verifiable  clear filter semantics from a11y-snapshot.md S3e | Keep |
| Test filter='interactive' returns focusable/actionable | Verifiable  role set defined in research S3e | Keep |
| Test filter='text' returns StaticText + headings | Verifiable  cheapest filter, clear criteria | Keep |
| Test CDP session created/detached per call | Verifiable  mock assertions on new_cdp_session/detach | Keep |
| Test both launch and CDP modes | Verifiable  existing pw_mocks fixture shows pattern | Keep |
| Test AXNodeInfo frozen dataclass fields | Verifiable  shape + frozen constraint | Keep |
| All tests FAIL (RED phase) | Verifiable  implementation does not exist yet | Keep |

### Architecture Notes

- **Pattern consistency:** Follow existing test_browser_manager.py pattern (pw_mocks fixture, AsyncMock, patch, pytest.mark.asyncio)
- **Module placement:** New test file tests/test_browser_snapshot.py (or extend test_browser_manager.py  test-writer's call)
- **Mock strategy:** Mock context.new_cdp_session(page) returning a CDPSession mock whose send() returns canned AXNode array
- **Canned data:** Include mix of roles (button, link, StaticText, heading, generic) with both focusable and non-focusable nodes to exercise all 3 filters
- **Single domain:** Browser tools only  no cross-domain concerns

### Changes Made

- Moved #735 backlog -> todo
- Added depends_on: [735] to #726 frontmatter (was only in body text)

### Dependencies

- Verified: #726 (impl) now properly depends_on #735 (test) in YAML frontmatter
- Verified: #727 (browser_snapshot tool) depends on #726  downstream, not blocking
- No circular dependencies

[[2026-03-10]] Tue 20:45

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Test filter='full' returns all non-ignored nodes | Verifiable  clear filter semantics from a11y-snapshot.md S3e | Keep |
| Test filter='interactive' returns focusable/actionable | Verifiable  role set defined in research S3e | Keep |
| Test filter='text' returns StaticText + headings | Verifiable  cheapest filter, clear criteria | Keep |
| Test CDP session created/detached per call | Verifiable  mock assertions on new_cdp_session/detach | Keep |
| Test both launch and CDP modes | Verifiable  existing pw_mocks fixture shows pattern | Keep |
| Test AXNodeInfo frozen dataclass fields | Verifiable  shape + frozen constraint | Keep |
| All tests FAIL (RED phase) | Verifiable  implementation does not exist yet | Keep |

### Architecture Notes

- **Pattern consistency:** Follow existing test_browser_manager.py pattern (pw_mocks fixture, AsyncMock, patch, pytest.mark.asyncio)
- **Module placement:** New test file tests/test_browser_snapshot.py (or extend test_browser_manager.py  test-writer's call)
- **Mock strategy:** Mock context.new_cdp_session(page) returning a CDPSession mock whose send() returns canned AXNode array
- **Canned data:** Include mix of roles (button, link, StaticText, heading, generic) with both focusable and non-focusable nodes to exercise all 3 filters
- **Single domain:** Browser tools only  no cross-domain concerns

### Changes Made

- Moved #735 backlog -> todo
- Added depends_on: [735] to #726 frontmatter (was only in body text)

### Dependencies

- Verified: #726 (impl) now properly depends_on #735 (test) in YAML frontmatter
- Verified: #727 (browser_snapshot tool) depends on #726  downstream, not blocking
- No circular dependencies

[[2026-03-10]] Tue 21:37

## Test-Writer Notes

- Test file: tests/test_browser_snapshot.py
- Classes: TestFromAC_AXNodeInfo, TestFromAC_SnapshotFull, TestFromAC_SnapshotInteractive, TestFromAC_SnapshotText, TestFromAC_SnapshotCDPSession, TestFromAC_SnapshotBothModes
- Tests per category: happy 9, edge 4, error 1, boundary 5
- Total: 19 tests, all FAIL (ImportError / AttributeError)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| AXNodeInfo frozen dataclass fields | test_construction_with_all_fields, test_is_dataclass, test_is_frozen, test_has_expected_field_names | happy, boundary |
| filter='full' all non-ignored | test_returns_all_non_ignored_nodes, test_returns_ax_node_info_instances, test_excludes_ignored_nodes, test_empty_tree_returns_empty_list | happy, edge |
| filter='interactive' focusable/actionable | test_returns_interactive_roles, test_excludes_non_interactive, test_focusable_generic_included | happy, edge |
| filter='text' StaticText + heading | test_returns_static_text, test_returns_headings, test_excludes_non_text_nodes | happy, boundary |
| CDP session created/detached per call | test_creates_and_detaches_session, test_detaches_session_on_send_error, test_each_call_creates_new_session | happy, error, boundary |
| Both launch and CDP modes | test_launch_mode, test_cdp_mode | happy |

[[2026-03-10]] Tue 21:37

## Test-Writer Notes

- Test file: tests/test_browser_snapshot.py
- Classes: TestFromAC_AXNodeInfo, TestFromAC_SnapshotFull, TestFromAC_SnapshotInteractive, TestFromAC_SnapshotText, TestFromAC_SnapshotCDPSession, TestFromAC_SnapshotBothModes
- Total: 19 tests, all FAIL
- ruff: clean

[[2026-03-10]] Tue 23:36

## Builder Notes

- Files changed: src/owlbear/tools/browser/manager.py
- Tests: 19 passed, coverage 90% on manager.py
- Lint: ruff clean
- Evidence: 19/19 TestFromAC tests pass; 33/33 existing browser_manager tests pass (no regressions)
- Implementation: Added AXNodeInfo frozen dataclass + BrowserManager.snapshot() method using CDP Accessibility.getFullAXTree
- Fixes applied: None (clean implementation)

[[2026-03-11]] Wed 00:37

## Review Evidence

### Test Results

- pytest: 19 passed, 0 failed (test_browser_snapshot.py)
- Regression: 33/33 existing test_browser_manager.py tests pass

### Lint Results

- ruff: All checks passed

### Coverage

- manager.py: 90% (missing lines 86-89 RuntimeError guard on page property, 112-113 RuntimeError guard on snapshot context, 181-185 cleanup edge paths)

### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact counts (len==7), exact id exclusion (8 not in ids), isinstance checks, exact field set equality, FrozenInstanceError, assert_awaited_once, await_count==2 |
| Negative/error paths | ADEQUATE | test_detaches_session_on_send_error (error + cleanup), test_excludes_ignored_nodes, test_empty_tree_returns_empty_list, all exclusion tests |
| Mutation reasoning | STRONG | Removing ignored check -> test_excludes_ignored_nodes fails; changing_INTERACTIVE_ROLES -> test_returns_interactive_roles fails; removing finally -> test_detaches_session_on_send_error fails; removing frozen=True -> test_is_frozen fails; removing focusable fallback -> test_focusable_generic_included fails |
| Test independence | STRONG | Each test uses fresh pw_mocks/cdp_session fixtures, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario (e.g., test_focusable_generic_included, test_detaches_session_on_send_error) |

### Security Review

- No hardcoded secrets
- No injection risk (CDP method name is hardcoded string)
- No path traversal
- No insecure deserialization
- Input validation present (context None check, Literal type for filter)
- No new dependencies
- No secret leakage in logs

### Test Writer vs Builder Comparison

Test file is untracked (?? status) so no git diff available. Cross-referenced test-writer AC table against actual file:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_AXNodeInfo::test_construction_with_all_fields | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_is_dataclass | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_is_frozen | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_has_expected_field_names | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_returns_all_non_ignored_nodes | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_returns_ax_node_info_instances | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_excludes_ignored_nodes | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_empty_tree_returns_empty_list | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_returns_interactive_roles | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_excludes_non_interactive | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_focusable_generic_included | No change | PRESERVED |
| TestFromAC_SnapshotText::test_returns_static_text | No change | PRESERVED |
| TestFromAC_SnapshotText::test_returns_headings | No change | PRESERVED |
| TestFromAC_SnapshotText::test_excludes_non_text_nodes | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_creates_and_detaches_session | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_detaches_session_on_send_error | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_each_call_creates_new_session | No change | PRESERVED |
| TestFromAC_SnapshotBothModes::test_launch_mode | No change | PRESERVED |
| TestFromAC_SnapshotBothModes::test_cdp_mode | No change | PRESERVED |

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| filter='full' returns all non-ignored | 7 of 8 canned nodes returned (id=8 excluded) | test_returns_all_non_ignored_nodes, test_excludes_ignored_nodes, test_returns_ax_node_info_instances, test_empty_tree_returns_empty_list | PASS |
| filter='interactive' returns focusable/actionable | roles {button,link,textbox} present; StaticText,heading,generic excluded; focusable generic included | test_returns_interactive_roles, test_excludes_non_interactive, test_focusable_generic_included | PASS |
| filter='text' returns StaticText + heading | StaticText and heading roles present; button,link,generic,textbox excluded | test_returns_static_text, test_returns_headings, test_excludes_non_text_nodes | PASS |
| CDP session created/detached per call | assert_awaited_once on new_cdp_session+detach; detach called on error; 2 calls = 2 sessions | test_creates_and_detaches_session, test_detaches_session_on_send_error, test_each_call_creates_new_session | PASS |
| Both launch and CDP modes | Launch uses context.new_cdp_session; CDP uses cdp_context.new_cdp_session with BrowserConfig(cdp_endpoint=...) | test_launch_mode, test_cdp_mode | PASS |
| AXNodeInfo frozen dataclass fields | Fields {id,role,name,description,properties}; is_dataclass+frozen; FrozenInstanceError on mutation | test_construction_with_all_fields, test_is_dataclass, test_is_frozen, test_has_expected_field_names | PASS |
| All tests FAIL (RED phase) | RED phase completed by test-writer; builder implemented -> 19/19 now pass (expected TDD flow) | All 19 TestFromAC tests | PASS |

### Verdict: PASS (confidence .93)

[[2026-03-11]] Wed 00:37

## Review Evidence

### Test Results

- pytest: 19 passed, 0 failed (test_browser_snapshot.py)
- Regression: 33/33 existing test_browser_manager.py tests pass

### Lint Results

- ruff: All checks passed

### Coverage

- manager.py: 90% (missing lines 86-89 RuntimeError guard on page property, 112-113 RuntimeError guard on snapshot context, 181-185 cleanup edge paths)

### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact counts (len==7), exact id exclusion (8 not in ids), isinstance checks, exact field set equality, FrozenInstanceError, assert_awaited_once, await_count==2 |
| Negative/error paths | ADEQUATE | test_detaches_session_on_send_error (error + cleanup), test_excludes_ignored_nodes, test_empty_tree_returns_empty_list, all exclusion tests |
| Mutation reasoning | STRONG | Removing ignored check -> test_excludes_ignored_nodes fails; changing_INTERACTIVE_ROLES -> test_returns_interactive_roles fails; removing finally -> test_detaches_session_on_send_error fails; removing frozen=True -> test_is_frozen fails; removing focusable fallback -> test_focusable_generic_included fails |
| Test independence | STRONG | Each test uses fresh pw_mocks/cdp_session fixtures, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario (e.g., test_focusable_generic_included, test_detaches_session_on_send_error) |

### Security Review

- No hardcoded secrets
- No injection risk (CDP method name is hardcoded string)
- No path traversal
- No insecure deserialization
- Input validation present (context None check, Literal type for filter)
- No new dependencies
- No secret leakage in logs

### Test Writer vs Builder Comparison

Test file is untracked (?? status) so no git diff available. Cross-referenced test-writer AC table against actual file:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_AXNodeInfo::test_construction_with_all_fields | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_is_dataclass | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_is_frozen | No change | PRESERVED |
| TestFromAC_AXNodeInfo::test_has_expected_field_names | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_returns_all_non_ignored_nodes | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_returns_ax_node_info_instances | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_excludes_ignored_nodes | No change | PRESERVED |
| TestFromAC_SnapshotFull::test_empty_tree_returns_empty_list | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_returns_interactive_roles | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_excludes_non_interactive | No change | PRESERVED |
| TestFromAC_SnapshotInteractive::test_focusable_generic_included | No change | PRESERVED |
| TestFromAC_SnapshotText::test_returns_static_text | No change | PRESERVED |
| TestFromAC_SnapshotText::test_returns_headings | No change | PRESERVED |
| TestFromAC_SnapshotText::test_excludes_non_text_nodes | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_creates_and_detaches_session | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_detaches_session_on_send_error | No change | PRESERVED |
| TestFromAC_SnapshotCDPSession::test_each_call_creates_new_session | No change | PRESERVED |
| TestFromAC_SnapshotBothModes::test_launch_mode | No change | PRESERVED |
| TestFromAC_SnapshotBothModes::test_cdp_mode | No change | PRESERVED |

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| filter='full' returns all non-ignored | 7 of 8 canned nodes returned (id=8 excluded) | test_returns_all_non_ignored_nodes, test_excludes_ignored_nodes, test_returns_ax_node_info_instances, test_empty_tree_returns_empty_list | PASS |
| filter='interactive' returns focusable/actionable | roles {button,link,textbox} present; StaticText,heading,generic excluded; focusable generic included | test_returns_interactive_roles, test_excludes_non_interactive, test_focusable_generic_included | PASS |
| filter='text' returns StaticText + heading | StaticText and heading roles present; button,link,generic,textbox excluded | test_returns_static_text, test_returns_headings, test_excludes_non_text_nodes | PASS |
| CDP session created/detached per call | assert_awaited_once on new_cdp_session+detach; detach called on error; 2 calls = 2 sessions | test_creates_and_detaches_session, test_detaches_session_on_send_error, test_each_call_creates_new_session | PASS |
| Both launch and CDP modes | Launch uses context.new_cdp_session; CDP uses cdp_context.new_cdp_session with BrowserConfig(cdp_endpoint=...) | test_launch_mode, test_cdp_mode | PASS |
| AXNodeInfo frozen dataclass fields | Fields {id,role,name,description,properties}; is_dataclass+frozen; FrozenInstanceError on mutation | test_construction_with_all_fields, test_is_dataclass, test_is_frozen, test_has_expected_field_names | PASS |
| All tests FAIL (RED phase) | RED phase completed by test-writer; builder implemented -> 19/19 now pass (expected TDD flow) | All 19 TestFromAC tests | PASS |

### Verdict: PASS (confidence .93)

[[2026-03-11]] Wed 08:46

## Docs Gate - Checklist passed. Updated copilot-instructions.md Browser row. Docstrings verified. Sources already attributed. No CLI changes. Research doc linked

[[2026-03-11]] Wed 09:48

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| filter='full' returns all non-ignored | TestFromAC_SnapshotFull: 4 tests (7/8 nodes, ignored excluded, empty tree, isinstance) â€” all PASS | PASS |
| filter='interactive' returns focusable/actionable | TestFromAC_SnapshotInteractive: 3 tests (roles in/out, focusable generic) â€” all PASS | PASS |
| filter='text' returns StaticText+heading | TestFromAC_SnapshotText: 3 tests (StaticText, heading in, others out) â€” all PASS | PASS |
| CDP session created/detached per call | TestFromAC_SnapshotCDPSession: 3 tests (create+detach, detach on error, 2 calls=2 sessions) â€” all PASS | PASS |
| Both launch and CDP modes | TestFromAC_SnapshotBothModes: 2 tests (launch vs cdp_endpoint) â€” all PASS | PASS |
| AXNodeInfo frozen dataclass fields | TestFromAC_AXNodeInfo: 4 tests (construction, is_dataclass, frozen, field names) â€” all PASS | PASS |
| All tests FAIL (RED phase) | Completed: test-writer RED -> builder GREEN -> 19/19 pass | PASS |

### Test Results

- pytest (scoped): 19 passed, 0 failed (tests/test_browser_snapshot.py)
- pytest (full suite): 9 pre-existing failures unrelated to #735 (test_content_extractor wrapping, test_daemon stale imports)
- ruff: All checks passed (test_browser_snapshot.py, manager.py)

### Confidence: .97

### Action: archive
