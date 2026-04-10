---
id: 726
title: Add accessibility-tree snapshot to BrowserManager
status: archived
priority: important
created: 2026-03-10T18:19:15.977845+01:00
updated: 2026-03-11T10:27:04.0992972+01:00
started: 2026-03-10T19:07:15.6779009+01:00
completed: 2026-03-11T10:27:04.0992972+01:00
tags:
    - phase-browser
    - scope:core
    - browser
depends_on:
    - 735
claimed_by: writer
claimed_at: 2026-03-11T10:26:58.168604+01:00
class: standard
---

**Source:** docs/research/a11y-snapshot.md, docs/research/pinchtab.md S4.3

Add an async `snapshot(filter)` method to `BrowserManager` that returns a parsed accessibility tree via CDP `Accessibility.getFullAXTree`. The deprecated `page.accessibility.snapshot()` API no longer exists in modern Playwright.

**Data model:** Define a frozen `AXNodeInfo` dataclass in `tools/browser/manager.py` (or a new `tools/browser/a11y.py` if the module grows) with fields: `id` (int, backendDOMNodeId from CDP), `role` (str), `name` (str), `description` (str, default ''), `properties` (dict, default {}).

**Implementation:** Use `context.new_cdp_session(page)` to create a CDP session, call `Accessibility.getFullAXTree`, flatten the AXNode array, apply the requested filter, and return `list[AXNodeInfo]`. Detach the CDP session after each call.

**Filter modes:**
- `interactive`: keep nodes where properties include focusable=True or role in {button, link, textbox, combobox, checkbox, radio, menuitem, tab}
- `full`: return all non-ignored nodes
- `text`: keep only StaticText role nodes + headings

**Patterns to follow:**
- `BrowserManager` is in `src/owlbear/tools/browser/manager.py`; new method adds to the existing class
- Use `self._context.new_cdp_session(self._page)` for CDP access (available in both launch and CDP modes)
- browser-use (`browser_use/dom/service.py`) validates this approach at scale

**Depends on:** #735 (test task, RED phase)

