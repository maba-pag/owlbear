---
id: 859
title: 'Reconcile #852 fetcher tests after Phase 2 CDP session management (#854)'
status: in-progress
priority: important
created: '2026-04-13T13:53:00.035906+00:00'
updated: '2026-04-13T23:28:20.841423+00:00'
tags:
- phase-2
- scope:mcp-browser
- type:test
- archived
- superseded
parent: 837
depends_on:
- 854
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
After #854 (Phase 2 CDP session management) lands, navigate() and read_text() use page.goto(url) and extract_content(page.content(), page.url) respectively. This replaces #852's Phase 1 fetcher.fetch()/last_content pattern for those two tools.

Several tests in test_mcp_browser_fetcher_852.py will fail because they assert Phase 1 behavior that Phase 2 supersedes:

**Conflicting tests (must update or remove):**
- `test_navigate_calls_fetcher_fetch_with_url` — asserts fetcher.fetch() called; Phase 2 uses page.goto()
- `test_navigate_returns_markdown_from_fetcher` — asserts fetcher return flows through; Phase 2 returns page.goto() result
- `test_navigate_stores_result_in_last_content` — asserts last_content updated; Phase 2 doesn't use last_content
- `test_navigate_fetcher_none_raises_tool_error` — asserts ToolError when fetcher=None; Phase 2 checks page=None
- `test_navigate_fetcher_none_tool_error_describes_unavailability` — same
- `test_read_text_returns_last_content_after_navigate` — Phase 2 reads live page, not cached
- `test_read_text_returns_most_recent_navigate_content` — same
- Integration tests asserting fetcher delegation

**Non-conflicting tests (should still pass):**
- `test_navigate_authentication_required_raises_tool_error` — if AuthenticationRequired is still caught
- `test_app_ctx_has_fetcher_field_default_none` — field still exists until cleanup
- `test_app_ctx_has_last_content_field_default_empty_string` — field still exists until cleanup

**AC:**
- [ ] All tests in test_mcp_browser_fetcher_852.py either pass or are removed/updated to reflect Phase 2 behavior
- [ ] No tests assert fetcher.fetch() delegation from navigate() (Phase 2 uses page.goto)
- [ ] No tests assert last_content caching from navigate() (Phase 2 uses live page)
- [ ] AppContext.fetcher and AppContext.last_content fields remain (cleanup deferred) but tests don't assert their use in navigate/read_text
- [ ] All other test files unaffected
- [ ] ruff clean
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: reconcile Phase 1 test file after Phase 2 supersedes |
| Interface clarity | PASS (refined) | AC tightened below — "remove conflicting" replaces ambiguous "updated to reflect Phase 2" |
| Dependency correctness | PASS | depends_on [854] correct — can't reconcile until Phase 2 implementation exists |
| Module layering | PASS | Test-only task, no production code |
| TDD compliance | PASS | Tagged type:test — this IS the test task |
| KISS/YAGNI | PASS | Minimal scope: remove/keep existing tests, no new code |
| Premise challenge | PASS | Phase 2 replaces Phase 1 behavior; Phase 1 tests must be cleaned up |
| Pattern consistency | PASS | Standard test reconciliation |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp-browser only |

### AC Refinement (supersedes original AC1)

Original AC1 ("All tests either pass or are removed/updated to reflect Phase 2 behavior") is ambiguous — "updated to reflect Phase 2 behavior" could lead to duplicating tests already in test_mcp_browser_session_837.py.

**Refined AC (binding):**
- [ ] Tests asserting Phase 1 fetcher delegation (fetcher.fetch calls, last_content caching, AuthenticationRequired from fetcher) are **removed** — do NOT rewrite as Phase 2 behavior tests (test_mcp_browser_session_837.py already covers page.goto, extract_content, page=None checks)
- [ ] AppContext field tests (TestFromAC_AppContextFields: defaults, constructor kwargs) remain and pass
- [ ] No test in the file asserts fetcher.fetch() was called by navigate()
- [ ] No test in the file asserts last_content was set by navigate()
- [ ] AppContext.fetcher and AppContext.last_content fields remain on the dataclass (cleanup deferred)
- [ ] All other test files unaffected
- [ ] ruff clean

### Test Inventory (17 tests in file)

**KEEP (4 — TestFromAC_AppContextFields):**
- test_app_ctx_has_fetcher_field_default_none
- test_app_ctx_has_last_content_field_default_empty_string
- test_app_ctx_accepts_fetcher_kwarg
- test_app_ctx_accepts_last_content_kwarg

**REMOVE (13 — all other classes):**
- TestFromAC_NavigateFetcherWiring (7 tests): All assert fetcher delegation or AuthenticationRequired from fetcher. Note: test_navigate_authentication_required_raises_tool_error and test_navigate_fetcher_none_* would "pass accidentally" under Phase 2 (page=None → ToolError, not fetcher → AuthenticationRequired), but they test Phase 1 intent and should still be removed to avoid misleading test coverage.
- TestFromAC_ReadTextState (3 tests): All assert last_content caching behavior. test_read_text_returns_empty_string_before_navigate was unlisted in original body but IS conflicting (Phase 2 read_text raises ToolError when page=None, not returns "").
- TestFromAC_IntegrationFetcherWiring (3 tests): All assert fetcher delegation end-to-end.

### Body Classification Corrections

Original body missed 4 tests from classification:
- test_app_ctx_accepts_fetcher_kwarg — non-conflicting (KEEP)
- test_app_ctx_accepts_last_content_kwarg — non-conflicting (KEEP)
- test_navigate_tool_error_message_describes_sso_expiry — conflicting (REMOVE)
- test_read_text_returns_empty_string_before_navigate — conflicting (REMOVE)

Original body misclassified test_navigate_authentication_required_raises_tool_error as "non-conflicting." It passes under Phase 2 only because page=None triggers ToolError before fetcher is reached — misleading test that should be REMOVED.

### Dependency Analysis

| Task | Status | Relationship |
|------|--------|--------------|
| #854 (GREEN: CDP session management) | todo | Blocking — must complete before #859 can start |
| #837 (parent: browser session management) | in-progress | Parent epic |
| #852 (Phase 1 fetcher wiring) | in-progress | Source of the tests being reconciled |

### Challenge Results
- Challenger: RECONSIDER (confidence 0.65) — flagged AC1 ambiguity re: duplicate Phase 2 tests
- Architect response: ACCEPTED — refined AC1 to explicitly prohibit duplicate test creation; specified exact keep/remove disposition for all 17 tests

### Verdict: APPROVE (with AC refinement)
### Action Taken: Advanced to todo. AC1 refined to "remove conflicting tests" (not "update to Phase 2"). Full 17-test disposition provided for builder clarity.
[[2026-04-13]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no new failing tests applicable.
- Task is a test reconciliation: remove 13 conflicting Phase 1 tests from `tests/test_mcp_browser_fetcher_852.py`, retain 4 `TestFromAC_AppContextFields` tests.
- Passing through to builder.
- Dependency: #854 (GREEN: CDP session management) must land first before builder can verify the 4 kept tests pass.
- Full keep/remove disposition already documented in Architecture Review (17-test inventory).

[[2026-04-14]]
## Archived — Superseded by CDP Pivot
Reconciliation of fetcher tests after CDP session management no longer needed — CDP session management (#854) itself is superseded. Phase 1 fetcher tests and Phase 2 CDP session tests are both replaced by Playwright + SSO extension approach.