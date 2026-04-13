---
id: 857
title: 'GREEN: Wire BrowserContentFetcher into MCP browser navigate/read_text'
status: in-progress
priority: important
created: '2026-04-12T15:15:50.852819+00:00'
updated: '2026-04-13T23:29:43.551674+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-green
parent: 852
depends_on:
- 856
- 842
- 850
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Implement wiring of BrowserContentFetcher into MCP browser server tools. RED partner: #856.

See `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` for full analysis.

## Acceptance Criteria

1. `AppContext` has `fetcher: BrowserContentFetcher | None = None` and `last_content: str = ""` fields.
2. `app_lifespan()` creates CDPConnectionManager + BrowserContentFetcher (guarded, fallback to None on failure).
3. `navigate(ctx, url)` calls `fetcher.fetch(url)`, stores result in `ctx.request_context.lifespan_context.last_content`, returns the markdown content.
4. `navigate()` catches `AuthenticationRequired` → `ToolError` with descriptive message.
5. `navigate()` returns `ToolError` if fetcher is None.
6. `read_text(ctx)` returns `ctx.request_context.lifespan_context.last_content`.
7. All #856 RED tests pass.
8. ruff clean.

## Notes

- Depends on #856 (RED tests), #842 (BrowserContentFetcher impl), #850 (ctx: Context in tools).
- `import` from `owlbear_browser` for `BrowserContentFetcher` and `AuthenticationRequired`.
- owlbear-mcp-browser pyproject.toml already depends on owlbear-browser (workspace dep).

**Affected files:** `serve/mcp-browser/src/owlbear_mcp_browser/server.py`
[[2026-04-13]]
## Research

**Validation pass** — existing research doc `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` covers all design decisions for this task. Verified against current codebase.

### Codebase State

| AC | Status | Evidence |
|----|--------|----------|
| AC1: AppContext fields | ✅ Done | `server.py` L26-28: `fetcher: BrowserContentFetcher \| None = None`, `last_content: str = ""` |
| AC2: Lifespan creates CDPConnectionManager + BrowserContentFetcher | ❌ Gap | `server.py` L39-45: lifespan still yields `AppContext(allowlist=allowlist)` only |
| AC3: navigate() calls fetcher.fetch(), stores, returns | ✅ Done | `server.py` L58-67 |
| AC4: AuthenticationRequired → ToolError | ✅ Done | `server.py` L63-65 |
| AC5: fetcher=None → ToolError | ✅ Done | `server.py` L55-57 |
| AC6: read_text() returns last_content | ✅ Done | `server.py` L74-76 |
| AC7: #856 RED tests pass | ✅ 24/24 pass | 1 regression in test_mcp_browser_775 — tracked in #852 builder notes, needs mock fetcher |
| AC8: ruff clean | ✅ Clean | No lint errors |

### Remaining Implementation

1. **AC2 lifespan wiring** — create `CDPConnectionManager()`, call `await cdp.connect()` (guarded by try/except for `CDPConnectionError` + general exceptions), create `BrowserContentFetcher(cdp)`. Fallback: fetcher stays None.
2. **Lifespan cleanup** — `CDPConnectionManager.disconnect()` in cleanup path (CDPConnectionManager supports `async with` via `__aenter__/__aexit__`, or manual disconnect).
3. **775 test regression** — `test_navigate_does_not_raise_for_allowlisted_domain` needs mock fetcher. Fix is described in #852 builder notes.

### Sources

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` §3a-3e | .95 |
| 2 | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` (current) | .95 |
| 3 | `serve/browser/src/owlbear_browser/cdp.py` L53-95 (CDPConnectionManager init/connect/disconnect) | .90 |
| 4 | `tests/test_mcp_browser_fetcher_852.py` (24 RED tests) | .90 |
| 5 | #852 builder notes (implementation details + 775 regression fix) | .85 |

### Tier & Decision

T1 — autonomous. No decision requests needed. All design decisions validated by parent research. Confidence: .90.

