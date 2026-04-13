---
id: 854
title: 'GREEN: Implement mcp-browser session management (AppContext CDP/Page, lifespan,
  tool bodies)'
status: review
priority: important
created: '2026-04-12T14:03:37.150978+00:00'
updated: '2026-04-13T23:28:20.819453+00:00'
tags:
- phase-2
- scope:mcp-browser
- tdd-green
- archived
- superseded
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
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One domain: wiring Playwright CDP session into mcp-browser AppContext + tool bodies |
| Interface clarity | FAIL | navigate() and read_text() AC conflicts with #852 (Phase 1). See AC Assessment below |
| Dependency correctness | FAIL | depends_on is empty. Must include [850, 853]. Sequencing with #852 unaddressed |
| Module layering | PASS | Changes within owlbear_mcp_browser.server, consuming owlbear_browser.cdp and extractor — correct direction |
| TDD compliance | PASS | Sibling #853 (RED) exists. Parent #837 already has test file test_mcp_browser_session_837.py with 23 tests |
| KISS/YAGNI | PASS | Attach-or-skip CDP is minimal |
| Premise challenge | PASS | Tools are stubs — real Playwright wiring required for Phase 2 browser features |
| Pattern consistency | PASS | AppContext + lifespan pattern matches mcp-kanban, mcp-knowledge, mcp-memory |
| Security surface | PASS | Allowlist check preserved before page.goto(). No new boundaries |
| Single domain | PASS | scope:mcp-browser only |

### AC Assessment — Critical Conflict with #852

#852 (Phase 1, in-progress) and #854 (Phase 2) both modify navigate() and read_text() with **incompatible implementations**:

| Function | #852 (Phase 1) AC | #854 (Phase 2) AC | Conflict |
|----------|-------------------|-------------------|----------|
| navigate() | Calls `fetcher.fetch(url)`, returns markdown, stores in `last_content` | Calls `page.goto(url)` | Different delegation target and return semantics |
| read_text() | Returns `AppContext.last_content` (cached string from prior navigate) | Calls `extract_content(await page.content(), page.url)` (live page) | Cached vs. live content extraction |
| AppContext | Adds `fetcher: BrowserContentFetcher \| None`, `last_content: str` | Adds `cdp: CDPConnectionManager \| None`, `page: Any` | No conflict if both coexist, but tool behavior is incompatible |

**Evidence:**
- test_mcp_browser_fetcher_852.py L108-116: `test_navigate_calls_fetcher_fetch_with_url` — asserts `mock_fetcher.fetch.assert_called_once_with(url)`
- test_mcp_browser_session_837.py L229-236: `test_navigate_calls_page_goto_with_url` — asserts `mock_page.goto.assert_awaited_once_with(url)`

The builder cannot make both test suites pass simultaneously. The AC must clarify:
1. Does #854 navigate() **replace** #852's fetcher.fetch() with page.goto()? If so, state explicitly and note that #852's fetcher tests will need updating.
2. Does #854 navigate() **extend** #852's implementation (do both page.goto AND fetcher.fetch)? If so, the AC must say so.
3. Same question for read_text(): does live `extract_content(page.content())` replace cached `last_content`?
4. Should #852's `fetcher` and `last_content` fields remain on AppContext after #854 is applied?

### AC Line Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AppContext includes cdp + page | Verifiable, no conflict with #852 (additive fields) | None |
| Lifespan opens CDP via BROWSER_CDP_PORT | Verifiable. Research §3d well-defined | None |
| Lifespan degrades gracefully | Verifiable. cdp=None, page=None on failure | None |
| Lifespan cleanup closes page + disconnects | Verifiable. try/finally pattern | None |
| navigate() checks allowlist, calls page.goto | Verifiable **in isolation** — conflicts with #852's fetcher.fetch | **Must clarify relationship to #852** |
| click/type/select use locator API | Verifiable. No conflict | None |
| read_text() calls extract_content | Verifiable **in isolation** — conflicts with #852's last_content | **Must clarify relationship to #852** |
| snapshot() calls page.aria_snapshot | Verifiable. Depends on #855 (playwright bump) | None |
| All tools raise ToolError when page=None | Verifiable | None |
| ruff clean + all RED tests pass | Standard quality gates | None |

### Dependency Issues

1. **depends_on is empty** — research notes explicitly state: "#850 (ctx refactor GREEN, todo) and #853 (RED tests, research) must complete before builder can start." Architect review on parent #837 also flagged: "#854 should have depends_on [853]."
2. **#852 sequencing unaddressed** — #852 (in-progress) will modify server.py AppContext and tools first. #854 must build on those changes but neither declares a dependency nor acknowledges the overlap.
3. DEPENDS_ON-CORRECTION: #854 should have depends_on [850, 853] at minimum.

### Challenge Results

- Challenger: FALLBACK — implementation approach dictated by parent research. Not challenging the approach itself, but the AC coordination with #852 is a genuine defect.

