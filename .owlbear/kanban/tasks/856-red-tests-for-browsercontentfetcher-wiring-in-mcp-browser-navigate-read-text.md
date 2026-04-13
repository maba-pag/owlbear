---
id: 856
title: 'RED: Tests for BrowserContentFetcher wiring in MCP browser navigate/read_text'
status: in-progress
priority: important
created: '2026-04-12T15:15:37.708042+00:00'
updated: '2026-04-13T23:29:43.529436+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-red
parent: 852
depends_on:
- 849
- 850
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

MCP browser server needs RED-phase tests for wiring BrowserContentFetcher into navigate() and read_text() tools. Tests must use the ctx: Context mock pattern (established by #849/#850).

See `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` §3e for test patterns.

## Acceptance Criteria

1. Test file `tests/test_mcp_browser_fetcher_852.py` with `_make_app_ctx` and `_make_mcp_ctx` helpers.
2. Tests for `navigate(ctx, url)`:
   - Success: calls `fetcher.fetch(url)`, returns markdown content, updates `last_content` in AppContext.
   - AuthenticationRequired: caught and raised as `ToolError` with descriptive message.
   - Fetcher is None: raises `ToolError("Browser not available")` or similar.
3. Tests for `read_text(ctx)`:
   - Returns `last_content` from AppContext (set by prior navigate).
   - Returns empty string when no prior navigate.
4. Tests for `AppContext`:
   - Has `fetcher: BrowserContentFetcher | None` field (default None).
   - Has `last_content: str` field (default "").
5. All tests FAIL at RED phase (navigate/read_text still stubs).
6. ruff clean.

## Notes

- Depends on #849 (ctx mock helpers) and #850 (ctx: Context in tool signatures).
- Follow mock patterns from `tests/test_contentfetcher_impl_830.py` for BrowserContentFetcher mocks.
- `ToolError` imported from `mcp.server.fastmcp.exceptions`.
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/856-red-browserfetcher-wiring-tests.md
- Sources: 5 studied, 5 high-relevance (all codebase-internal)
- Recommendation: Task #856 deliverables already exist — `tests/test_mcp_browser_fetcher_852.py` covers all 6 AC items (17 tests, ruff clean). Implementation also shipped on parent #852. Only remaining work is fixing 2 stale tests in sibling files (#775, #850) that conflict with the new fetcher-None guard. (confidence: .90)
- Follow-up tasks created: #861 (Fix stale navigate tests in #775/#850 to supply mock fetcher)
- Decision requests: none
- Tier: T1 — autonomous test fix

## Challenge Results
- Challenger: FALLBACK — trivial finding, no recommendation to challenge
- Confidence in original: .90
- Self-challenge: "Should fetcher-None guard be removed?" No — correct behavior per #852 AC, prevents silent failures
[[2026-04-13]]
## Architecture Review

### Pre-existing Deliverables

All #856 deliverables were produced by the test-writer on parent task #852. The test file `tests/test_mcp_browser_fetcher_852.py` (17 tests, 330 lines) covers AC1–AC4 and AC6 completely. AC5 ("tests FAIL at RED phase") is no longer applicable — the #852 builder shipped the implementation, so tests now pass. This is a process artifact, not a defect — the tests were correctly written to fail and did fail before the GREEN phase.

**Test-writer: write a pass-through note acknowledging the pre-existing test file. No new tests needed.**

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: RED tests for fetcher wiring in navigate/read_text |
| Interface clarity | PASS | AC specifies exact file name, helper signatures, test cases, expected behaviors |
| Dependency correctness | PASS | #849/#850 in-progress but deliverables exist — parent #852 completed the full TDD cycle including these tests |
| Module layering | PASS | Test-only task, imports from owlbear_mcp_browser (correct direction) |
| TDD compliance | PASS | This IS the RED phase task; tests were correctly RED before implementation |
| KISS/YAGNI | PASS | Minimal scope, tests exercise only the specified behaviors |
| Premise challenge | PASS | Deliverables exist on parent #852, but pipeline requires task to transit gates |
| Pattern consistency | PASS | Uses established _make_app_ctx/_make_mcp_ctx pattern, pytest.raises(ToolError), AsyncMock |
| Security surface | PASS | No new boundaries — test-only changes |
| Single domain | PASS | scope:mcp-browser only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Test file with _make_app_ctx and _make_mcp_ctx helpers | Verifiable, delivered — both helpers present in test file | None |
| AC2: navigate success tests (calls fetch, returns markdown, updates last_content) | Verifiable, delivered — 3 tests cover all three assertions | None |
| AC3: AuthenticationRequired → ToolError, fetcher None → ToolError | Verifiable, delivered — 4 tests (auth error, message check, None guard, None message) | None |
| AC4: read_text returns last_content / empty string | Verifiable, delivered — 3 tests (after navigate, before navigate, most recent) | None |
| AC5: Tests FAIL at RED phase | N/A — implementation shipped on parent #852; tests were RED before GREEN phase | No action possible |
| AC6: ruff clean | Verifiable, confirmed by test-writer on #852 | None |

### Challenge Results

- Challenger: FALLBACK — deliverables pre-exist on parent, no architectural decision to challenge
- Architect response: accepted

### Verdict: APPROVE
### Action Taken: Advanced to todo. All deliverables exist in tests/test_mcp_browser_fetcher_852.py (17 tests). Test-writer should write pass-through note.
[[2026-04-13]]
## Test-Writer Notes

**Pass-through — deliverables pre-exist on parent task #852.**

- Test file: `tests/test_mcp_browser_fetcher_852.py` (17 tests, 330 lines)
- All AC items covered:
  - AC1: `_make_app_ctx` and `_make_mcp_ctx` helpers present ✓
  - AC2: `navigate()` success tests (calls fetch, returns markdown, updates `last_content`) ✓
  - AC3: `AuthenticationRequired` → `ToolError`, fetcher None → `ToolError` ✓
  - AC4: `read_text()` returns `last_content` / empty string ✓
  - AC5: N/A — implementation shipped on parent #852; tests were RED before GREEN phase ✓ (process artifact, not defect)
  - AC6: ruff clean ✓
- Current pytest status: 17 passed (implementation shipped by #852 builder)
- No new tests written — architecture review verdict was APPROVE with explicit pass-through instruction.

[[2026-04-14]]
## CDP Pivot Impact
Tests assert Phase 1 fetcher.fetch() delegation pattern which is being replaced by Playwright direct approach (#871). Tests in `test_mcp_browser_fetcher_852.py` will need removal/update when #871 lands. Cleanup tracked in #870.