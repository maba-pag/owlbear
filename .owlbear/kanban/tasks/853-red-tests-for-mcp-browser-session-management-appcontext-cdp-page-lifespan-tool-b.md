---
id: 853
title: 'RED: Tests for mcp-browser session management (AppContext CDP/Page, lifespan,
  tool bodies)'
status: todo
priority: important
created: '2026-04-12T14:03:37.122556+00:00'
updated: '2026-04-13T23:28:20.793531+00:00'
tags:
- phase-2
- scope:mcp-browser
- tdd-red
- archived
- superseded
parent: 837
depends_on:
- 850
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Write failing tests for mcp-browser browser session management.

**Source:** .owlbear/research/837-mcp-browser-session-management.md

**AC:**
- [ ] Tests for AppContext includes CDPConnectionManager and optional Page fields
- [ ] Tests for lifespan: successful CDP connection yields AppContext with cdp+page
- [ ] Tests for lifespan: failed CDP connection yields AppContext with cdp=None, page=None
- [ ] Tests for lifespan cleanup: disconnects CDP and closes page on exit
- [ ] Tests for navigate(): checks allowlist then calls page.goto(url)
- [ ] Tests for click(): calls page.locator(selector).click()
- [ ] Tests for type(): calls page.locator(selector).fill(text)
- [ ] Tests for select(): calls page.locator(selector).select_option(value)
- [ ] Tests for read_text(): calls extract_content(page.content(), page.url)
- [ ] Tests for snapshot(): calls page.aria_snapshot()
- [ ] Tests for all tools: raise ToolError when page is None
- [ ] All tests mock at CDP boundary (no real browser)
- [ ] All tests FAIL on current HEAD
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/837-mcp-browser-session-management.md (validation pass — parent doc §3g covers test strategy for this task)
- Sources: 12 studied (parent doc), 3 high-relevance codebase patterns: test_contentfetcher_impl_830.py (CDP/Page mocks), test_mcp_browser_836.py (_make_mcp_ctx), test_mcp_browser_775.py (lifespan test pattern)
- Recommendation: ~20 tests in tests/test_mcp_browser_session_853.py, organized by AC group. Mock at CDP boundary using _make_mock_page/_make_mock_cdp pattern from test_contentfetcher_impl_830.py. All tests FAIL on current HEAD because AppContext lacks cdp/page, lifespan doesn't connect CDP, and tool bodies are stubs. (confidence: .90)
- Follow-up tasks created: none — this IS the follow-up task from #837 research
- Decision requests: none
- Tier: T1 — autonomous RED phase, no decisions needed

## Challenge Results
- Challenge: FALLBACK — trivial validation pass, test strategy fully defined in parent doc §3g. No recommendation to challenge.

## Validation Evidence
- server.py L22-25: AppContext(allowlist: DomainAllowlist) — no cdp/page fields → AppContext tests FAIL
- server.py L56-61: app_lifespan yields AppContext(allowlist=allowlist) — no CDP connect → lifespan tests FAIL
- server.py L68-107: all 6 tools return stubs → tool body tests FAIL
- cdp.py L43-104: CDPConnectionManager.connect/disconnect exist → mock targets confirmed
- extractor.py L48: extract_content(html, url) exists → read_text mock target confirmed
- Dependency #850 (ctx: Context on tools) at todo — correct ordering, RED tests assume ctx present
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED tests only — one test file for session management |
| Interface clarity | PASS | 13 AC lines, each maps to specific test scenario with mock targets specified |
| Dependency correctness | PASS | depends_on [850] correct — ctx: Context must land before tests can fail for the right reasons (missing CDP/page, not missing ctx param) |
| Module layering | PASS | Test file only, no source changes |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope matching research §3g strategy |
| Premise challenge | PASS | Tests validate session management not yet implemented (confirmed: AppContext lacks cdp/page, lifespan has no CDP, 5/6 tool bodies are stubs) |
| Pattern consistency | PASS | Mock at CDP boundary using _make_mock_page/_make_mock_cdp from test_contentfetcher_impl_830.py, _make_mcp_ctx from test_mcp_browser_775.py |
| Security surface | PASS | Tests only, no new system boundaries |
| Single domain | PASS | scope:mcp-browser only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AppContext includes CDPConnectionManager and optional Page | Verifiable — test dataclass fields | None |
| Lifespan: successful CDP yields AppContext with cdp+page | Verifiable — async test with mock CDPConnectionManager | None |
| Lifespan: failed CDP yields cdp=None, page=None | Verifiable — mock CDPConnectionManager.connect raises | None |
| Lifespan cleanup: disconnects CDP and closes page | Verifiable — assert disconnect/close called on exit | None |
| navigate(): checks allowlist then calls page.goto(url) | Verifiable — mock page.goto, verify call order | None |
| click(): calls page.locator(selector).click() | Verifiable — mock locator chain | None |
| type(): calls page.locator(selector).fill(text) | Verifiable — mock locator chain | None |
| select(): calls page.locator(selector).select_option(value) | Verifiable — mock locator chain | None |
| read_text(): calls extract_content(page.content(), page.url) | Verifiable — mock page.content + patch extract_content | None |
| snapshot(): calls page.aria_snapshot() | Verifiable — mock page.aria_snapshot | None |
| All tools: raise ToolError when page is None | Verifiable — AppContext with page=None, assert ToolError | None |
| All tests mock at CDP boundary | Verifiable — no Playwright imports at test time | None |
| All tests FAIL on current HEAD | Verifiable — pytest run confirms failures | None |

