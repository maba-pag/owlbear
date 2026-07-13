---
id: 849
title: 'RED: Update test_mcp_browser_775 AC3 tests for ctx: Context parameter'
status: archived
priority: medium
created: '2026-04-12T12:52:52.072571+00:00'
updated: '2026-04-14T01:00:19.099043+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-red
parent: 836
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Update 5 AC3 tests in TestFromAC_NavigateToolError to pass a mock `ctx: Context` with `DomainAllowlist` via `lifespan_context` instead of relying on env var reads.

**Source:** .owlbear/research/836-mcp-browser-ctx-refactor.md §3b

**AC:**

- [ ] Add `_make_app_ctx(domains)` and `_make_mcp_ctx(app_ctx)` helpers following kanban test pattern
- [ ] All 5 AC3 tests call `navigate(ctx, url=...)` with mock ctx carrying appropriate allowlist
- [ ] Tests fail initially (navigate() still has old signature) — RED phase
- [ ] ruff clean

**Affected files:** `tests/test_mcp_browser_775.py`
[[2026-04-12]]

## Research

- Research doc: .owlbear/research/836-mcp-browser-ctx-refactor.md §3b (parent task doc covers this task)
- Sources: 8 studied in parent doc, 6 high-relevance; validated current codebase state
- Recommendation: Follow established _make_app_ctx/_make_mcp_ctx pattern from kanban/knowledge/memory tests. Update 5 AC3 tests to call navigate(ctx, url=...) with mock ctx carrying DomainAllowlist. (confidence: .92)
- Follow-up tasks created: none needed — task AC is complete and actionable
- Decision requests: none

## Challenge Results

- Challenger: FALLBACK — trivial T1 refactor following established convention, single viable approach
- Confidence in original: .92
- Key challenges: none — pattern dictated by 3 existing MCP server test suites
- Researcher response: N/A

## Validation Notes

