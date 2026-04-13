---
id: 854
title: 'GREEN: Implement mcp-browser session management (AppContext CDP/Page, lifespan,
  tool bodies)'
status: backlog
priority: important
created: '2026-04-12T14:03:37.150978+00:00'
updated: '2026-04-12T15:49:07.913551+00:00'
tags:
- phase-2
- scope:mcp-browser
- tdd-green
parent: 837
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Implement browser session management to make RED tests pass.

**Source:** .owlbear/research/837-mcp-browser-session-management.md

**AC:**
- [ ] AppContext includes cdp: CDPConnectionManager | None and page: Any (optional Page)
- [ ] Lifespan opens CDP connection to running Edge via BROWSER_CDP_PORT env (default 9222)
- [ ] Lifespan degrades gracefully if no Edge running (cdp=None, page=None)
- [ ] Lifespan cleanup closes page and disconnects CDP in finally block
- [ ] navigate() checks allowlist via ctx, then calls page.goto(url)
- [ ] click() calls page.locator(selector).click()
- [ ] type() calls page.locator(selector).fill(text)
- [ ] select() calls page.locator(selector).select_option(value)
- [ ] read_text() calls extract_content(await page.content(), page.url)
- [ ] snapshot() calls page.aria_snapshot()
- [ ] All tools raise ToolError("No browser session") when page is None
- [ ] ruff clean
- [ ] All RED tests pass
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/854-mcp-browser-session-green.md (validation pass of parent doc)
- Sources: 6 studied, 5 high-relevance (≥.85)
- Recommendation: Follow parent research §3c-§3e exactly — extend AppContext with cdp+page, lifespan attach-or-skip CDP, replace tool stubs with Playwright locator API calls, extract_content for read_text, aria_snapshot for snapshot. (confidence: .88)
- Follow-up tasks created: none — #853 (RED) and #855 (playwright bump) already exist
- Decision requests: none
- Blockers: #850 (ctx refactor GREEN, todo) and #853 (RED tests, research) must complete before builder can start
- Challenge: FALLBACK — implementation approach dictated by parent research + architect approval
- Tier: T1 — autonomous, within approved Phase 2 architecture