---
id: 853
title: 'RED: Tests for mcp-browser session management (AppContext CDP/Page, lifespan,
  tool bodies)'
status: backlog
priority: important
created: '2026-04-12T14:03:37.122556+00:00'
updated: '2026-04-12T15:48:48.472343+00:00'
tags:
- phase-2
- scope:mcp-browser
- tdd-red
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