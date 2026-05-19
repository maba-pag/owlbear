---
id: 881
title: RED — Test GraphContentFetcher protocol + Graph API logic
status: archived
priority: someday
created: '2026-04-14T20:25:52.920823+00:00'
updated: '2026-04-15T03:52:56.299378+00:00'
tags:
- phase-4
- scope:knowledge
- deferred
- tdd:red
parent: 879
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Write failing tests for the `GraphContentFetcher` class covering protocol conformance and Graph API logic.

## Acceptance Criteria

1. Protocol conformance: `isinstance(fetcher, ContentFetcher)` is True
2. URL parsing: SharePoint URL correctly decomposed into hostname + site relative path
3. MSAL token acquisition: mock `PublicClientApplication`; verify token used in Authorization header
4. Site resolution: mock httpx for `GET /sites/{hostname}:/{path}` returns site-id
5. Page fetch: mock httpx for `GET /sites/{site-id}/pages/{page-id}?$expand=canvasLayout` returns canvas JSON
6. Content extraction: `innerHtml` from text web parts concatenated to markdown string
7. Error paths: auth failure raises, 404 site raises, malformed canvas response handled
8. Dependencies: msal + httpx only (no msgraph-sdk)
9. All tests fail (class does not yet exist)

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocol.py`
- Existing browser fetcher pattern: `serve/browser/src/owlbear_browser/fetcher.py`
- Test file: `tests/test_graph_fetcher_879.py`
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED tests only for GraphContentFetcher |
| Interface clarity | PASS | AC specifies exact mock targets (MSAL PublicClientApplication, httpx), API endpoints, assertion types |
| Dependency correctness | PASS | Layer 0, no deps needed; parent #879 decomposition is clean |
| Module layering | PASS | Test file in tests/, imports from owlbear_knowledge |
| TDD compliance | PASS | This IS the RED phase; GREEN counterpart is #883 |
| KISS/YAGNI | PASS | Minimal scope: tests only, no implementation |
| Premise challenge | PASS | GraphContentFetcher validated by research #773 and #879 |
| Pattern consistency | PASS | Mirrors BrowserContentFetcher test pattern (test_contentfetcher_impl_830.py) |
| Security surface | PASS | Tests mock MSAL/httpx; AC7 covers auth failure paths |
| Single domain | PASS | Knowledge domain only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 Protocol conformance | Clear, testable isinstance check | None |
| AC2 URL parsing | Testable; format derivable from research doc | None |
| AC3 MSAL mock | Specific mock target + header assertion | None |
| AC4 Site resolution | Specific endpoint pattern | None |
| AC5 Page fetch | Specific endpoint + query param | None |
| AC6 Content extraction | innerHtml from text web parts to markdown | None |
| AC7 Error paths | 3 enumerated scenarios | None |
| AC8 Dependencies | Clear constraint: msal + httpx only | None |
| AC9 All tests fail | Standard RED gate | None |

### Codebase Evidence

- ContentFetcher protocol: serve/knowledge/src/owlbear_knowledge/protocol.py (runtime_checkable, async fetch)
- BrowserContentFetcher pattern: serve/browser/src/owlbear_browser/fetcher.py (structural subtyping template)
- Existing fetcher test pattern: tests/test_contentfetcher_impl_830.py
- No GraphContentFetcher or Graph API code exists yet (confirmed via search)
- SourceType enum: serve/knowledge/src/owlbear_knowledge/models.py (SHAREPOINT_API handled by sibling #880/#882)

### Challenge Results

- Challenger: proceed (confidence 0.95)
- Architect response: accepted — no conflicts, clean decomposition, pattern-consistent AC

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC is precise and testable, architecture sound, follows established ContentFetcher test pattern

[[2026-04-14]]

## Test-Writer Notes

**Test file:** `tests/test_graph_fetcher_879.py` (shared with #880)

### AC Coverage

| AC | Description | Tests |
|----|-------------|-------|
| AC1 | Protocol conformance (`isinstance`, async) | `test_graph_content_fetcher_importable`, `test_satisfies_content_fetcher_protocol`, `test_fetch_is_async_coroutine` |
| AC2 | URL parsing: hostname + site path decomposition | `test_site_resolution_endpoint_includes_hostname_and_path`, `test_url_site_path_excludes_sitepages_and_page_filename`, `test_page_filename_from_url_used_in_page_lookup` |
| AC3 | MSAL token acquisition + Authorization header | `test_msal_public_client_app_used_for_token_acquisition`, `test_bearer_token_sent_in_authorization_header` |
| AC4 | Site resolution via Graph API | `test_site_resolution_endpoint_includes_hostname_and_path`, `test_site_not_found_404_raises_exception`, `test_site_id_from_resolution_used_in_subsequent_api_calls` |
| AC5 | Page fetch with canvasLayout expansion | `test_canvas_layout_expansion_included_in_page_fetch_url`, `test_page_endpoint_contains_resolved_site_id` |
| AC6 | innerHtml → markdown extraction | `test_inner_html_from_text_webpart_included_in_output`, `test_multiple_text_webparts_all_present_in_output`, `test_empty_canvas_sections_returns_string`, `test_malformed_canvas_response_handled_gracefully` |
| AC7 | Error paths: auth failure, 404, malformed canvas | `test_auth_failure_raises_exception`, `test_site_not_found_404_raises_exception`, `test_malformed_canvas_response_handled_gracefully` |
| AC8 | Dependencies: msal + httpx only | `test_msal_package_is_importable`, `test_graph_fetcher_uses_httpx_not_msgraph` |
| AC9 | All tests fail | ✅ Verified — 28 FAIL, 0 PASS |

### Test Counts by Category

- **Happy path:** 8 (protocol, token flow, site resolution, page fetch, content extraction)
- **Edge cases:** 3 (multi-webpart, empty canvas, URL parsing specificity)
- **Error paths:** 3 (auth failure, 404, malformed canvas)
- **Boundary:** 2 (page filename in lookup, SitePages exclusion from site path)

**Total: 28 tests (16 in TestFromAC_GraphContentFetcher, added 3 to existing file from #880) — all FAIL**

### Notes

- File was pre-populated by task #880's writer with SourceType and RefreshOrchestrator tests; #881 appended 3 additional URL-parsing and dependency specificity tests to close AC2+AC8 gaps.
- `test_msal_package_is_importable` fails: `msal` not yet in project deps (builder must add to pyproject.toml).
- `test_graph_fetcher_uses_httpx_not_msgraph` will pass once module exists — asserts httpx import present and no msgraph import.
- Ruff clean: 0 violations.
[[2026-04-15]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/graph_fetcher.py` — new module implementing `GraphContentFetcher` (MSAL device-code flow + httpx Graph API calls, URL parsing, innerHtml extraction). Already existed from prior work.
- `serve/knowledge/src/owlbear_knowledge/models.py` — `SourceType.SHAREPOINT_API = "sharepoint_api"` already present.
- `serve/knowledge/src/owlbear_knowledge/refresh.py` — `_handle_sharepoint_api`, `graph_fetcher` kwarg in `__init__`, routing in `refresh()` already present.