### Follow-up Tasks

None — task has concrete AC, implementation path is clear, and the 775 regression fix is already documented.
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: wire BrowserContentFetcher into MCP browser lifespan + tools |
| Interface clarity | PASS | AC specifies exact fields, method calls, exception handling, error conditions. Each AC line maps to RED tests in test_mcp_browser_fetcher_852.py |
| Dependency correctness | PASS | #842 (BrowserContentFetcher impl): task archived but deliverables exist in serve/browser/src/owlbear_browser/fetcher.py. #856 (RED tests): todo — correctly listed. #850 (ctx: Context): in-progress — deliverables partially exist |
| Module layering | PASS | mcp-browser depends on owlbear-browser (workspace dep confirmed in pyproject.toml). Imports: AuthenticationRequired, BrowserContentFetcher from owlbear_browser — correct direction, no upward imports |
| TDD compliance | PASS | #856 is the RED partner with 17 tests in test_mcp_browser_fetcher_852.py covering all behavioral AC |
| KISS/YAGNI | PASS | Minimal wiring — connects existing CDPConnectionManager + BrowserContentFetcher into existing lifespan pattern. No speculative features |
| Premise challenge | PASS | MCP browser server is a stub without this wiring. BrowserContentFetcher delegation is the mechanism for authenticated web content extraction |
| Pattern consistency | PASS | Follows established ctx: Context + lifespan_context pattern from mcp-kanban, mcp-knowledge, mcp-memory servers. ToolError for tool-level errors matches convention |
| Security surface | PASS | DomainAllowlist check preserved (already in place). AuthenticationRequired caught. No new user-input boundaries |
| Single domain | PASS | scope:mcp-browser only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: AppContext fields | Verifiable, already implemented (server.py L30-31) | None |
| AC2: app_lifespan creates CDPConnectionManager + BrowserContentFetcher | Verifiable. **REFINED**: must also disconnect CDPConnectionManager in finally block after yield | See refinement below |
| AC3: navigate() calls fetcher.fetch, stores, returns | Verifiable, already implemented (server.py L85-90) | None |
| AC4: AuthenticationRequired → ToolError | Verifiable, already implemented (server.py L87-89) | None |
| AC5: fetcher=None → ToolError | Verifiable. Current code returns "" (server.py L83-84) but RED tests expect ToolError (test_navigate_fetcher_none_raises_tool_error). Builder must fix this | None — AC is correct, code must be updated |
| AC6: read_text returns last_content | Verifiable, already implemented (server.py L108-110) | None |
| AC7: All #856 RED tests pass | Verifiable, standard test gate. 17 tests in test_mcp_browser_fetcher_852.py | None |
| AC8: ruff clean | Verifiable, standard lint gate | None |

### AC2 Refinement

Original: "app_lifespan() creates CDPConnectionManager + BrowserContentFetcher (guarded, fallback to None on failure)."

**Refined AC2**: "app_lifespan() creates CDPConnectionManager + BrowserContentFetcher (guarded by try/except — CDPConnectionError or any connection failure → fetcher stays None). Disconnects CDPConnectionManager in finally block after yield."

Builder guidance: Use try/finally around the yield. In the try before yield, create CDPConnectionManager, call await cdp.connect() inside nested try/except, create BrowserContentFetcher(cdp) on success. In finally after yield, call await cdp.disconnect() if cdp was created and is connected. See CDPConnectionManager.__aexit__ pattern in serve/browser/src/owlbear_browser/cdp.py L86-98 for cleanup reference.

### Implementation Notes for Builder

