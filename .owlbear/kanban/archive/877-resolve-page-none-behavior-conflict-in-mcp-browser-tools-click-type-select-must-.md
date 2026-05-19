---
id: 877
title: Resolve page=None behavior conflict in mcp-browser tools (click/type/select
  must ToolError, read_text/snapshot keep last_content fallback)
status: archived
priority: needed
created: '2026-04-14T15:28:40.305402+00:00'
updated: '2026-04-14T21:29:43.189194+00:00'
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

### Action Taken: Advanced to todo. Builder should reference architecture review notes alongside AC, especially for AC6 navigate gap and AC7 navigate semantic

[[2026-04-14]]

## Test-Writer Notes

- Test file (new): tests/test_mcp_browser_877.py
- Classes (new): TestFromAC_ReadTextPageNoneFallback, TestFromAC_SnapshotPageNoneFallback, TestFromAC_NavigateAppContextDryRun
- Tests per category (877 file): happy 2, edge 2, error 0, boundary 1
- Total new: 5 tests, all FAIL (ToolError raised instead of fallback returns)
- ruff: clean

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (click/type/select raise ToolError when page=None) | Covered by existing PASSING tests in 837/853/854 — no new RED tests possible (already implemented) | Pass-through |
| AC2 (read_text returns last_content fallback) | test_read_text_returns_last_content_when_page_none, test_read_text_returns_empty_string_when_page_none_no_cached_content | FAIL ✅ |
| AC2 (snapshot returns last_content fallback) | test_snapshot_returns_last_content_when_page_none, test_snapshot_returns_empty_string_when_page_none_no_cached_content | FAIL ✅ |
| AC3 (update 836 click/type/select to use mock page) | Updated 3 tests in TestFromAC_AllToolsCallableWithCtx — added_make_mcp_ctx_with_mock_page() helper; tests now PASS (existing behavior) | Done |
| AC4 (update 850 click/type/select to use mock page) | Updated 3 tests in TestFromAC_CtxParameterOnAllTools — inline mock page; tests now PASS | Done |
| AC5 (update 837 read_text/snapshot ToolError → last_content) | test_read_text_returns_string_when_page_is_none, test_snapshot_returns_string_when_page_is_none | FAIL ✅ |
| AC6 (update 853 read_text/snapshot/navigate ToolError → fallback) | test_read_text_returns_string_when_page_none, test_snapshot_returns_string_when_page_none, test_navigate_returns_url_when_page_none | FAIL ✅ |
| AC7 (update 854 read_text/snapshot/navigate ToolError → fallback) | test_read_text_returns_string_when_no_page, test_snapshot_returns_string_when_no_page, test_navigate_returns_url_when_no_page | FAIL ✅ |
| AC8/navigate dry-run (AppContext+fetcher=None returns url) | test_navigate_returns_url_when_appcontext_no_fetcher_no_page | FAIL ✅ |

### Summary

- 5 new tests in test_mcp_browser_877.py: all FAIL
- 8 existing tests updated in 837/853/854: flipped from PASS → FAIL (over-specified assertions removed)
- 6 existing tests corrected in 836/850 (click/type/select mock page): now PASS (correct existing behavior)
- Total failing across all files: 20 (up from 13 pre-changes; net 7 new failures proving unimplemented behavior)
- Commit: 6583eb36
[[2026-04-14]]

## Builder Notes

### Files Changed

- **None** — server.py already contained the correct implementation from the #871 dependency commit (6583eb36 or prior). All three lines already in place:
  - `read_text`: returns `getattr(app_ctx, "last_content", "")` when page is None
  - `snapshot`: returns `getattr(app_ctx, "last_content", "")` when page is None
  - `navigate` AppContext branch: returns `url` (dry-run) when fetcher and page are both None

### Test Evidence

- Scope: test_mcp_browser_877.py + 837 + 853 + 854 + 836 + 850 + 871
- Result: **114 passed, 0 failed** (7.07s, 4 xdist workers)
- All 5 new TestFromAC_ tests in 877.py: PASS
- All 8 updated tests in 837/853/854: PASS
- All 6 corrected tests in 836/850: PASS
- Existing 871 suite (21 tests): PASS — unaffected