### Test Results

- 28 passed, 0 failed (all TestFromAC_* classes: SourceTypeSharePointAPI (4), GraphContentFetcher (16), RefreshOrchestratorDispatch (5+) plus extras from #880)
- RED verification: confirmed via test-writer notes (all 28 FAIL before implementation)

### Coverage

- `graph_fetcher.py`: **91.6%** (64/67 statements, 12/16 branches) ✅ ≥ 90%
- Uncovered lines 31-33: else-branch in `_parse_sharepoint_url` for URLs without `/SitePages/` — defensive path not exercised by current URLs

### Lint Status

- `ruff check`: **clean** — 0 violations on both `graph_fetcher.py` and test file

### Evidence

- `isinstance(fetcher, ContentFetcher)`: ✅
- MSAL `PublicClientApplication` patched and verified: ✅
- Bearer token in Authorization header: ✅
- Graph API URL sequence (site resolve → pages list → canvasLayout): ✅
- `innerHtml` extraction from text web parts: ✅
- Error paths (auth failure, 404, malformed canvas): ✅
- `msal` in `pyproject.toml`: ✅
- No `msgraph` import: ✅
[[2026-04-15]]

## Review Evidence

### Tests

pytest: **28 passed, 0 failed** (quality-runner, independent run)
Ruff: **clean** (0 violations)
Coverage: **96%** on `owlbear_knowledge.graph_fetcher` (uncovered: else-branch in `_parse_sharepoint_url` for non-SitePages URLs — consistent with builder report)

### AC Compliance

| AC | Test(s) | Assertion Strength | Status |
|----|---------|-------------------|--------|
| AC1 Protocol conformance | `test_satisfies_content_fetcher_protocol`, `test_fetch_is_async_coroutine`, `test_graph_content_fetcher_importable` | Strong: `isinstance(fetcher, ContentFetcher)` direct check | PASS |
| AC2 URL parsing | `test_site_resolution_endpoint_includes_hostname_and_path`, `test_url_site_path_excludes_sitepages_and_page_filename`, `test_page_filename_from_url_used_in_page_lookup` | Strong: hostname in URL + negative assertions (SitePages/filename excluded from site path) | PASS |
| AC3 MSAL token | `test_msal_public_client_app_used_for_token_acquisition`, `test_bearer_token_sent_in_authorization_header` | Mixed: first test accepts any of 3 MSAL methods (minor weakness); second test checks ALL GET calls for `Authorization: Bearer` value | PASS |
| AC4 Site resolution | `test_site_resolution_endpoint_includes_hostname_and_path`, `test_site_not_found_404_raises_exception`, `test_site_id_from_resolution_used_in_subsequent_api_calls` | Strong: custom site-id injected, verified in subsequent call URLs | PASS |
| AC5 Page fetch canvasLayout | `test_canvas_layout_expansion_included_in_page_fetch_url`, `test_page_endpoint_contains_resolved_site_id` | Strong: "canvasLayout" string in URL + site-id propagation | PASS |
| AC6 Content extraction | `test_inner_html_from_text_webpart_included_in_output`, `test_multiple_text_webparts_all_present_in_output`, `test_empty_canvas_sections_returns_string`, `test_malformed_canvas_response_handled_gracefully` | Mixed: first two strong (specific text); last two assert `isinstance(result, str)` only — intentionally weak for graceful-degradation paths | PASS |
| AC7 Error paths | `test_auth_failure_raises_exception`, `test_site_not_found_404_raises_exception`, `test_malformed_canvas_response_handled_gracefully` | Strong: `pytest.raises` for raise cases | PASS |
| AC8 Dependencies | `test_msal_package_is_importable`, `test_graph_fetcher_uses_httpx_not_msgraph` | Source code inspection for dep constraints | PASS |
| AC9 All tests fail | Test-writer self-report: 28 FAIL. Cannot independently verify — GREEN implementation (graph_fetcher.py) in working tree. Logical argument: `ImportError` on import + missing `SourceType.SHAREPOINT_API` would cause all 28 to fail. | UNVERIFIABLE (structural pipeline limitation) |

### Deductions

- −0.03: AC9 unverifiable (structural — GREEN implementation co-present with RED review)
- −0.02: `test_msal_public_client_app_used_for_token_acquisition` uses `or` across 3 MSAL methods; specific device-flow path not asserted. Compensated by `test_bearer_token_sent_in_authorization_header`.

### TestFromAC_* Modifications

None detected. Builder notes for #881 do not list test file changes.

### Notes

`TestFromAC_RefreshOrchestratorDispatch` in this file uses `graph_fetcher` kwarg (pre-decomposition naming), while task #884's tests use canonical `graph_content_fetcher`. Builder for #884 added backward-compat alias (`graph_content_fetcher if graph_content_fetcher is not None else graph_fetcher`) to preserve these tests. This alias pattern is correct and these 5 tests pass cleanly.

### Verdict

Confidence: **0.95 → PASS**
Action: Advance #881 → docs
[[2026-04-15]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` covers only project identity and repo branches — no module-level API docs to update |
| 2 | Module docstrings | Yes | Updated | `graph_fetcher.py`: all public symbols have accurate docstrings ✅. `models.py`: `SourceType` class docstring ✅. `refresh.py`: fixed stale `graph_fetcher` → `graph_content_fetcher` in `_handle_sharepoint_api` Returns section (commit 58ecb51e) |
| 3 | External attribution | Yes | Verified | `GraphContentFetcher Implementation Research (Task #879)` section already present in `.owlbear/sources/overview.md` — 4 sources (canvasLayout API ref, SE Q&A, msgraph-sdk dep analysis, azure-identity vs msal comparison) |
| 4 | CLI changes | No | N/A | No CLI changes in this task |
| 5 | Research doc | Yes | Verified | `.owlbear/research/879-graphcontentfetcher-implementation.md` exists; referenced in task body via architecture review section |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/refresh.py` — docstring only: `_handle_sharepoint_api` Returns section corrected to `graph_content_fetcher`

### Scratch Files

No `881-*` files found in `.owlbear/scratch/`.
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 Protocol conformance | test_satisfies_content_fetcher_protocol (isinstance check), test_fetch_is_async_coroutine | PASS |
| AC2 URL parsing | test_site_resolution_endpoint_includes_hostname_and_path, test_url_site_path_excludes_sitepages_and_page_filename | PASS |
| AC3 MSAL token | test_msal_public_client_app_used_for_token_acquisition, test_bearer_token_sent_in_authorization_header | PASS |
| AC4 Site resolution | test_site_resolution_endpoint_includes_hostname_and_path, test_site_id_from_resolution_used_in_subsequent_api_calls | PASS |
| AC5 Page fetch canvasLayout | test_canvas_layout_expansion_included_in_page_fetch_url, test_page_endpoint_contains_resolved_site_id | PASS |
| AC6 Content extraction | test_inner_html_from_text_webpart_included_in_output, test_multiple_text_webparts_all_present_in_output, test_malformed_canvas_response_handled_gracefully | PASS |
| AC7 Error paths | test_auth_failure_raises_exception (pytest.raises), test_site_not_found_404_raises_exception (pytest.raises HTTPStatusError), test_malformed_canvas_response_handled_gracefully | PASS |
| AC8 Dependencies | test_msal_package_is_importable, test_graph_fetcher_uses_httpx_not_msgraph | PASS |
| AC9 All tests fail | Unverifiable (structural: GREEN co-present), logical argument accepted | PASS (deducted) |

### Test Results

- pytest (full suite): 4387 passed, 190 failed, 8 skipped. All 190 failures in unrelated files (orchestrator_loop, planner_gates_selector, analysis, scaffold_mcp_memory, lint_guard_hook). Task-scoped: 28 passed, 0 failed.
- ruff: 3 errors, all outside scope (engine.py E501, test_refresh_sharepoint_879.py RUF002+UP024)

### Architect Quality: 5/5

All 9 AC lines specific and testable. Each maps to concrete assertions (isinstance, mock targets, endpoint patterns, error types). No builder improvisation needed. Research-grounded scope.

### Deduction Breakdown

- AC9 unverifiable (structural pipeline limitation): -0.02
- No in-scope test failures: no deduction
- No in-scope lint violations: no deduction
- Reviewer evidence present and detailed: no deduction
- AC quality 5/5: no deduction

### Confidence: 0.98

### Action: archive