### Codebase Evidence

- server.py L22-25: AppContext(allowlist: DomainAllowlist) — no cdp/page fields
- server.py L56-61: app_lifespan yields AppContext(allowlist=allowlist) — no CDP connection
- server.py L68-107: navigate has allowlist logic, 5 others are stubs returning placeholders
- cdp.py L43-104: CDPConnectionManager.connect/disconnect are the mock targets
- extractor.py L48: extract_content(html, url) is the read_text mock target
- test_contentfetcher_impl_830.py L47-60: _make_mock_page/_make_mock_cdp patterns established
- test_mcp_browser_775.py L46-48: _make_mcp_ctx pattern for lifespan_context wiring

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in current session
- Research challenge was also FALLBACK — test strategy fully defined in parent doc §3g
- Confidence: .93

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 13 AC lines verifiable with established mock patterns. Dependency on #850 correctly declared.
[[2026-04-13]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_browser_session_853.py`

**Classes:**
- `TestFromAC_AppContextFields` — 4 tests (AC1)
- `TestFromAC_LifespanSuccessfulConnection` — 4 tests (AC2)
- `TestFromAC_LifespanFailedConnection` — 2 tests (AC3)
- `TestFromAC_LifespanCleanup` — 3 tests (AC4)
- `TestFromAC_NavigateToolBody` — 3 tests (AC5)
- `TestFromAC_ClickToolBody` — 1 test (AC6)
- `TestFromAC_TypeToolBody` — 1 test (AC7)
- `TestFromAC_SelectToolBody` — 1 test (AC8)
- `TestFromAC_ReadTextToolBody` — 1 test (AC9)
- `TestFromAC_SnapshotToolBody` — 1 test (AC10)
- `TestFromAC_ToolErrorWhenNoPage` — 6 tests (AC11)

**Test counts per category:**
- Happy path: 8 (lifespan success, tool body delegations)
- Edge/boundary: 3 (cleanup skipped on no-CDP, blocked domain no goto call, lifespan failure graceful degrade)
- Error paths: 10 (ToolError on blocked domain, ToolError×6 when page=None, lifespan connect failure)
- Structural: 6 (AppContext field presence/defaults)

**Total: 27 tests, all FAIL** — pytest exit 1, 0 passed, 27 failed.

**Failure root causes on current HEAD:**
1. `AppContext` lacks `cdp`/`page` fields → `AttributeError`/`TypeError` in helpers and AC1 tests.
2. `CDPConnectionManager` not imported in `server.py` → `AttributeError` on `patch` for all lifespan tests.
3. Tool functions lack `ctx` param; tool bodies are stubs → `TypeError` for all tool-body and ToolError-on-no-page tests.

**AC coverage table:**

| AC Line | Tests |
|---------|-------|
| AppContext cdp+page fields | test_appcontext_cdp_defaults_to_none, test_appcontext_page_defaults_to_none, test_appcontext_accepts_cdp_kwarg, test_appcontext_accepts_page_kwarg |
| Lifespan success: cdp+page set | test_lifespan_sets_cdp_on_successful_connect, test_lifespan_sets_page_on_successful_connect, test_lifespan_calls_cdp_connect, test_lifespan_calls_new_page |
| Lifespan failed: cdp=None, page=None | test_lifespan_sets_cdp_none_on_failed_connect, test_lifespan_sets_page_none_on_failed_connect |
| Lifespan cleanup disconnect+close | test_lifespan_cleanup_closes_page, test_lifespan_cleanup_disconnects_cdp, test_lifespan_cleanup_skipped_when_connect_failed |
| navigate() allowlist+page.goto | test_navigate_calls_page_goto_with_allowed_url, test_navigate_raises_tool_error_for_blocked_domain, test_navigate_does_not_call_goto_when_blocked |
| click() locator.click | test_click_calls_locator_click |
| type() locator.fill | test_type_calls_locator_fill |
| select() locator.select_option | test_select_calls_locator_select_option |
| read_text() extract_content | test_read_text_calls_extract_content_with_page_html_and_url |
| snapshot() aria_snapshot | test_snapshot_calls_aria_snapshot |
| ToolError when page=None (×6 tools) | test_navigate/click/type/select/read_text/snapshot_raises_when_page_none |
| Mock at CDP boundary | All tests — no real Playwright/browser imports |

**Mock strategy:** `_make_mock_cdp` (CDPConnectionManager boundary), `_make_mock_page` (Playwright Page), `_make_mcp_ctx_with_page`/`_make_mcp_ctx_no_page` (AppContext wire-up). Patches: `owlbear_mcp_browser.server.CDPConnectionManager`, `owlbear_mcp_browser.server.extract_content`.
[[2026-04-13]]
## Builder Notes

### Verdict: REJECT → todo
**Reason:** Mutually exclusive `TestFromAC_*` contracts between tasks 836 and 853.

### Conflict
| Source | Test Class | Input | Expected Output |
|--------|-----------|-------|----------------|
| `test_mcp_browser_836.py` | `TestFromAC_AllToolsCallableWithCtx` | `AppContext(page=None)` | `isinstance(result, str)` — no error |
| `test_mcp_browser_session_853.py` | `TestFromAC_ToolErrorWhenNoPage` | `AppContext(page=None)` | `ToolError` raised |

Both test classes use actual `AppContext` dataclass instances with `page=None`. Same function, same input type, contradictory expected behavior. No implementation can satisfy both.

### Evidence
- 836 `_make_mcp_ctx()` → `AppContext(allowlist=DomainAllowlist(domains=[]))` (page=None by default)
- 836 tests: `result = await click(ctx, "#btn"); assert isinstance(result, str)` — pass today via backward-compat branch
- 853 `_make_mcp_ctx_no_page()` → `AppContext(allowlist=..., cdp=None, page=None)`
- 853 tests: `with pytest.raises(ToolError): await click(ctx, "#btn")`
- Removing the backward-compat branches → 853 AC11 passes but 5 tests in `TestFromAC_AllToolsCallableWithCtx` (836) break
- Keeping the backward-compat branches → 836 tests pass but 5 tests in `TestFromAC_ToolErrorWhenNoPage` (853) fail

### Test-writer action required
Update `tests/test_mcp_browser_836.py` class `TestFromAC_AllToolsCallableWithCtx` — the 5 tests for click/type_input/select/read_text/snapshot must use an AppContext WITH a mock page (not page=None). The "callable with ctx" contract only requires a valid ctx, not an empty one. Once these tests no longer assert string-return from page=None, the builder can implement 853 AC11.

Specifically:
- `test_click_called_with_ctx_and_selector`
- `test_type_input_called_with_ctx_selector_and_text`
- `test_select_called_with_ctx_selector_and_value`
- `test_read_text_called_with_ctx`
- `test_snapshot_called_with_ctx`

All 5 should be updated to inject a mock page into the AppContext lifespan context, verifying the tools are callable — not that they silently swallow missing-page errors.

[[2026-04-14]]
## Archived — Superseded by CDP Pivot
CDP session management tests designed for Edge CDP approach with `CDPConnectionManager`, `page.goto()` via CDP port. CDP blocked by Group Policy. New architecture uses Playwright `launch_persistent_context()` + SSO extension — different session model entirely.