### Lint Status

- `ruff check serve/mcp-browser/src/ tests/test_mcp_browser_*.py` → **clean**

### Coverage

- No new code written; all touched functions previously exercised. 90%+ maintained.

### Summary

Build was a verification pass: dependency already satisfied the AC. GREEN confirmed across all 114 tests.
[[2026-04-14]]

## Review Evidence

### Test Results

Quality-Runner: **FAILED TO EXECUTE** — WMI/xdist hang on node spawning (environmental, not a code defect). Fell back to sequential evidence.

**Fallback 1 — `pytest_results.txt` (full-suite run, new file in working tree):**

- **4220 passed, 288 failed, 8 skipped** (249.85s)
- Zero `test_mcp_browser_*` failures in the failure list. All 288 failures are pre-existing unrelated tasks.
- This is direct evidence that the entire mcp-browser test suite passes, consistent with builder's "114 passed, 0 failed" scoped claim.

**Noted artifact:** `test_836_v.txt` (new file in working tree) shows 8 failures in `test_mcp_browser_836.py` with ToolError at server.py line numbers that differ from current HEAD. Confirmed to be a RED-phase artifact captured by the test-writer before the #871 dependency implementation was in place. It does NOT represent current state.

### Lint

Not independently run (QR unavailable). Builder self-reports `ruff check serve/mcp-browser/src/ tests/test_mcp_browser_*.py` → clean. Deduction applied for non-independent verification.

### Coverage

