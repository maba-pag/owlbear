---
id: 736
title: 'Tests: browser_snapshot tool in BrowserToolset (RED phase for #727)'
status: todo
priority: important
created: 2026-03-10T20:12:11.0632312+01:00
updated: 2026-03-10T22:10:28.0639138+01:00
tags:
    - phase-browser
    - scope:core
    - browser
    - test
claimed_by: test-writer
claimed_at: 2026-03-10T22:10:28.0639138+01:00
class: standard
---

**Source:** docs/research/browser-snapshot-tool-research.md

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