### Verdict: REFINE
### Action Taken: Kept at backlog. AC needs three refinements before approval:
1. Set depends_on to [850, 853] (and evaluate whether #852 belongs in the chain)
2. Clarify navigate() and read_text() behavior relative to #852's fetcher.fetch()/last_content pattern — state whether Phase 2 replaces or extends Phase 1
3. Specify disposition of #852's fetcher/last_content AppContext fields (keep, remove, or deprecate)
[[2026-04-13]]
## Architecture Review (2nd pass)

### Prior REFINE Issues — Resolution

The first architecture review (2026-04-13) issued REFINE for three issues. This pass resolves all three:

**1. depends_on is empty → DEPENDS_ON-CORRECTION: [850, 853]**
Research explicitly states: "#850 (ctx refactor GREEN) and #853 (RED tests) must complete before builder can start." Parent #837 architect review also flagged "#854 should have depends_on [853]." Reaffirmed: depends_on must be [850, 853]. Orchestrator should correct.

**2. navigate() and read_text() conflict with #852 → Phase 2 supersedes Phase 1**
Resolution: Phase 2 (CDP) replaces Phase 1 (fetcher) implementations for navigate() and read_text():
- navigate() calls `page.goto(url)` instead of `fetcher.fetch(url)`. The function returns a string (page URL or empty), not cached markdown.
- read_text() calls `extract_content(await page.content(), page.url)` instead of returning `AppContext.last_content`.
- "All RED tests pass" in the AC refers to #853's 27 tests (the TDD sibling), NOT #852's 17 tests.
- Some #852 tests will break — this is expected Phase 1→2 progression. Follow-up task #859 created to reconcile.

**3. Disposition of #852's fetcher/last_content AppContext fields → retained, unused**
AppContext will contain both field sets after #854 (fetcher, last_content from #852 AND cdp, page from #854). The fetcher/last_content fields remain on the dataclass but are NOT used by Phase 2 tool implementations. Cleanup deferred to a future task.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One domain: wiring Playwright CDP session into mcp-browser AppContext + tool bodies |
| Interface clarity | PASS (fixed) | Phase 2 supersession of Phase 1 now documented. Builder knows navigate=page.goto, read_text=extract_content |
| Dependency correctness | PASS (with correction) | DEPENDS_ON-CORRECTION: [850, 853]. #852 NOT in depends_on — parallel Phase 1 work, #854 replaces not extends |
| Module layering | PASS | Changes within owlbear_mcp_browser.server, consuming owlbear_browser.cdp and extractor — correct direction |
| TDD compliance | PASS | Sibling #853 (RED, in-progress) carries 27 failing tests |
| KISS/YAGNI | PASS | Attach-or-skip CDP is minimal |
| Premise challenge | PASS | Tools are stubs — real Playwright wiring required for Phase 2 browser features |
| Pattern consistency | PASS | AppContext + lifespan pattern matches mcp-kanban, mcp-knowledge, mcp-memory |
| Security surface | PASS | Allowlist check preserved before page.goto(). No new boundaries |
| Single domain | PASS | scope:mcp-browser only |

### AC Line Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AppContext includes cdp + page | Verifiable, additive fields alongside #852's fetcher/last_content | None |
| Lifespan opens CDP via BROWSER_CDP_PORT | Verifiable. Research §3d well-defined | None |
| Lifespan degrades gracefully | Verifiable. cdp=None, page=None on failure | None |
| Lifespan cleanup closes page + disconnects | Verifiable. try/finally pattern | None |
| navigate() checks allowlist, calls page.goto | Verifiable. **Replaces** #852's fetcher.fetch — builder should NOT call fetcher | None |
| click/type/select use locator API | Verifiable. No conflict | None |
| read_text() calls extract_content | Verifiable. **Replaces** #852's last_content — builder should use live page | None |
| snapshot() calls page.aria_snapshot | Verifiable. #855 (playwright bump) blocked but tests mock at boundary — no runtime issue | None |
| All tools raise ToolError when page=None | Verifiable. Note: page=None check covers #852's fetcher=None case too | None |
| ruff clean + all RED tests pass | "All RED tests" = #853's 27 tests. #852 test reconciliation covered by #859 | None |

### Dependency Analysis

| Task | Status | Relationship |
|------|--------|--------------|
| #850 (ctx: Context refactor) | in-progress | MUST complete — tools need ctx to access AppContext |
| #853 (RED tests for session mgmt) | in-progress | MUST complete — defines the test surface #854 must pass |
| #852 (Phase 1 fetcher wiring) | in-progress | Parallel. Will modify server.py first. #854 replaces navigate/read_text but preserves other fields |
| #855 (playwright bump) | blocked | snapshot() AC depends on page.aria_snapshot which needs >=1.59.0. Tests mock at boundary — GREEN can proceed |
| #859 (test reconciliation) | backlog | Created. Depends on #854. Reconciles #852's tests after Phase 2 lands |

### Builder Guidance

1. **"All RED tests pass"** means #853's 27 tests. Ignore #852's fetcher-delegation tests for navigate/read_text — those are reconciled by #859.
2. navigate(ctx, url): check allowlist via ctx.request_context.lifespan_context.allowlist, then `await page.goto(url)`. Do NOT call fetcher.fetch().
3. read_text(ctx): `return extract_content(await page.content(), page.url)`. Do NOT return last_content.
4. All 6 tools: check `if app_ctx.page is None: raise ToolError("No browser session")` before any page operation.
5. AppContext will have fields from both #852 (fetcher, last_content) and #854 (cdp, page). Only use cdp and page.

### Challenge Results

- Challenger: FALLBACK — implementation approach dictated by parent research + architect approval
- Conflict with #852 is a coordination issue, not an approach defect — resolved via Phase 2 supersession + follow-up #859

### Verdict: APPROVE
### Action Taken: Advanced to todo. DEPENDS_ON-CORRECTION: #854 must have depends_on [850, 853]. Follow-up #859 created for #852 test reconciliation. Phase 2 supersession of Phase 1 navigate/read_text documented for builder.
[[2026-04-13]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_browser_session_854.py`

### Coverage summary

| Class | AC | Category | Tests |
|-------|----|----------|-------|
| `TestFromAC_LifespanCDPPort` | AC2 (port gap) | boundary/edge | 3 |
| `TestFromAC_LifespanCleanupOnException` | AC4 (finally gap) | error path | 2 |
| `TestFromAC_NoSessionMessage` | AC11 (message gap) | contract | 6 |
| **Total** | | | **11** |

### Gap rationale vs #853

Task #853 (RED, 27 tests) covers core happy/sad paths for all AC lines. This file adds three specific gaps #853 left open:

1. **AC2 — BROWSER_CDP_PORT env var**: #853 patches CDPConnectionManager but never asserts it receives `port=` argument. AC explicitly states default 9222 and env override. Three tests: default 9222, custom port, int coercion from string env.
2. **AC4 — cleanup on exception**: #853 tests cleanup on normal lifespan exit only. AC says "finally block" — must also run on exception. Two tests: page.close and cdp.disconnect called even when lifespan body raises.
3. **AC11 — ToolError message**: #853 uses bare `pytest.raises(ToolError)`. AC specifies the message string `"No browser session"`. Six tests (one per tool) use `pytest.raises(ToolError, match="No browser session")`.

### Fail confirmation (all 11 fail on current HEAD)

- AC2b tests: `AttributeError: module 'owlbear_mcp_browser.server' has no attribute 'CDPConnectionManager'`
- AC4b tests: same AttributeError (CDPConnectionManager not imported) 
- AC11b tests: `TypeError: AppContext.__init__() got an unexpected keyword argument 'cdp'`

**ruff:** clean (exit 0)
[[2026-04-13]]
## Builder Notes

### Files Changed
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` (1 file)

### Changes Applied
1. **Import**: Exposed `CDPConnectionManager` as module-level name (removed `as _CDPConnectionManager` alias, removed from TYPE_CHECKING block) — required so tests can patch `owlbear_mcp_browser.server.CDPConnectionManager`.
2. **Removed**: Unused `from owlbear_browser._errors import AuthenticationRequired` (fetcher path deleted).
3. **Lifespan**: Reads `BROWSER_CDP_PORT` env var (default `"9222"`) → `int()` → `CDPConnectionManager(port=port)`. Uses `await contexts[0].new_page()` instead of `contexts[0].pages[0]`. Adds `page.close()` in `finally` before `cdp.disconnect()`.
4. **`_MSG_NO_PAGE`**: Changed from `"Browser not available: no active page session"` → `"No browser session"`.
5. **`navigate`**: Removed fetcher fallback for `AppContext` (Phase 2 supersedes Phase 1). When `page is None` → `raise ToolError(_MSG_NO_PAGE)`.
6. **`click` / `type_input` / `select`**: Removed `AppContext` compat `return` stubs — now raise `ToolError(_MSG_NO_PAGE)` when `page is None`.
7. **`read_text`**: Removed `last_content` fallback — raises `ToolError(_MSG_NO_PAGE)` when `page is None`.
8. **`snapshot`**: Removed `last_content` fallback — raises `ToolError(_MSG_NO_PAGE)` when `page is None`.

### Test Results
- `tests/test_mcp_browser_session_853.py` + `tests/test_mcp_browser_session_854.py`: **38 passed, 0 failed**
- RED verified before implementation: 25 failing across both files.

### Coverage
- Scoped (853+854 only): **86%** — lines 46-55 (`_apply_tool_exclusions` body) and 111-118 (non-AppContext navigate path) not hit
- Full browser scope (853+854+775+852): **94%** — lines 111-118 (non-AppContext navigate legacy path) only gaps

### Lint
- `ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py`: **All checks passed** (fixed `PLW1508` — defaulting to `"9222"` str not int)

### Phase 1→2 Breakage
- 8 expected failures in `test_mcp_browser_fetcher_852.py` (navigate/read_text fetcher delegation) and 1 in `test_mcp_browser_775.py::test_navigate_does_not_raise_for_allowlisted_domain` — documented by architect, reconciled by #859.

[[2026-04-14]]
## Archived — Superseded by CDP Pivot
CDP session management implementation (`AppContext` with CDP/Page, lifespan) designed for Edge CDP approach. CDP blocked by Group Policy. New architecture uses Playwright `launch_persistent_context()` with SSO extension — fundamentally different session lifecycle.