No new production code written (builder notes: implementation already present from #871 commit 6583eb36). Coverage gate N/A.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|---------------------------|---------|
| AC1: click/type/select raise ToolError when page=None | `TestFromAC_ToolErrorWhenNoPage` (853), `TestFromAC_NoSessionMessage` (854) exact match assertions | Yes — `pytest.raises(ToolError)` | COVERED |
| AC2: read_text returns last_content | `test_read_text_returns_last_content_when_page_none`, `test_read_text_returns_empty_string_when_page_none_no_cached_content` (877) | Yes — exact `result == _LAST_CONTENT` and `result == ""` | COVERED (STRONG) |
| AC2: snapshot returns last_content | `test_snapshot_returns_last_content_when_page_none`, `test_snapshot_returns_empty_string_when_page_none_no_cached_content` (877) | Yes — exact value | COVERED (STRONG) |
| AC3: 836 click/type/select use mock page | 3 tests in `TestFromAC_AllToolsCallableWithCtx` (836) — `_make_mcp_ctx_with_mock_page()` | Yes — ToolError would fail `isinstance(result, str)` | COVERED |
| AC4: 850 click/type/select use mock page | 3 tests in `TestFromAC_CtxParameterOnAllTools` (850) — inline mock page | Yes — same | COVERED |
| AC5: 837 read_text/snapshot accept string return | `test_read_text_returns_string_when_page_is_none`, `test_snapshot_returns_string_when_page_is_none` (837) | Yes — ToolError is not a str | COVERED (LAX, compensated by 877) |
| AC6: 853 read_text/snapshot/navigate fallback | 3 tests in `TestFromAC_ToolErrorWhenNoPage` (853): read_text/snapshot assert `isinstance(str)`, navigate asserts `result == _ALLOWED_URL` | Yes | COVERED |
| AC7: 854 read_text/snapshot/navigate fallback | 3 tests in `TestFromAC_NoSessionMessage` (854): same pattern | Yes | COVERED |
| AC8: All mcp_browser tests pass | `pytest_results.txt` full suite: 0 mcp_browser failures | Yes (indirect) | PASS |
| AC9: ruff clean | Builder self-report (not independently verified) | — | UNVERIFIED |

No MISSING lines.

#### 5.1 Security

No new user-facing input surfaces. `getattr(app_ctx, "last_content", "")` reads internal lifespan context only — no injection risk. Navigate allowlist check (`app_ctx.allowlist.check(url)`) remains the first guard before any page/fetcher/dry-run branch. PASS.

#### 5.2 Test Integrity — TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| 837 `test_read_text_returns_string_when_page_is_none` | Changed from `pytest.raises(ToolError)` → `assert isinstance(result, str)` | CORRECTED — adjudicated design change; original assertion was over-specified per architect #877 |
| 837 `test_snapshot_returns_string_when_page_is_none` | Same pattern | CORRECTED |
| 853 `test_navigate_returns_url_when_page_none` | Changed from `pytest.raises(ToolError)` → `assert result == _ALLOWED_URL` | CORRECTED — stronger assertion (exact URL) |
| 853 `test_read_text_returns_string_when_page_none` | ToolError → `assert isinstance(result, str)` | CORRECTED |
| 853 `test_snapshot_returns_string_when_page_none` | ToolError → `assert isinstance(result, str)` | CORRECTED |
| 854 `test_navigate_returns_url_when_no_page` | ToolError → `assert result == _ALLOWED_URL` | CORRECTED — stronger |
| 854 `test_read_text_returns_string_when_no_page` | ToolError → `assert isinstance(result, str)` | CORRECTED |
| 854 `test_snapshot_returns_string_when_no_page` | ToolError → `assert isinstance(result, str)` | CORRECTED |
| 836/850 click/type/select tests | page=None calls → mock page calls | CORRECTED — changed from invalid invocation to valid invocation |

All changes are architect-adjudicated corrections, not weakening of valid assertions. PRESERVED.

#### 5.3 Test Quality

- **877 assertions:** STRONG — exact `result == _LAST_CONTENT` and `result == ""` and `result == _ALLOWED_URL`
- **837/853/854 read_text/snapshot:** LAX (`isinstance(result, str)`) — ADEQUATE: these tests originally asserted wrong behavior; the correction is minimal. **Compensated** by 877 exact-value tests.
- **853/854 navigate:** STRONG — `result == _ALLOWED_URL`
- **Mutation robustness:** Flipping read_text/snapshot back to `raise ToolError` would fail `isinstance(result, str)` (exception propagates, no return value). Flipping navigate return would fail exact URL assertion.
- **Test independence:** All tests use isolated `AppContext` instances. No shared mutable state.
- Overall: **ADEQUATE** — no WEAK rating.

#### 5.4 Data Safety

No concurrent writes, no LLM output persisted, no multi-step atomicity concerns. PASS.

#### 5.5 Implementation-Aware Test Gap Analysis

- `navigate` SimpleNamespace path (when `"page" in vars(app_ctx)` and `page is None` → raises ToolError): still covered by existing 837 tests using `_make_ctx_with_page(None)` (SimpleNamespace with explicit page attr).
- `navigate` AppContext+fetcher is not None path: covered by 852 tests (unchanged).
- `navigate` AppContext+fetcher=None, page=None dry-run: NEWLY COVERED by 877 `test_navigate_returns_url_when_appcontext_no_fetcher_no_page`.
- `read_text` with page is not None (Playwright path): covered by 837 `test_read_text_calls_extract_content_with_page_html_and_url`.
- All significant branches exercised. PASS.

#### 5.7 Builder Process Quality

1 `## Builder Notes` section. 0 retries. CLEAN.

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: click/type/select raise ToolError | `server.py` lines 108–142: `if page is not None: ...; else: raise ToolError(_MSG_NO_PAGE)` verified for all three. | PASS |
| AC2: read_text/snapshot return last_content | `server.py` read_text lines 145–153: `return getattr(app_ctx, "last_content", "")`. snapshot lines 156–163: same. | PASS |
| AC3: 836 click/type/select use mock page | `test_mcp_browser_836.py` `TestFromAC_AllToolsCallableWithCtx`: `_make_mcp_ctx_with_mock_page()` helper verified in code. | PASS |
| AC4: 850 click/type/select use mock page | `test_mcp_browser_ctx_850.py` `TestFromAC_CtxParameterOnAllTools`: inline `AppContext(page=mock_page)` verified. | PASS |
| AC5: 837 read_text/snapshot assert str | `test_mcp_browser_session_837.py`: both tests assert `isinstance(result, str)` verified. | PASS |
| AC6: 853 fallback + navigate URL | `test_mcp_browser_session_853.py`: read/snapshot assert `isinstance(str)`, navigate asserts `result == _ALLOWED_URL`. Code read confirms. | PASS |
| AC7: 854 fallback + navigate URL | `test_mcp_browser_session_854.py`: same pattern. Code read confirms. | PASS |
| AC8: All mcp_browser tests pass | `pytest_results.txt` (4220 passed, 288 failed): zero `test_mcp_browser_*` entries in failure list. | PASS |
| AC9: ruff clean | Builder self-report; not independently verified (QR unavailable). | UNVERIFIED |

### Deductions

- −0.05: Quality-runner could not execute independently (WMI/xdist environment failure); test evidence from pre-existing `pytest_results.txt` used
- −0.03: Ruff not independently verified with QR

### Verdict

Confidence: **0.92 → PASS**

`PASS #877 → docs | confidence .92`
[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | Task establishes page=None contract for read_text/snapshot/navigate. copilot-instructions.md has no mcp-browser section — nothing to update. |
| 2 | Module docstrings | Yes | Updated | server.py not modified by builder (implementation pre-existed from #871), but task AC2 finalizes the fallback contract. `read_text` and `snapshot` docstrings updated to document last_content fallback. Commit `35a0eb08`. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | CLI changes | No | N/A | MCP tools, not CLI commands. |
| 5 | Research doc | No | N/A | No research doc linked or produced. |

### Files Updated

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — `read_text` and `snapshot` docstrings (commit `35a0eb08`)

### Scratch Files

No `.owlbear/scratch/877-*` files found. Nothing to clean.

### Review Evidence Pre-flight

`## Review Evidence` section present. Confidence 0.92 → PASS noted by reviewer.
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: click/type/select raise ToolError when page=None | server.py L140, L154, L166: `raise ToolError(_MSG_NO_PAGE)` | PASS |
| AC2: read_text/snapshot return last_content fallback | server.py L181, L192: `getattr(app_ctx, "last_content", "")` | PASS |
| AC3: 836 click/type/select use mock page | test_mcp_browser_836.py `_make_mcp_ctx_with_mock_page()` helper, 3 tests pass | PASS |
| AC4: 850 click/type/select use mock page | test_mcp_browser_ctx_850.py inline `AppContext(page=mock_page)`, 3 tests pass | PASS |
| AC5: 837 read_text/snapshot accept string return | test_mcp_browser_session_837.py both assert `isinstance(result, str)` | PASS |
| AC6: 853 read_text/snapshot/navigate fallback | test_mcp_browser_session_853.py: str assertions + `result == _ALLOWED_URL` for navigate | PASS |
| AC7: 854 read_text/snapshot/navigate fallback | test_mcp_browser_session_854.py: same pattern confirmed | PASS |
| AC8: All mcp_browser tests pass | Full suite 4261 passed, 323 failed; zero mcp_browser failures | PASS |
| AC9: ruff clean | `ruff check serve/mcp-browser/ tests/test_mcp_browser_*.py` all checks passed | PASS |

### Test Results

- pytest: 4261 passed, 323 failed, 8 skipped (zero mcp_browser failures; 323 are pre-existing unrelated)
- ruff: clean for all task-scoped files; 1 unrelated E501 in kanban/engine.py

### Architect Quality: 5/5

Exceptionally specific AC: 9 lines naming exact test classes, methods, and behaviors. Self-identified gap in AC6 navigate and documented it in architecture notes. Clarified "current behavior" ambiguity. Builder needed zero improvisation.

### Deduction Breakdown

- No deductions. All 9 AC lines have specific evidence. Reviewer section present and detailed. Full suite clean for task scope. Lint independently verified.

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 07937870 | chore | kanban task 877 | #877 |
