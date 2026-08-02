---
id: 838
title: Wire check_sso_redirect() into browser URL-fetch pipeline
status: archived
priority: medium
created: '2026-04-11T17:45:57.821416+00:00'
updated: '2026-04-12T16:46:39.579621+00:00'
tags:
- phase-1
- scope:browser
- type:feature
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

`CDPConnectionManager.check_sso_redirect(page)` exists in `serve/browser/src/owlbear_browser/cdp.py` (L116) and detects SSO redirects and login forms. However it is never called from the extraction path — the content pipeline currently only calls `extract(html)` which receives an already-fetched HTML string.

AC3 of task #760 says "Login redirect detection aborts extraction, reports SSO expiry." The isolation tests pass (`TestFromAC_SSODetection` in `test_edge_launcher_cdp_755.py`) but the integration call site is missing.

## Acceptance Criteria

1. In the browser URL-fetch workflow (the code path that navigates a URL and returns HTML), call `await manager.check_sso_redirect(page)` **before** passing the HTML to `extract()`.
2. If `AuthenticationRequired` is raised, the extraction must be aborted (exception propagates or is converted to an error response).
3. The MCP `navigate`/`read_text` tools in `serve/mcp-browser/src/owlbear_mcp_browser/server.py` or the equivalent fetch handler must surface the `AuthenticationRequired` error to the caller.
4. Integration test: a test that stubs a page with an IdP URL, calls the full fetch→extract pipeline, and confirms `AuthenticationRequired` propagates (or is wrapped in an appropriate error response).

## Notes

- `check_sso_redirect(page)` takes a Playwright `page` object — it cannot be called from `extract(html: str)` which only receives HTML. Call site must be at Playwright layer.
- MCP browser server (`server.py`) is currently a stub — the actual CDP fetch integration is a prerequisite.
- Identified by reviewer during #760 code review.
[[2026-04-12]]

## Research

- Research doc: .owlbear/research/838-wire-check-sso-redirect.md
- Sources: 10 studied, 8 high-relevance (all internal codebase)
- Recommendation: Close #838 as superseded — 3/4 ACs (AC1, AC2, AC4) fully covered by #830/#842 (BrowserContentFetcher). AC3 (MCP server wiring) extracted to new task #852. (confidence: .85)
- Follow-up tasks created: #852 (Wire BrowserContentFetcher into MCP browser server tools) at research
- Decision requests: none — T1 autonomous (scope overlap resolution + follow-up extraction)

## Challenge Results

- Challenger: FALLBACK — subagent unavailable
- Confidence in original: .85
- Key challenges: Self-challenged keeping #838 narrowed to AC3 only vs. new task. New task wins — cleaner AC, proper depends_on chain (#842), avoids confusion with superseded ACs.
- Researcher response: accepted — separate task is more actionable
[[2026-04-12]]

## Architecture Review

### Verdict: REJECT (Superseded) → done

Task #838 has no remaining unique scope. All 4 ACs are fully addressed by other tasks:

| #838 AC | Requirement | Covered By | Evidence |
|---------|-------------|------------|----------|
| AC1 | Call `check_sso_redirect(page)` before `extract()` | #830/#842 | `BrowserContentFetcher.fetch()` in `fetcher.py:18` calls `await self._cdp.check_sso_redirect(page)` before `extract_content()` |
| AC2 | `AuthenticationRequired` aborts extraction | #830/#842 | Exception propagates from `check_sso_redirect` through `fetch()`. Test `test_sso_redirect_raises_authentication_required` confirms. |
| AC3 | MCP tools surface `AuthenticationRequired` | #852 | New task with clean AC and `depends_on: [842]`. MCP server.py confirmed still stubs. |
| AC4 | Integration test with stubbed IdP URL | #830/#842 | 19 tests in `test_contentfetcher_impl_830.py` (lines 194-243 cover SSO path explicitly) |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task superseded — no implementation scope remains |
| Premise challenge | FAIL | Capability now exists in #830/#842 (BrowserContentFetcher). AC3 extracted to #852. |

### Codebase Verification

- `serve/browser/src/owlbear_browser/fetcher.py` — BrowserContentFetcher exists, calls `check_sso_redirect(page)` at line 18, propagates `AuthenticationRequired`
- `tests/test_contentfetcher_impl_830.py` — 19 tests covering SSO detection, AuthenticationRequired propagation, page lifecycle
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — 6 stub tools, no BrowserContentFetcher wiring (correctly scoped to #852)
- #852 created with `depends_on: [842]`, parent: 751, correct AC for MCP layer wiring

### Challenge Results

- Challenger: FALLBACK — not invoked (REJECT verdict, skip per protocol)
- Researcher recommendation (close as superseded): validated and accepted

### Action Taken

Closed as superseded. #830/#842 cover AC1/AC2/AC4. #852 covers AC3. Recommend orchestrator archive this task.
[[2026-04-12]]

## Audit

### AC Verification (Superseded Task)

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Call check_sso_redirect(page) before extract() | Superseded by #830/#842 — `fetcher.py:18` calls `await self._cdp.check_sso_redirect(page)` before `extract_content()` | PASS |
| AC2: AuthenticationRequired aborts extraction | Superseded by #830/#842 — exception propagates through `fetch()`. Test `test_sso_redirect_raises_authentication_required` (test_contentfetcher_impl_830.py:193) confirms | PASS |
| AC3: MCP tools surface AuthenticationRequired | Extracted to #852 (at todo, depends_on [842]). MCP server.py confirmed still stubs. Scope properly transferred | PASS |
| AC4: Integration test with stubbed IdP URL | Superseded by #830/#842 — 21 tests in test_contentfetcher_impl_830.py, SSO path at L193-243 | PASS |

### Research Deliverables

- Research doc: `.owlbear/research/838-wire-check-sso-redirect.md` — exists
- Follow-up task: #852 created at todo, references research doc
- Follow-up references research doc: confirmed in #852 body

### Test Results

- pytest (scoped): test_contentfetcher_impl_830.py — 21 passed, 0 failed
- pytest (full): serial run reached ~57% — scattered pre-existing failures, none in #838 scope (no code changes for this task)
- ruff: clean — 0 violations in serve/ and tests/

### Architect Quality: 4/5

Original AC was clear and specific with 4 verifiable criteria. Supersession was correctly identified by researcher. AC3 properly extracted to #852 with clean dependencies. Minor gap: task could have been identified as overlapping with #830 earlier in the pipeline.

### Deduction Breakdown

- Start: 1.00
- AC lines without evidence: 0 (all 4 verified via supersession) — -.00
- Lint: clean — -.00
- AC quality >3: no deduction — -.00
- Reviewer evidence section: N/A for superseded task (architect review serves equivalent role) — -.00
- Full suite incomplete (mitigated: zero code changes, domain tests 21/21 pass) — -.01
- Upstream did not commit deliverables (task file + research doc untracked) — -.02

### Confidence: .97

### Action: archive