1. **AC5 code fix needed**: Current navigate() at L83-84 returns `""` when fetcher is None. Must change to `raise ToolError("Browser not available")` or similar — the RED tests assert ToolError with message containing "browser"/"available"/"not".
2. **AC2 remaining work**: server.py app_lifespan() at L63-68 only yields AppContext(allowlist=allowlist). Must add CDPConnectionManager creation, guarded connect, BrowserContentFetcher initialization, and finally-block cleanup.
3. **775 test regression**: test_navigate_does_not_raise_for_allowlisted_domain needs mock fetcher — tracked separately in #861.

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| cdp.connect() | CDP timeout (Edge not running) | CDPConnectionError | Yes (AC2 guard) | fetcher=None → ToolError on navigate |
| cdp.connect() | Unexpected error | Exception | Yes (AC2 guard) | fetcher=None → ToolError on navigate |
| fetcher.fetch(url) | SSO redirect | AuthenticationRequired | Yes (AC4) | ToolError with descriptive message |
| cdp.disconnect() | Disconnect failure | Exception | Should be suppressed in finally | None — cleanup is best-effort |

### Challenge Results

- Challenger: reconsider (confidence 0.32)
- Challenger concerns: (1) timeout spec in AC2, (2) non-AuthRequired catch-all, (3) #842 dep safety, (4) error msg precision, (5) cleanup/finally needed
- Architect response: Partially accepted, partially rebutted
  - **Accepted**: #5 cleanup clause — AC2 refined to include disconnect in finally block
  - **Accepted**: #3 dependency #842 safe — deliverables confirmed in codebase
  - **Accepted**: #4 error messages adequate — keyword-based test assertions are correct pattern
  - **Rebutted**: #1 timeout spec — Playwright has default timeouts, CDPConnectionError guard covers it. Over-specification (YAGNI)
  - **Rebutted**: #2 non-AuthRequired catch-all — MCP framework handles unhandled tool exceptions as internal errors. Adding catch-all would mask bugs. Correct pattern is to catch only expected exceptions
- Challenger confidence 0.32 rates implementation completeness, not AC quality. This is a GREEN task — the gaps ARE the work. AC is sound and verifiable.
- Architect final confidence: .90

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC2 refined to include CDPConnectionManager cleanup after yield. Builder guidance provided for AC5 code fix and AC2 lifespan wiring.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_lifespan_857.py
- Classes: `TestFromAC_LifespanBrowserFetcherWiring`
- Tests per category: happy 2, edge 1, error 0, boundary 1
- Total: 4 tests, all FAIL
- ruff: clean
- Commit: 3fd37121

### AC Coverage Table

| AC Line | Tests |
|---------|-------|
| AC1: AppContext fields | Covered by existing test_mcp_browser_fetcher_852.py (17 tests, all pass) |
| AC2: app_lifespan creates CDPConnectionManager + BrowserContentFetcher | `test_lifespan_fetcher_is_not_none_when_cdp_connect_succeeds`, `test_lifespan_fetcher_is_browser_content_fetcher_instance`, `test_lifespan_browser_content_fetcher_constructed_with_cdp_manager`, `test_lifespan_creates_independent_fetcher_per_invocation` — ALL FAIL |
| AC3: navigate() calls fetcher.fetch(), stores, returns | Covered by existing tests (pass) |
| AC4: AuthenticationRequired → ToolError | Covered by existing tests (pass) |
| AC5: fetcher=None → ToolError | Covered by existing tests (pass) |
| AC6: read_text() returns last_content | Covered by existing tests (pass) |
| AC7: All #856 RED tests pass | Existing 17 tests all pass — no new failures introduced |
| AC8: ruff clean | n/a (test files only) |

### Failure Summary
- Tests 1 & 2: `ctx.fetcher is None` — app_lifespan never creates BrowserContentFetcher
- Test 3: `AttributeError: owlbear_mcp_browser.server has no attribute BrowserContentFetcher` — only TYPE_CHECKING import, no runtime import added yet
- Test 4: `AssertionError: fetcher1 is not None` — same root cause as 1 & 2

[[2026-04-14]]
## CDP Pivot Impact
Fetcher wiring implementation (navigate calls `fetcher.fetch()`, read_text returns `last_content`) will be replaced by Playwright direct approach in #871 (navigator uses `page.goto()` + `page.content()` + `extract_content()`). This task's deliverables will be superseded when #871 lands.