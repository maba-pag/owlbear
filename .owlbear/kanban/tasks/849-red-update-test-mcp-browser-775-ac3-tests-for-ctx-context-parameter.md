---
id: 849
title: 'RED: Update test_mcp_browser_775 AC3 tests for ctx: Context parameter'
status: in-progress
priority: important
created: '2026-04-12T12:52:52.072571+00:00'
updated: '2026-04-12T16:56:07.281133+00:00'
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
| AC1: Add _make_app_ctx(domains) and _make_mcp_ctx(app_ctx) helpers | Verifiable, pattern-consistent with 15+ test files | None |
| AC2: All 5 AC3 tests call navigate(ctx, url=...) | Verifiable, 5 tests identified and confirmed | None |
| AC3: Tests fail initially (RED phase) | Verifiable, server.py L68 still has navigate(url: str) | None |
| AC4: ruff clean | Verifiable, standard gate | None |

### Challenge Results

- Challenger: FALLBACK — trivial T1 refactor following established convention, single viable approach
- Architect response: accepted

### Verdict: APPROVE
### Action Taken: Advanced to todo. All AC lines precise and verifiable. Pattern dictated by 15+ existing test files.
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