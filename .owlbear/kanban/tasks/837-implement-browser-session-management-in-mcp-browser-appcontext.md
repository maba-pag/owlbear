---
id: 837
title: Implement browser session management in mcp-browser AppContext
status: in-progress
priority: important
created: '2026-04-11T15:28:49.551640+00:00'
updated: '2026-04-12T17:07:18.729466+00:00'
tags:
- phase-2
- scope:mcp-browser
parent: 751
depends_on:
- 771
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Add browser session state to mcp-browser AppContext: CDPConnectionManager and Playwright Page lifecycle.

**Source:** .owlbear/research/771-mcp-browser-server.md §3f, .owlbear/research/playwright-browser-integration-v2.md

**Why:** Current tool bodies are stubs returning placeholder values. Full browser interaction requires a live Playwright Page object managed through AppContext. The lifespan function should open a CDP connection and yield a page; cleanup should disconnect and terminate the browser subprocess.

**AC:**
- [ ] AppContext includes CDPConnectionManager and optional Page fields
- [ ] Lifespan opens CDP connection to running Edge (or fails gracefully)
- [ ] Lifespan cleanup disconnects browser and terminates subprocess
- [ ] navigate() uses Page.goto()
- [ ] click/type/select use Page locator methods
- [ ] read_text uses owlbear_browser.extract_content()
- [ ] snapshot returns accessibility tree as markdown
- [ ] Tests mock Playwright at CDP boundary
- [ ] ruff clean
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/837-mcp-browser-session-management.md
- Sources: 12 studied, 8 high-relevance (≥.85)
- Recommendation: Attach-or-skip CDP connection + shared page model (confidence: .85)
  - Option C: Lifespan attempts CDP connect; degrades gracefully if no Edge running
  - Shared page in AppContext for interactive tool workflow (navigate → click → read)
  - page.aria_snapshot() for snapshot tool (requires Playwright ≥1.59)
  - Locator-based API for click/type/select (Playwright best practice)
  - extract_content(html, url) for read_text (reuses existing extractor)
- Blocker: Task #836 (ctx: Context refactor) must complete first — tools need ctx to access AppContext
- Follow-up tasks created: #853 (RED tests), #854 (GREEN impl), #855 (playwright version bump)
- Decision requests: none
- Challenge: FALLBACK — architecture dictated by existing patterns
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single domain: wiring Playwright/CDP into mcp-browser AppContext. Tool implementations are tightly coupled to the same AppContext state |
| Interface clarity | PASS | Each AC line maps to a specific Playwright API call. Tool signatures clear from existing stubs in server.py |
| Dependency correctness | FAIL | depends_on [771] invalid (task deleted). Research doc explicitly blocks on #836. See DEPENDS_ON-CORRECTION below |
| Module layering | PASS | Changes within owlbear_mcp_browser.server, consuming owlbear_browser.cdp and owlbear_browser.extractor — correct dependency direction |
| TDD compliance | PASS | Children #853 (RED) and #854 (GREEN) carry TDD decomposition |
| KISS/YAGNI | PASS | Attach-or-skip (Option C) is minimal. No subprocess management in MCP server |
| Premise challenge | PASS | Stubs currently return placeholder values — real Playwright wiring is necessary for Phase 2 browser tools |
| Pattern consistency | PASS | Identical AppContext + lifespan pattern used by mcp-kanban, mcp-knowledge, mcp-memory |
| Security surface | PASS | navigate() preserves existing allowlist check before page.goto(). No new security boundaries |
| Single domain | PASS | scope:mcp-browser only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| app_lifespan CDP connect | No Edge running | CDPConnectionError | Yes — degrade to cdp=None, page=None | Tools return ToolError |
| Tool body (any) | page is None | ToolError | Yes — AC requires check | Clear error message |
| page.goto | Network error | Playwright TimeoutError | No — not in AC | Unhandled propagation |
| page crashed | Page closed mid-session | Playwright error | Partial — page.is_closed() mitigation noted in research but not in AC | Tools fail until restart |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AppContext includes CDPConnectionManager and optional Page fields | Verifiable. Research §3c defines exact dataclass | None |
| Lifespan opens CDP connection to running Edge (or fails gracefully) | Verifiable. Option C well-defined in research §3a/§3d | None |
| Lifespan cleanup disconnects browser and terminates subprocess | Verifiable. Research §3d shows finally block pattern | Subprocess termination N/A for Option C (attach-only) — AC wording slightly misleading but acceptable |
| navigate() uses Page.goto() | Verifiable. Preserves allowlist check from #836 | None |
| click/type/select use Page locator methods | Verifiable. Research §3e maps to specific Playwright APIs | None |
| read_text uses owlbear_browser.extract_content() | Verifiable. extract_content(html, url) exists at extractor.py:48 | None |
| snapshot returns accessibility tree as markdown | Verifiable. page.aria_snapshot() in Playwright ≥1.59. Depends on #855 | None |
| Tests mock Playwright at CDP boundary | Verifiable. Test approach guideline — matches existing test_contentfetcher pattern | None |
| ruff clean | Standard quality gate | None |

