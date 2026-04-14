---
id: 877
title: Resolve page=None behavior conflict in mcp-browser tools (click/type/select
  must ToolError, read_text/snapshot keep last_content fallback)
status: todo
priority: needed
created: '2026-04-14T15:28:40.305402+00:00'
updated: '2026-04-14T16:27:54.630130+00:00'
tags:
- phase-2
- scope:mcp-browser
- quality
parent: 751
depends_on:
- 871
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Cross-task AC conflict identified during #871 review cycle. Tasks 836/850 assert silent-return for page=None on all tools. Tasks 837/853/854 assert ToolError for the same condition. The current server.py implementation silently returns, which fails 15 TestFromAC_ assertions across 837/853/854.

**Root cause:** Task 836 AC says "all 6 tools accept ctx: Context as first parameter" — the tests over-specify by calling tools with page=None and asserting string return. The "callable with ctx" contract requires valid invocation, not null-page tolerance. Task 850 tests inherit the same over-specification.

**Architect adjudication (from #871 review cycle):**

### Interactive tools (click, type_input, select)
- page=None → `raise ToolError("No browser session")`
- These have no fallback mode. A browser page is physically required to click/type/select.

### Read tools (read_text, snapshot)
- page is not None → use page (Playwright path)
- page is None → return `last_content` (ContentFetcher fallback, may be "")
- This supports the fetcher-only pipeline: navigate() → fetcher.fetch() → last_content → read_text()/snapshot() returns it. ToolError here would break the pipeline.

## Acceptance Criteria

1. `click()`, `type_input()`, `select()` raise `ToolError("No browser session")` when `page is None`
2. `read_text()`, `snapshot()` continue returning `last_content` fallback when `page is None` (current behavior preserved)
3. Update `tests/test_mcp_browser_836.py` `TestFromAC_AllToolsCallableWithCtx`: click/type/select tests use a mock page instead of page=None
4. Update `tests/test_mcp_browser_ctx_850.py` `TestFromAC_CtxParameterOnAllTools`: click/type/select tests use a mock page instead of page=None
5. Update `tests/test_mcp_browser_session_837.py` `TestFromAC_ReadTextTool` and `TestFromAC_SnapshotTool`: ToolError-on-page=None tests → accept last_content fallback behavior
6. Update `tests/test_mcp_browser_session_853.py` `TestFromAC_ToolErrorWhenNoPage`: read_text/snapshot ToolError assertions → accept last_content fallback
7. Update `tests/test_mcp_browser_session_854.py` `TestFromAC_NoSessionMessage`: read_text/snapshot ToolError assertions → accept last_content fallback; navigate ToolError assertion → accept AppContext dry-run path (returns URL)
8. All MCP browser tests pass (test_mcp_browser_*.py)
9. ruff clean

## Notes

- 836 is in `review`, 850 is in `in-progress`, 837/853/854 are in `in-progress` — test updates here are correcting over-specified assertions, not changing the original task ACs
- Only 3 lines change in server.py (add ToolError guard to click/type/select)
- Existing test_mcp_browser_server_871.py (21 tests) should remain unaffected
[[2026-04-14]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: resolve page=None behavior conflict across 5 tools + align tests |
| Interface clarity | PASS | AC1–AC2 clearly define per-tool behavior. AC3–AC7 specify exact test classes/methods |
| Dependency correctness | PASS | depends_on [871] is in `todo`; server.py already migrated. Dependency ordering prevents premature build |
| Module layering | PASS | All changes within mcp-browser server and tests. No cross-package imports |
| TDD compliance | PASS | Conflict-resolution task: modifies both server.py (3 lines) and tests in one atomic change |
| KISS/YAGNI | PASS | Minimal: 3 server.py lines + test assertion updates. No new abstractions |
| Premise challenge | PASS | 15 failing test assertions from conflicting AC across tasks 836/850 vs 837/853/854 — must be resolved |
| Pattern consistency | PASS | Uses existing `AppContext.last_content` field, existing `_MSG_NO_PAGE` constant, existing `getattr` pattern |
| Security surface | PASS | No new boundaries. Allowlist check still runs before any navigate fallback |
| Single domain | PASS | All within scope:mcp-browser |

### Server.py Changes (3 lines, for builder reference)
1. `read_text`: `raise ToolError(_MSG_NO_PAGE)` → `return getattr(app_ctx, "last_content", "")`
2. `snapshot`: `raise ToolError(_MSG_NO_PAGE)` → `return getattr(app_ctx, "last_content", "")`
3. `navigate` (AppContext branch, line 118): `raise ToolError(_MSG_NO_PAGE)` → `return url` (dry-run: allowlist passed, no page/fetcher to use)

### AC Clarifications for Builder
- **AC2 wording**: "current behavior preserved" refers to the intended design behavior, not current HEAD (which raises ToolError). The change IS to replace ToolError with last_content return for read_text/snapshot.
- **AC6 minor gap**: `test_mcp_browser_session_853.py` `TestFromAC_ToolErrorWhenNoPage` also contains `test_navigate_raises_when_page_none` (uses AppContext), which will fail after the navigate dry-run change. Update it to accept URL return. AC8 catch-all covers this.
- **AC7 navigate semantic**: "AppContext dry-run path" means: when `isinstance(app_ctx, AppContext)` and both `fetcher` and `page` are None, return `url` after allowlist check (consistent with the non-AppContext fallback path at the bottom of navigate). The allowlist security gate is preserved.
- **Notes inaccuracy**: "add ToolError guard to click/type/select" should read "change read_text/snapshot/navigate FROM ToolError TO fallback returns" — the guards already exist on click/type/select. Line count (3) is correct.

### SimpleNamespace vs AppContext paths
- test_mcp_browser_session_837.py navigate tests use `_make_ctx_with_page(None)` → SimpleNamespace with explicit `page` attribute → SimpleNamespace path still raises ToolError → UNAFFECTED.
- test_mcp_browser_session_854.py navigate test uses `_make_mcp_ctx_no_page()` → AppContext → affected by dry-run change → covered by AC7.
- test_mcp_browser_session_853.py navigate test uses `_make_mcp_ctx_no_page()` → AppContext → affected but NOT listed in AC6 → builder should update per AC8 catch-all.

### 836/850 read_text/snapshot tests: NO changes needed
- `test_read_text_called_with_ctx` and `test_snapshot_called_with_ctx` in 836 assert `isinstance(result, str)` — `""` passes this. Same for 850. AC3/AC4 correctly scope changes to click/type/select only.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in tool list
- Architect response: Self-challenged. Confidence: 0.89. Gap in AC6 (navigate test in 853) is covered by AC8 catch-all and these architecture notes.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder should reference architecture review notes alongside AC, especially for AC6 navigate gap and AC7 navigate semantic.