- server.py L68: navigate(url: str) still has old signature → RED tests will correctly fail with TypeError on navigate(ctx, url=...)
- Pattern template: tests/test_mcp_kanban_create_task_475.py L68-75
- For browser: _make_app_ctx(domains: list[str]) → AppContext(allowlist=DomainAllowlist(domains=domains))
- 4 of 5 tests should remove os.environ patches entirely; test_navigate_does_not_raise should also drop the app_lifespan context manager
[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: update 5 AC3 tests to use ctx mock pattern |
| Interface clarity | PASS | All 4 AC lines specific and verifiable; _make_app_ctx(domains) signature specified in validation notes |
| Dependency correctness | PASS | No dependencies listed, none needed — standalone test-file update |
| Module layering | PASS | Test-only changes, no production code modified |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope, following established pattern |
| Premise challenge | PASS | Required before GREEN #850 can add ctx to navigate() |
| Pattern consistency | PASS | Exact _make_app_ctx/_make_mcp_ctx pattern used in 15+ test files across kanban/knowledge/memory servers |
| Security surface | PASS | No new boundaries; test mocks only |
| Single domain | PASS | scope:mcp-browser only |

### Codebase Evidence

- server.py L68: `navigate(url: str)` — old signature confirmed → RED tests calling `navigate(ctx, url=...)` will fail with TypeError
- AppContext(allowlist: DomainAllowlist) already defined at server.py L22-25
- Pattern template: tests/test_mcp_kanban_create_task_475.py L68-75 (and 15+ other test files)
- Browser variant: `_make_app_ctx(domains: list[str]) → AppContext(allowlist=DomainAllowlist(domains=domains))`
- 5 tests verified in TestFromAC_NavigateToolError: test_navigate_raises_tool_error_for_blocked_domain, test_navigate_raises_tool_error_when_allowlist_is_empty, test_navigate_raises_tool_error_when_domain_not_configured, test_navigate_does_not_raise_for_allowlisted_domain, test_navigate_raises_tool_error_for_subdomain_not_in_allowlist
- 4 of 5 tests should remove os.environ patches; test_navigate_does_not_raise should also drop the app_lifespan context manager

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Add _make_app_ctx(domains) and_make_mcp_ctx(app_ctx) helpers | Verifiable, pattern-consistent with 15+ test files | None |
| AC2: All 5 AC3 tests call navigate(ctx, url=...) | Verifiable, 5 tests identified and confirmed | None |
| AC3: Tests fail initially (RED phase) | Verifiable, server.py L68 still has navigate(url: str) | None |
| AC4: ruff clean | Verifiable, standard gate | None |

### Challenge Results

- Challenger: FALLBACK — trivial T1 refactor following established convention, single viable approach
- Architect response: accepted

### Verdict: APPROVE

### Action Taken: Advanced to todo. All AC lines precise and verifiable. Pattern dictated by 15+ existing test files

[[2026-04-12]]

## Test-Writer Notes

**File:** `tests/test_mcp_browser_775.py`
**Class updated:** `TestFromAC_NavigateToolError`

### Changes made

- Added module-level imports: `DomainAllowlist` from `owlbear_mcp_browser.allowlist`, `AppContext` from `owlbear_mcp_browser.server`
- Added `_make_app_ctx(domains: list[str]) -> AppContext` helper — returns `AppContext(allowlist=DomainAllowlist(domains=domains))`
- Added `_make_mcp_ctx(app_ctx: AppContext) -> MagicMock` helper — wires `app_ctx` into `ctx.request_context.lifespan_context`
- Replaced all 5 AC3 tests: removed `os.environ` patches, removed `app_lifespan` context manager from `test_navigate_does_not_raise`, each test now passes `ctx` mock via `_make_mcp_ctx(_make_app_ctx([...]))` and calls `navigate(ctx, url=...)`

### Test categories

| Category | Count |
|----------|-------|
| Happy path | 1 (`test_navigate_does_not_raise_for_allowlisted_domain`) |
| Error path | 3 (blocked domain, empty allowlist, unset allowlist) |
| Boundary | 1 (subdomain not in allowlist) |
| **Total** | **5** |

### Fail verification

pytest `tests/test_mcp_browser_775.py::TestFromAC_NavigateToolError` — **5 failed, 0 passed**
Failure: `TypeError: navigate() got multiple values for argument 'url'` (navigate still has old `(url: str)` signature)
ruff: `All checks passed!`

### AC coverage

| AC | Tests |
|----|-------|
| Add `_make_app_ctx(domains)` and `_make_mcp_ctx(app_ctx)` helpers | ✅ Both helpers added |
| All 5 AC3 tests call `navigate(ctx, url=...)` | ✅ All 5 updated |
| Tests fail initially (RED phase) | ✅ All 5 fail with TypeError |
| ruff clean | ✅ All checks passed |
[[2026-04-13]]

## Builder Notes

**Status:** DONE — previous builder session added `ctx: Context` to `navigate()` in server.py

### Files changed

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — `navigate(ctx: Context, url: str)`, uses `ctx.request_context.lifespan_context.allowlist` (no env read)

### Test results

- `tests/test_mcp_browser_775.py`: **25 passed, 0 failed**
- `TestFromAC_NavigateToolError` (5 AC3 tests): all pass — blocked domain, empty allowlist, unconfigured allowlist, allowlisted domain (no raise), subdomain boundary

### Lint

- `ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py tests/test_mcp_browser_775.py`: **All checks passed**

### Coverage

- `owlbear_mcp_browser.server`: **67%** — navigate() paths fully covered; uncovered lines are click/type_input/select/read_text/snapshot tools (scope of #850 GREEN task, not #849)

### Evidence

- All 5 AC3 tests pass (navigate allowlist paths)
- ruff clean
- 25/25 tests pass in test_mcp_browser_775.py
- navigate() reads lifespan allowlist from ctx, no per-call env read

### Retry context

Previous builder session already added `ctx: Context` to `navigate()`. Tests were already green on arrival; gate checks confirm no regressions.
[[2026-04-13]]

## Review Evidence

### Tests

pytest `tests/test_mcp_browser_775.py`: **25 passed, 0 failed** (run independently via quality-runner)

### Lint

ruff `serve/mcp-browser/src/owlbear_mcp_browser/server.py` + `tests/test_mcp_browser_775.py`: **clean**

### Coverage

`owlbear_mcp_browser.server`: **67%** — navigate() allowlist/fetcher paths fully covered; uncovered lines are page-based tools (scope of #850+, not #849)

### Changed Files

`get_changed_files` (staged+unstaged): neither `tests/test_mcp_browser_775.py` nor `serve/mcp-browser/src/owlbear_mcp_browser/server.py` appear in the working-tree diff — both changes are already committed. GREEN work (ctx on navigate + AppContext fields) was in place before review.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Add `_make_app_ctx(domains)` and `_make_mcp_ctx(app_ctx)` helpers | Both helpers present at lines 43–50 of test_mcp_browser_775.py, following established kanban/knowledge/memory pattern | ✅ PASS |
| AC2: All 5 AC3 tests call `navigate(ctx, url=...)` with mock ctx carrying appropriate allowlist | Confirmed at lines 163–222: all 5 tests construct ctx via `_make_mcp_ctx(_make_app_ctx([...]))` or `_make_mcp_ctx(AppContext(...))` and call `navigate(ctx, url=...)` | ✅ PASS |
| AC3: Tests fail initially (RED phase) | Test-writer reports 5 failed, failure mode `TypeError: navigate() got multiple values for argument 'url'` — consistent with old `navigate(url: str)` receiving `ctx` as positional plus `url=` as keyword | ✅ PASS |
| AC4: ruff clean | quality-runner confirmed ruff exit 0 | ✅ PASS |

### Assertion Strength

- 4 error-path tests: `pytest.raises(ToolError)` — STRONG; would fail if no exception raised or wrong type raised
- 1 happy-path test: no-raise check only (no return-value assertion) — ADEQUATE for "verify no exception" contract

### Test Quality Notes

- Two tests (`test_navigate_raises_tool_error_when_allowlist_is_empty` and `test_navigate_raises_tool_error_when_domain_not_configured`) both use `_make_app_ctx([])` + any URL — functionally identical. Minor duplication; architect accepted these as distinct cases in the AC. Deduct .02.
- Happy-path test uses `fetcher=mock_fetcher` — appropriate, because page=None means navigate() falls through to the fetcher path. The mock prevents a None-fetcher no-op from masking the allowlist check.
- TestFromAC_NavigateToolError modifications improve tests (stronger isolation, no env-var dependency) — not a weakening. ✅

### Deductions

- .02 for two near-duplicate empty-allowlist tests

### Verdict

**PASS #849 → docs | confidence .93**
[[2026-04-13]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `navigate()` signature changed to `navigate(ctx: Context, url: str)`. `copilot-instructions.md` (80 lines) covers only branch/project identity — no MCP tool API inventory to update. No entry warranted. |
| 2 | Module docstrings | Yes | Verified | `server.py` fully read (L1–200). All public symbols have accurate docstrings: module, `AppContext`, `app_lifespan`, `navigate`, `click`, `type_input`, `select`, `read_text`, `snapshot`. `navigate` docstring `"""Navigate the browser to *url*."""` remains accurate post-signature change. No edits needed. |
| 3 | External attribution | No | N/A | Task used internal `_make_app_ctx/_make_mcp_ctx` pattern from kanban/knowledge/memory test files — no external sources. |
| 4 | CLI changes | No | N/A | MCP tool, not CLI. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/836-mcp-browser-ctx-refactor.md` exists; linked in task body under `## Research`. Follow-up tasks noted as none needed. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `849-*` files found in `.owlbear/scratch/`)
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Add _make_app_ctx(domains) and_make_mcp_ctx(app_ctx) helpers | Both present at test_mcp_browser_775.py L43-50, follow kanban/knowledge pattern | PASS |
| AC2: All 5 AC3 tests call navigate(ctx, url=...) with mock ctx | Confirmed at L163-222: all 5 use _make_mcp_ctx(_make_app_ctx([...])) and call navigate(ctx, url=...) | PASS |
| AC3: Tests fail initially (RED phase) | Test-writer verified: 5 failed with TypeError (old navigate(url: str) signature) | PASS |
| AC4: ruff clean | ruff check on test file: clean | PASS |

### Test Results

- pytest tests/test_mcp_browser_775.py: 24 passed, 1 failed (test_navigate_does_not_raise_for_allowlisted_domain)
- Failure cause: cross-task regression from b1795c20 (added page guard to navigate after #849 committed). Already tracked as #861.
- Full suite: 355 failed, 4202 passed. Failures are pre-existing (kanban AppContext changes, missing lint-changed.ps1, browser session tests), none introduced by #849.
- ruff: 1 violation in engine.py (unrelated to task scope)

### Reviewer Evidence

Present, detailed, PASS verdict at .93. Code-level findings trusted.

### Upstream Commits Verified

- Test file: 54e7679b, 0de9a771 (committed)
- Server file: 4c5c7daa feat(mcp-browser): add ctx: Context to all 6 tools (#836) (committed)

### Architect Quality: 4/5

AC lines specific, verifiable, and pattern-consistent. Minor gap: AC didn't anticipate builder would also implement GREEN, but this was handled cleanly.

### Deduction Breakdown

- 1 test failure in task scope (cross-task regression from b1795c20, tracked as #861): -.05

### Confidence: .95

### Action: archive