### Codebase Evidence

- server.py:22-25: AppContext(allowlist: DomainAllowlist) — will be extended with cdp + page fields
- server.py:51-58: app_lifespan already wired to FastMCP — CDP connect logic inserts naturally
- cdp.py:43-104: CDPConnectionManager with connect/disconnect/async-context-manager — ready for use
- extractor.py:48-74: extract_content(html, url) — exact signature match for read_text tool
- Locator-based API (page.locator().click/fill/select_option) is current Playwright best practice

### Challenge Results

- Challenger: FALLBACK — no challenger agent available
- Architecture follows established patterns across 3 other MCP servers; low controversy

### Dependency Corrections

DEPENDS_ON-CORRECTION: task #837 should have depends_on [836] (not [771] which no longer exists; research explicitly states "#836 must complete first")

DEPENDS_ON-CORRECTION: task #854 should have depends_on [853] (GREEN must follow RED)

### Notes

- Children #853/#854/#855 carry the TDD decomposition. Pipeline processes children; #837 completes when children are done.
- Minor gap: page.is_closed() check noted in research (§4 Risk) but absent from AC. Recommend adding to #854 AC as defensive check.
- AC3 "terminates subprocess" is slightly misleading for Option C (attach-only, no subprocess). Not blocking — builder will interpret correctly from research context.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Flagged two DEPENDS_ON-CORRECTIONs for orchestrator: #837 depends_on [836], #854 depends_on [853].
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_session_837.py
- Classes: TestFromAC_AppContextFields, TestFromAC_LifespanCDPConnect, TestFromAC_LifespanCleanup, TestFromAC_NavigateTool, TestFromAC_ClickTool, TestFromAC_TypeTool, TestFromAC_SelectTool, TestFromAC_ReadTextTool, TestFromAC_SnapshotTool
- Tests per category: happy 9, edge 0, error 8, boundary 6
- Total: 23 tests, all FAIL
- ruff: clean

AC Coverage:
| AC Line | Tests |
|---------|-------|
| AppContext includes CDPConnectionManager + optional Page fields | 4 (field presence, construction with None) |
| Lifespan opens CDP or degrades gracefully | 4 (cdp/page set on success; cdp/page=None on failure) |
| Lifespan cleanup disconnects browser | 2 (clean exit + exception exit) |
| navigate() uses Page.goto() | 3 (goto called, allowlist blockage preserved, page=None guard) |
| click() uses page.locator().click() | 2 (called correctly, page=None guard) |
| type_input() uses page.locator().fill() | 2 (called correctly, page=None guard) |
| select() uses page.locator().select_option() | 2 (called correctly, page=None guard) |
| read_text() uses extract_content(html, url) | 2 (extract_content patched+verified, page=None guard) |
| snapshot() uses page.aria_snapshot() | 2 (called+return verified, page=None guard) |

Failure causes at current HEAD:
- AppContext missing cdp/page fields → AssertionError (AC1 tests)
- app_lifespan does not import/use CDPConnectionManager → AssertionError (AC2/AC3 tests)
- Tools have no ctx parameter → TypeError (all tool tests)

Mocking: CDP boundary patched at `owlbear_browser.cdp.playwright_connect_over_cdp`; tools use SimpleNamespace lifespan_context.

Commit: f0867899 (branch dev)