**AC:**
- [ ] `AXNodeInfo` frozen dataclass with fields: id (int), role (str), name (str), description (str), properties (dict)
- [ ] `BrowserManager.snapshot(filter='full')` returns `list[AXNodeInfo]`
- [ ] `filter='interactive'` returns only focusable/actionable nodes
- [ ] `filter='text'` returns only StaticText + heading nodes
- [ ] CDP session created via `context.new_cdp_session(page)` and detached after each call (no leaked sessions)
- [ ] Works in both launch and CDP modes
- [ ] Tests mock `CDPSession.send()` with canned AXNode responses (see #735)

[[2026-03-10]] Tue 19:58
## Architecture Review
**Verdict:** APPROVED (with refinements applied)

### AC Assessment
| AC Line (original) | Assessment | Action |
|---------------------|------------|--------|
| BrowserManager.snapshot() returns parsed a11y tree | Vague  no return type, no data model, no implementation mechanism | Rewritten: returns `list[AXNodeInfo]` via CDP `getFullAXTree` |
| Filter parameter: interactive `|` full `|` text | Adequate concept but missing filter definitions | Rewritten: each filter mode specifies exact inclusion criteria |
| Output format matches PinchTab's ref schema (id, role, text, selector) | WRONG  `page.accessibility.snapshot()` deprecated; `selector` requires extra CDP call | Rewritten: `AXNodeInfo` dataclass with id/role/name/description/properties; selector deferred |
| Tests with mocked Playwright page | Too vague  doesn't specify what to mock or test | Rewritten: mock `CDPSession.send()` with canned AXNode responses; test each filter + both modes |

### Architecture Notes
- **Implementation mechanism:** CDP `Accessibility.getFullAXTree` via `context.new_cdp_session(page)`. Validated by browser-use (80K stars). Playwright's `page.accessibility.snapshot()` is deprecated/removed.
- **Module placement:** New `snapshot()` method on existing `BrowserManager` in `src/owlbear/tools/browser/manager.py`. `AXNodeInfo` dataclass in same module (or `a11y.py` if it grows).
- **Layer compliance:** `tools/browser/`  correct layer per architecture-standards. No upward imports.
- **Security:** CDP session must be created/detached per call to prevent leaked sessions. Explicit in AC.
- **Pattern consistency:** Follows existing `BrowserManager` public API pattern (`page` property, async methods).
- **Single domain:** Browser tools only  no cross-domain concerns.

### Changes Made
- Rewrote task body with precise AC (7 verifiable criteria) based on a11y-snapshot.md
- Added implementation guidance: CDP approach, data model, filter definitions, patterns to follow
- Created #735: Tests: BrowserManager.snapshot() via CDP (RED phase)  preceding test task for TDD compliance
- Noted dependency: #726 depends on #735 (test-first)

### Dependencies
- Added: #735 (test task, RED phase)  created as preceding TDD task
- Verified: #727 (browser_snapshot tool) depends on #726  downstream, not blocking
- Verified: No circular dependencies

[[2026-03-11]] Wed 09:36
## Test-Writer Notes
- Test file: tests/test_browser_snapshot.py (written under #735)
- Classes: TestFromAC_AXNodeInfo, TestFromAC_SnapshotFull, TestFromAC_SnapshotInteractive, TestFromAC_SnapshotText, TestFromAC_SnapshotCDPSession, TestFromAC_SnapshotBothModes
- Tests per category: happy 8, edge 3, error 1, boundary 7
- Total: 19 tests, all PASS (impl already exists)
- ruff: clean
- AC coverage: all 7 AC lines covered by existing #735 test suite
- Note: RED-phase tests pre-existed from #735; implementation already built. No new tests needed.

[[2026-03-11]] Wed 09:55
## Builder Notes
- Files changed: src/owlbear/tools/browser/manager.py (AXNodeInfo + BrowserManager.snapshot() -- already built under #735)
- Tests: 19 passed (tests/test_browser_snapshot.py), coverage 90% on manager.py
- Lint: ruff clean
- Evidence: All 7 AC lines covered by existing implementation
- Fixes applied: None -- implementation complete from #735

[[2026-03-11]] Wed 10:09
## Review Evidence

### Test Results
- pytest: 19 passed, 0 failed (tests/test_browser_snapshot.py)
- Existing browser manager tests: 33 passed, 0 failed (tests/test_browser_manager.py)
- No regressions from _enter_cdp / _exit_cdp changes

### Lint Results
- ruff: All checks passed (src/owlbear/tools/browser/manager.py, tests/test_browser_snapshot.py)

### Coverage
- manager.py: 90% (uncovered: L86-89 page property guard, L112-113 snapshot not-entered guard, L178-182 CDP connection error -- all defensive guards)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact values checked (field names, counts, roles, IDs, types) |
| Negative/error paths | ADEQUATE | error-on-send, frozen mutation, exclude-ignored, exclude filters; missing not-entered guard |
| Mutation resilience | STRONG | Flipping _INTERACTIVE_ROLES, _TEXT_ROLES, removing finally, inverting filter -- all caught |
| Test independence | STRONG | Each test creates its own mocks via fixtures, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario and outcome |

### Security Review
| Check | Status |
|-------|--------|
| Hardcoded secrets | Clean |
| Injection | Clean -- CDP call uses fixed string |
| Path traversal | N/A |
| Insecure deserialization | Clean |
| Input validation | filter param typed with Literal; CDP response processed safely with .get() |
| Dependency risk | No new deps |
| Secret leakage | Clean |

### TestFromAC Comparison
Test file created in same commit as implementation (single commit d274586). All 6 TestFromAC classes present and intact. No prior version to diff against.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AXNodeInfo frozen dataclass (id, role, name, description, properties) | manager.py L37-46: @dataclasses.dataclass(frozen=True) with correct fields; 4 tests in TestFromAC_AXNodeInfo | PASS |
| BrowserManager.snapshot(filter='full') returns list[AXNodeInfo] | manager.py L95-150; TestFromAC_SnapshotFull 4 tests (count=7, isinstance, excludes ignored, empty) | PASS |
| filter='interactive' returns only focusable/actionable nodes | manager.py L140-142; TestFromAC_SnapshotInteractive 3 tests (roles present, excluded, focusable generic) | PASS |
| filter='text' returns only StaticText + heading nodes | manager.py L143-144; TestFromAC_SnapshotText 3 tests | PASS |
| CDP session created/detached per call (no leaks) | manager.py L118-121 try/finally; TestFromAC_SnapshotCDPSession 3 tests (lifecycle, error detach, two calls) | PASS |
| Works in both launch and CDP modes | TestFromAC_SnapshotBothModes 2 tests; launch uses context mock, CDP uses cdp_context mock | PASS |
| Tests mock CDPSession.send() with canned AXNode responses | All tests use CANNED_AX_TREE fixture or custom canned responses | PASS |

### Verdict: PASS (confidence .93)

[[2026-03-11]] Wed 10:26
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AXNodeInfo frozen dataclass (id, role, name, description, properties) | manager.py L37-46: @dataclasses.dataclass(frozen=True), correct fields; 4 tests in TestFromAC_AXNodeInfo | PASS |
| BrowserManager.snapshot(filter='full') returns list[AXNodeInfo] | manager.py L95-150; TestFromAC_SnapshotFull 4 tests | PASS |
| filter='interactive' returns only focusable/actionable nodes | manager.py L140-142; TestFromAC_SnapshotInteractive 3 tests | PASS |
| filter='text' returns only StaticText + heading nodes | manager.py L143-144; TestFromAC_SnapshotText 3 tests | PASS |
| CDP session created/detached per call (no leaked sessions) | manager.py L118-121 try/finally; TestFromAC_SnapshotCDPSession 3 tests | PASS |
| Works in both launch and CDP modes | TestFromAC_SnapshotBothModes 2 tests | PASS |
| Tests mock CDPSession.send() with canned AXNode responses | All tests use CANNED_AX_TREE fixture | PASS |

### Test Results
- pytest (scoped): 19 passed, 0 failed
- pytest (full): 398 passed, 1 failed (pre-existing test_bootstrap unrelated), 20 skipped
- ruff: clean

### Confidence: .97
### Action: archive
