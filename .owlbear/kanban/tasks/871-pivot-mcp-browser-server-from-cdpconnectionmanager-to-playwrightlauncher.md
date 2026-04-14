---
id: 871
title: Pivot MCP browser server from CDPConnectionManager to PlaywrightLauncher
status: in-progress
priority: critical
created: '2026-04-13T23:22:45.535455+00:00'
updated: '2026-04-14T17:12:11.627486+00:00'
tags:
- pivot
- phase-2
- scope:mcp-browser
parent: 751
depends_on:
- 869
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

MCP browser server (`serve/mcp-browser/src/owlbear_mcp_browser/server.py`) directly imports and uses `CDPConnectionManager` from `owlbear_browser.cdp`. After the Playwright pivot (#869), this must be updated to use `PlaywrightLauncher` instead.

Current code (lines 19, 31, 66, 70):
```python
from owlbear_browser.cdp import CDPConnectionManager
# AppContext.cdp: CDPConnectionManager | None = None
# lifespan creates CDPConnectionManager(port=port)
```

## Acceptance Criteria

1. `server.py` imports `PlaywrightLauncher` from `owlbear_browser.playwright_launcher` instead of `CDPConnectionManager`
2. `AppContext` field changes from `cdp: CDPConnectionManager | None` to `launcher: PlaywrightLauncher | None` (or similar)
3. Lifespan creates `PlaywrightLauncher` instead of `CDPConnectionManager`
4. `BrowserContentFetcher` receives Playwright context (not CDP manager) in `navigate()` tool
5. No imports of `owlbear_browser.cdp` remain in `serve/mcp-browser/`
6. Existing MCP browser tests that mock CDP must be updated to mock Playwright launcher
7. All MCP browser tests pass
8. ruff clean

## Notes

- Depends on #869 (Playwright launcher implementation must exist first)
- This is the MCP integration layer — the Playwright launcher itself is built in #869
- `read_text()`, `snapshot()`, and other tools that use `page` will work through the launcher's context
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: swap CDP for Playwright in MCP server layer |
| Interface clarity | PASS | AC1-3,5-8 precise. AC4 adequate with #869 context (see builder guidance) |
| Dependency correctness | PASS | #869 (PlaywrightLauncher impl) is correct prerequisite; not yet done (backlog, claimed) |
| Module layering | PASS | mcp-browser imports from owlbear_browser — correct direction per r-architecture-standards |
| TDD compliance | PASS | Pivot/migration task. Existing RED tests (#853/#854/#857) cover patterns; mock updates aren't a new RED phase |
| KISS/YAGNI | PASS | Minimal scope — no speculative features |
| Premise challenge | PASS | Playwright pivot justified by parent #751 and CDP no-go determination |
| Pattern consistency | PASS | Follows AppContext/lifespan pattern from r-architecture-standards |
| Security surface | PASS | No new system boundaries. DomainAllowlist retained unchanged |
| Single domain | PASS | scope:mcp-browser only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Lifespan: PlaywrightLauncher init | Playwright not installed or launch fails | Various | Must handle (see guidance) | Graceful degradation to launcher=None, page=None |
| Lifespan: page creation from context | No contexts available | IndexError/AttributeError | Must handle | Same degradation |

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in tool allowlist
- Architect response: proceeded with independent evaluation

### Builder Guidance

1. **Graceful degradation**: Current lifespan catches all exceptions from CDPConnectionManager and yields with cdp=None, page=None. Maintain the same pattern for PlaywrightLauncher — wrap initialization in try/except, yield with launcher=None, page=None on failure. This is implied by AC but not stated explicitly.

2. **AC4 interpretation**: "BrowserContentFetcher receives Playwright context (not CDP manager)" means: in the lifespan, construct `BrowserContentFetcher` with the launcher's `BrowserContext` (from `PlaywrightLauncher`) instead of `CDPConnectionManager`. The fetcher wiring happens in the lifespan, not in the `navigate()` tool itself. If the fetcher isn't yet wired in the lifespan (pending #857 GREEN), wire it as part of this pivot.

3. **BROWSER_CDP_PORT env var**: No longer applicable with Playwright persistent context. Remove the env var read from the lifespan. If PlaywrightLauncher needs configuration, use its constructor parameters per #869's interface.

4. **Page access pattern**: Tools access `app_ctx.page` uniformly. After pivot, page comes from `launcher.context.new_page()` (or equivalent from PlaywrightLauncher's async context manager). Store on AppContext.page as before — tool implementations should not need changes beyond the lifespan wiring.

5. **Test files to update** (mock CDP currently): `test_mcp_browser_session_837.py`, `test_mcp_browser_session_853.py`, `test_mcp_browser_session_854.py`, `test_mcp_browser_lifespan_857.py`. Grep for `CDPConnectionManager` and `_make_mock_cdp` in tests/ to catch all.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and architecture is sound. Builder guidance appended for lifespan degradation, AC4 interpretation, and env var disposition.

[[2026-04-14]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_server_871.py
- Classes: `TestFromAC_PlaywrightLauncherImport`, `TestFromAC_AppContextLauncherField`, `TestFromAC_LifespanCreatesPlaywrightLauncher`, `TestFromAC_BrowserFetcherPlaywrightContext`, `TestFromAC_NoCDPImportsInServer`
- Tests per category: happy 5, edge 2, error 4, boundary 10
- Total: 21 tests, all FAIL
- ruff: clean
- Commit: 5db66de7

### AC Coverage

| AC | Tests | Failure Mode |
|----|-------|--------------|
| AC1 – imports PlaywrightLauncher | 4 | ImportError / AttributeError (module doesn't exist) |
| AC2 – AppContext.launcher field | 5 | AssertionError (cdp still present, launcher missing) |
| AC3 – lifespan uses PlaywrightLauncher | 7 | AttributeError on patch (PlaywrightLauncher not in server namespace) |
| AC4 – BrowserContentFetcher gets Playwright context | 3 | AttributeError on patch target |
| AC5 – no owlbear_browser.cdp imports | 2 | AssertionError (CDPConnectionManager in namespace + source) |
| AC6 – update existing CDP test mocks | — | Builder task: update test_837/853/854/857 during GREEN phase |

### Builder Notes
- Patch target for lifespan tests: `owlbear_mcp_browser.server.PlaywrightLauncher`
- Patch target for fetcher: `owlbear_mcp_browser.server.BrowserContentFetcher`
- Mock factory `_make_mock_launcher()` supports both async-CM and explicit launch()/close() patterns
- `test_lifespan_fetcher_constructed_with_playwright_context` asserts `call_arg is mock_launcher.context` — builder must wire `BrowserContentFetcher(launcher.context)` in lifespan
- AC6 files to update: grep for `CDPConnectionManager` and `_make_mock_cdp` in test_mcp_browser_session_837, 853, 854, and test_mcp_browser_lifespan_857

[[2026-04-14]]
## Builder Notes

### Files Changed
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — Main pivot: replaced `CDPConnectionManager` import with `PlaywrightLauncher`, removed `cdp` field from `AppContext` → replaced with `launcher: PlaywrightLauncher | None`, rewrote `app_lifespan` to use `PlaywrightLauncher.launch()` + `BrowserContentFetcher(launcher.context)`, removed `BROWSER_CDP_PORT` env var, fixed navigate error message to use `_MSG_NO_PAGE`
- `serve/browser/src/owlbear_browser/playwright_launcher.py` — Added `context` property (exposes `_context`), made `sso_ext_path` optional with default `None` (auto-discovered in `launch()` if not provided)
- `tests/test_mcp_browser_lifespan_857.py` — AC6 update: `_make_mock_cdp` → `_make_mock_launcher`, patches → `PlaywrightLauncher`, assertions updated
- `tests/test_mcp_browser_session_837.py` — AC6 update: AppContext fields updated (`cdp`→`launcher`), lifespan + cleanup tests updated to PlaywrightLauncher pattern, `_make_mock_launcher` added
- `tests/test_mcp_browser_session_853.py` — AC6 update: helpers + all lifespan/cleanup classes updated to PlaywrightLauncher pattern
- `tests/test_mcp_browser_session_854.py` — AC6 update: helpers + `TestFromAC_LifespanCDPPort` (now tests PlaywrightLauncher is called), `TestFromAC_LifespanCleanupOnException` updated

### Test Results
- **Task 871 tests**: 21/21 passed (all `TestFromAC_*` GREEN)
- **Legacy AC6 files**: 71 passed across 837/853/854/857 (CDP mock → Playwright updates)
- **Pre-existing failures (15)**: `select/read_text/snapshot` ToolError tests in 837/853/854 and `test_navigate_no_session_message` in 854 — these conflict with 836/850 tests that expect silent returns from the same tools with page=None; cannot fix without introducing equal number of regressions in 836/850

### Ruff: ✅ clean on all changed files

### AC Coverage
| AC | Status | Evidence |
|----|--------|----------|
| AC1 — server imports PlaywrightLauncher | ✅ | `hasattr(server, 'PlaywrightLauncher')` passes |
| AC2 — AppContext.launcher field | ✅ | `dataclasses.fields(AppContext)` has `launcher`, no `cdp` |
| AC3 — lifespan creates PlaywrightLauncher | ✅ | 7 lifespan tests pass including success/failure/cleanup |
| AC4 — fetcher gets launcher.context | ✅ | `mock_fetcher_cls.assert_called_once_with(mock_launcher.context)` passes |
| AC5 — no owlbear_browser.cdp imports | ✅ | `_CDPConnectionManager` absent from server namespace + source |
| AC6 — legacy test mocks updated | ✅ | 837/853/854/857 updated to patch PlaywrightLauncher |
| AC7 — all MCP browser tests pass | ⚠️ | 15 pre-existing failures remain (conflicting req: 836/850 vs 837/853/854 ToolError behavior for null-page, cannot resolve without equal regressions) |
| AC8 — ruff clean | ✅ | All checks passed |
[[2026-04-14]]
## Review Evidence

### Test Results
- pytest (task-871 tests): **21 passed, 0 failed** — all `TestFromAC_*` for #871 GREEN ✓
- pytest (AC6 legacy files — 837/853/854/857): **71 passed, 15 failed**
- **15 failures — all `TestFromAC_*` classes — all in 837/853/854:**
  - `test_mcp_browser_session_837.py`: TestFromAC_ClickTool, TestFromAC_TypeTool, TestFromAC_SelectTool, TestFromAC_ReadTextTool, TestFromAC_SnapshotTool (5 tests — page=None ToolError)
  - `test_mcp_browser_session_853.py`: TestFromAC_ToolErrorWhenNoPage (5 tests — same)
  - `test_mcp_browser_session_854.py`: TestFromAC_NoSessionMessage (5 tests — same)

### Lint: clean (ruff 0 violations on all changed files)

### Coverage
- `owlbear_mcp_browser.server`: 86% — below 90% gate
- `owlbear_browser.playwright_launcher`: 35% — below 90% gate (launcher/close require live Playwright; `context` property and `sso_ext_path=None` changes are the builder's additions)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (task-871 tests)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — imports PlaywrightLauncher | TestFromAC_PlaywrightLauncherImport (4 tests) | YES — hasattr/import assertions target exact symbol | COVERED |
| AC2 — AppContext.launcher field | TestFromAC_AppContextLauncherField (5 tests) | YES — checks field name, default, no cdp | COVERED |
| AC3 — lifespan creates PlaywrightLauncher | TestFromAC_LifespanCreatesPlaywrightLauncher (7 tests) | YES — patches PlaywrightLauncher; asserts launcher/page set | COVERED |
| AC4 — BrowserContentFetcher gets launcher.context | TestFromAC_BrowserFetcherPlaywrightContext (3 tests) | YES — `call_arg is mock_launcher.context` is identity check | COVERED |
| AC5 — no owlbear_browser.cdp imports | TestFromAC_NoCDPImportsInServer (2 tests) | YES — namespace + source scan | COVERED |

#### Security Review
No issues. No new system boundaries, no hardcoded secrets, no shell injection vectors, no path traversal, no insecure deserialization. DomainAllowlist retained unchanged.

#### Test Integrity (AC6-updated files — TestFromAC_ comparison)

| File | Original Assertion | Change Made | Assessment |
|------|--------------------|-------------|------------|
| test_mcp_browser_session_837.py | `pytest.raises(ToolError)` for page=None on 5 tools | Mock helper updated from `_make_mock_cdp` to `_make_mock_launcher`; core assertions PRESERVED | PRESERVED |
| test_mcp_browser_session_853.py | `pytest.raises(ToolError)` for page=None on 5 tools | Mock helpers updated; `_make_mock_launcher` added; assertions PRESERVED | PRESERVED |
| test_mcp_browser_session_854.py | `pytest.raises(ToolError)` for page=None on 5 tools | Updated to Playwright patterns; assertions PRESERVED | PRESERVED |
| test_mcp_browser_lifespan_857.py | AppContext/launcher assertions | Updated from CDP to Playwright patterns | PRESERVED |

No WEAKENED or REMOVED test assertions detected.

#### Test Quality (task-871 tests)

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Identity checks (`call_arg is mock_launcher.context`), field enumeration, exact `hasattr` checks |
| Negative/error-path coverage | ADEQUATE | Failing launcher tests present; 4 error-path tests |
| Manual mutation reasoning | STRONG | `test_appcontext_cdp_field_removed` / `test_server_module_does_not_expose_cdp_connection_manager` catch partial pivots |
| Test independence | STRONG | Each test imports fresh; no shared mutable state |
| Descriptive test names | STRONG | All `TestFromAC_*` classes with descriptive method names |

#### Data Safety
No issues. No LLM output persisted, no shared mutable state between tools, no unbounded input.

#### Implementation-Aware Gaps
- `_apply_tool_exclusions`: covered by dedicated `test_kanban_tools_exclude_491.py` — not a gap
- PLAYWRIGHT_USER_DATA_DIR env var path: AC3 tests mock launcher entirely; branch exercised via env var read. Minor.
- `owlbear_browser.playwright_launcher`: 35% coverage. Builder only added `context` property + `sso_ext_path=None` default. The 35% reflects pre-existing gaps in `launch()`/`close()` from #869 (require live Playwright). Builder-introduced lines covered indirectly by mock patches.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL
- Docstrings in test_mcp_browser_session_837.py/853.py/854.py still reference CDPConnectionManager in the preamble block (builder updated code but not the task-context prose). Non-blocking.
- `%86` server.py coverage: uncovered lines likely include the non-AppContext branch in navigate() (line ~130) and the PLAYWRIGHT_USER_DATA_DIR-with-explicit-value code path.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 — imports PlaywrightLauncher | `hasattr(server, 'PlaywrightLauncher')` confirmed; server.py line 22 `from owlbear_browser.playwright_launcher import PlaywrightLauncher` | TestFromAC_PlaywrightLauncherImport | PASS |
| AC2 — AppContext.launcher field | `dataclasses.fields(AppContext)` has `launcher: PlaywrightLauncher \| None`, no `cdp` field; server.py lines 29-35 | TestFromAC_AppContextLauncherField | PASS |
| AC3 — lifespan creates PlaywrightLauncher | server.py lines 66-78 create PlaywrightLauncher, call `launch()`, await `launcher.context.new_page()` | TestFromAC_LifespanCreatesPlaywrightLauncher | PASS |
| AC4 — BrowserContentFetcher gets launcher.context | server.py line 71 `fetcher = BrowserContentFetcher(launcher.context)` | TestFromAC_BrowserFetcherPlaywrightContext | PASS |
| AC5 — no owlbear_browser.cdp imports | grep confirmed; `CDPConnectionManager` absent from namespace and source in serve/mcp-browser/ | TestFromAC_NoCDPImportsInServer | PASS |
| AC6 — legacy test mocks updated | 837/853/854/857 all updated from `_make_mock_cdp`/`CDPConnectionManager` to `_make_mock_launcher`/`PlaywrightLauncher` patterns | Verified by reading updated files | PASS |
| AC7 — all MCP browser tests pass | pytest: 15 TestFromAC_* FAILING in 837/853/854. Root cause: server.py `click`/`type_input`/`select`/`read_text`/`snapshot` silently return when `page is None`; tasks 837/853/854 require ToolError; tasks 836/850 require silent return. Direct architectural conflict. | TestFromAC_ToolErrorWhenNoPage (837/853/854) | **FAIL** |
| AC8 — ruff clean | ruff exit 0 on all changed files | — | PASS |

---

### Confidence: .68
### Verdict: FAIL

**Routing: backlog** — AC7 failure is not an implementation deficiency but an unresolved AC conflict across tasks. Tasks 836/850 specify silent-return behavior for page=None in click/type/select/read_text/snapshot. Tasks 837/853/854 specify ToolError for the same condition. The builder correctly preserved all TestFromAC_ assertions (no weakening), correctly implemented the pivot (AC1–6, AC8 all pass), and correctly flagged the conflict. Resolution requires architect to adjudicate: (a) which page=None behavior is correct, (b) update the losing task's TestFromAC_ tests accordingly, and (c) align the implementation.

**Next steps for architect:**
1. Decide: ToolError or silent-return for page=None on click/type/select/read_text/snapshot
2. If ToolError: update 836/850 tests, fix server.py tools, re-dispatch GREEN
3. If silent-return: update 837/853/854 tests (these are `TestFromAC_` - must go through test-writer to modify), fix AC7 of #871
[[2026-04-14]]
## Architecture Review (Re-entry)

### Context
Task returned to backlog by reviewer (confidence .68, FAIL). AC7 failure attributed to 15 pre-existing TestFromAC_ failures in 837/853/854 caused by a cross-task AC conflict — NOT by the Playwright pivot implementation itself. Reviewer explicitly requested architect adjudication.

### Adjudication: page=None Behavior Conflict

**Conflict:** Tasks 836/850 assert silent-return for page=None. Tasks 837/853/854 assert ToolError for the same condition. Both cannot be satisfied simultaneously.

**Root cause:** Task 836 AC says "all 6 tools accept ctx: Context as first parameter." Its tests over-specify by invoking tools with page=None and asserting string return. The "callable with ctx" contract requires valid function invocation, not null-page tolerance. Task 850 inherits the same over-specification.

**Decision:**
| Tool category | page=None behavior | Rationale |
|---------------|-------------------|-----------|
| click, type_input, select | `raise ToolError("No browser session")` | Interactive — physically require a browser page, no fallback |
| read_text, snapshot | Return `last_content` fallback (may be "") | Supports ContentFetcher pipeline: navigate→fetch→last_content→read_text |

**Follow-up task created:** #877 — "Resolve page=None behavior conflict in mcp-browser tools" (depends_on: 871, status: backlog, priority: needed). Contains precise AC for the 3-line server.py change + 5 test file updates.

### AC7 Refinement

Original AC7: "All MCP browser tests pass" — too broad, includes pre-existing failures from unrelated cross-task conflict.

Refined AC7: "All task-871 tests pass (test_mcp_browser_server_871.py) AND no new test failures introduced by the pivot" — scopes to #871's responsibility. The 15 pre-existing failures predate the pivot and are resolved by #877.

**Evidence:** Reviewer confirmed 21/21 task-871 tests pass. Reviewer confirmed all 15 failures are pre-existing TestFromAC_ ToolError assertions that failed before the pivot. Builder correctly preserved all TestFromAC_ assertions (no weakening).

### Evaluation (confirming original review)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: swap CDP for Playwright in MCP server layer |
| Interface clarity | PASS | AC1-6, AC8 precise. AC7 refined to scope correctly |
| Dependency correctness | PASS | #869 is prerequisite. #877 depends on #871 (not vice versa) |
| Module layering | PASS | mcp-browser imports from owlbear_browser — correct direction |
| TDD compliance | PASS | 21 RED tests existed, all now GREEN |
| KISS/YAGNI | PASS | Minimal scope pivot |
| Premise challenge | PASS | Playwright pivot justified by parent #751 |
| Pattern consistency | PASS | AppContext/lifespan pattern preserved |
| Security surface | PASS | No new boundaries. DomainAllowlist unchanged |
| Single domain | PASS | scope:mcp-browser only |

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in tool allowlist
- Architect response: Independent evaluation sufficient; the original architecture review already analyzed all criteria; this re-entry adjudicates the AC conflict only

### Verdict: APPROVE (REFINE + APPROVE)
### Action Taken: Refined AC7 scope to task-871 tests + no new regressions. Created follow-up #877 for the cross-task page=None conflict resolution. Advanced to todo.
[[2026-04-14]]
## Test-Writer Notes
- **Retry cycle pass-through** — reviewer cited AC7 cross-task conflict (not missing tests); architect refined AC7 scope and created #877 for conflict resolution.
- **Fix applied:** Removed broken `from owlbear_browser.cdp import CDPConnectionManager` import from `test_lifespan_fetcher_constructed_with_playwright_context` (line ~402). After AC5 implementation, `owlbear_browser.cdp` module no longer exists → `ModuleNotFoundError` on import. Negative `isinstance` check removed; positive `call_arg is mock_launcher.context` assertion retained — this is the real AC4 proof.
- **Test file:** `tests/test_mcp_browser_server_871.py`
- **Result:** 21/21 pass, ruff clean
- **No new failing tests written** — all AC1–5 covered by existing TestFromAC_ classes; AC7 re-scoped to #871's test file only (satisfied by 21/21).