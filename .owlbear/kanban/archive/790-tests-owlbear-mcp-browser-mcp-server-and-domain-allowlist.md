---
id: 790
title: Tests — owlbear_mcp_browser MCP server and domain allowlist
status: done
priority: needed
created: '2026-04-10T12:31:33.683712+00:00'
updated: '2026-04-11T17:08:45.983760+00:00'
tags:
- phase-1
- scope:mcp-browser
- type:test
parent: 775
depends_on:
- 787
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify 6 MCP tools registered: `navigate`, `click`, `type`, `select`, `read_text`, `snapshot`
- Tests verify domain allowlist configuration via `BROWSER_ALLOWED_DOMAINS` env var
- Tests verify requests to non-allowlisted domains are rejected with `ToolError`
- Tests verify `BROWSER_TOOLS_EXCLUDE` env var removes tools from registration
- File: `tests/test_mcp_browser_775.py`

## Context
- WS-C: Browser Packages
- Scope item 2 from #775

[[2026-04-11]]
## Review Evidence

### Test Results
pytest: 24 passed, 0 failed (independently executed via quality-runner)

### Lint
ruff: clean on serve/mcp-browser/src/ + tests/test_mcp_browser_775.py

### Coverage
| Module | % |
|--------|---|
| allowlist.py | 100% |
| __init__.py | 100% |
| server.py | 92% |
| Overall | 93% |

Uncovered 8% = stub bodies of click, type_input, select, read_text, snapshot (no real browser at this phase — acceptable).

---

### AC Compliance

| AC Line | Mapped Tests | Evidence | Status |
|---------|-------------|----------|--------|
| AC1 — 6 tools registered: navigate, click, type, select, read_text, snapshot | TestFromAC_MCPServerLifespan (2 tests) | test_mcp_browser_775.py L78: checks app_lifespan importable; L81-L84: checks `_mcp.settings.lifespan is not None`. Neither test introspects tool names. Removing all 6 @_mcp.tool() decorators leaves both tests green. | FAIL |
| AC2 — domain allowlist via BROWSER_ALLOWED_DOMAINS | TestFromAC_DomainAllowlistEnvVar (5 tests) | Env var set, unset, empty, comma-separated, single domain. Assertions call DomainAllowlist.check() — mutation-resistant. | PASS |
| AC3 — ToolError for non-allowlisted domains | TestFromAC_NavigateToolError (5 tests) | Blocked domain, empty, unset, allowed passes, subdomain not listed. Exact frozenset membership in allowlist.py L30 validated. | PASS |
| AC4 — BROWSER_TOOLS_EXCLUDE removes tools | TestFromAC_ApplyToolExclusions (12 tests) | Import, single/multi exclusion, no env var, empty, whitespace strip, exception swallowing, return set[str], trailing comma, lifespan wiring. | PASS |

---

### Deductions

**D1 (–0.22) — AC1 coverage gap (blocking)**
AC1 says "Tests verify 6 MCP tools registered: navigate, click, type, select, read_text, snapshot". TestFromAC_MCPServerLifespan has 0 tests that check named tool registration. Required fix: add a test that calls `mcp_app.list_tools()` (or `_mcp._tool_manager.list_tools()`) and asserts all 6 names are present. For example:
```python
def test_six_tools_registered_by_name(self) -> None:
    from owlbear_mcp_browser.server import mcp_app
    tool_names = {t.name for t in mcp_app.list_tools()}
    assert {"navigate", "click", "type", "select", "read_text", "snapshot"} <= tool_names
```
Note: the `type` tool uses `@_mcp.tool(name="type")` on function `type_input` — test must check registered name "type" not "type_input".

**D2 (informational) — navigate() rebuilds allowlist per-call instead of using lifespan context**
server.py L57-58: navigate() reads BROWSER_ALLOWED_DOMAINS on every call and creates a fresh DomainAllowlist, bypassing AppContext.allowlist yielded by app_lifespan. The lifespan context is created but consumed by nothing. test_navigate_does_not_raise_for_allowlisted_domain passes because env var is set, not because lifespan context is wired. Not a blocking test gap, but a design defect worth tracking.

---

### Confidence
Base: 0.90 (24/24, clean lint, 93% coverage)
AC1 gap: –0.22
Final: 0.68 → FAIL

### Verdict
FAIL #790 → todo | AC1 not mechanically verified: TestFromAC_MCPServerLifespan has no test asserting named tool registration. Add test introspecting mcp_app.list_tools() for 6 named tools.

### Status Note
Task was in `backlog` (not `review`) when claimed. User-directed review. Routing to `todo` for test-writer AC1 fix.
[[2026-04-11]]
## Test-Writer Notes (AC1 gap retry)

**File:** tests/test_mcp_browser_775.py
**Added test:** `TestFromAC_MCPServerLifespan::test_six_tools_registered_by_name`
**Commit:** 834c3356

### Fix
Added `test_six_tools_registered_by_name` to `TestFromAC_MCPServerLifespan`. The test imports `mcp_app` from `owlbear_mcp_browser.server` (which is `_mcp._tool_manager`), calls the sync `list_tools()` method, and asserts all 6 registered names are present: `navigate, click, type, select, read_text, snapshot`.

Note: `type` is registered via `@_mcp.tool(name="type")` on `type_input` — the test checks the registered name, not the function name.

### Results
pytest: 25 passed, 0 failed (was 24 before fix)
ruff: not re-run (no new imports or changed logic, only assertion added)

### AC Coverage
| AC Line | Test(s) | Status |
|---------|---------|--------|
| AC1 — 6 tools registered | test_app_lifespan_importable + test_mcp_server_has_lifespan_configured + **test_six_tools_registered_by_name** | PASS |
| AC2 — BROWSER_ALLOWED_DOMAINS | TestFromAC_DomainAllowlistEnvVar (5) | PASS |
| AC3 — ToolError for non-allowlisted | TestFromAC_NavigateToolError (5) | PASS |
| AC4 — BROWSER_TOOLS_EXCLUDE | TestFromAC_ApplyToolExclusions (12) | PASS |

All 4 AC lines now mechanically verified.
[[2026-04-11]]
## Builder Notes

### Files Changed
- `tests/test_mcp_browser_775.py` — test-writer added `test_six_tools_registered_by_name` (commit 834c3356) to close AC1 gap. No implementation files modified (tests are the deliverable for this `type:test` task).

### Test Results
- **25/25 passed** (was 24 before AC1 gap fix), 0 failed, 1.55s
- All `TestFromAC_*` classes: 100% green

### Coverage
| Module | % |
|--------|---|
| allowlist.py | 100% |
| __init__.py | 100% |
| server.py | 92% |
| **Overall** | **93%** |

Uncovered 8% = stub bodies of click, type_input, select, read_text, snapshot (lines 78, 84, 90, 96, 102) — no real browser at this phase, acceptable.

### Lint
ruff: clean on `tests/test_mcp_browser_775.py` + `serve/mcp-browser/src/`

### AC Compliance
| AC Line | Test(s) | Status |
|---------|---------|--------|
| AC1 — 6 tools registered | test_app_lifespan_importable + test_mcp_server_has_lifespan_configured + test_six_tools_registered_by_name | PASS |
| AC2 — BROWSER_ALLOWED_DOMAINS | TestFromAC_DomainAllowlistEnvVar (5) | PASS |
| AC3 — ToolError for non-allowlisted | TestFromAC_NavigateToolError (5) | PASS |
| AC4 — BROWSER_TOOLS_EXCLUDE | TestFromAC_ApplyToolExclusions (12) | PASS |

### Evidence
Independently executed pytest + ruff. All 4 ACs mechanically verified. No new dependencies, no files outside scope.
[[2026-04-11]]
## Review Evidence (Cycle 2)

### Test Results
pytest: **25 passed, 0 failed** (independently executed via quality-runner)
Previous cycle: 24 passed. Net: +1 test (test_six_tools_registered_by_name).

### Lint
ruff: **clean** on serve/mcp-browser/src/ + tests/test_mcp_browser_775.py

### Coverage
| Module | % |
|--------|---|
| allowlist.py | 100% |
| __init__.py | 100% |
| server.py | 92% |
| **Overall** | **93%** |

Uncovered 8% = stub bodies of click, type_input, select, read_text, snapshot — no real browser at this phase. Acceptable.

---

### AC Compliance

| AC Line | Tests | Evidence | Status |
|---------|-------|----------|--------|
| AC1 — 6 tools registered: navigate, click, type, select, read_text, snapshot | test_app_lifespan_importable_from_server + test_mcp_server_has_lifespan_configured + **test_six_tools_registered_by_name** | test_six_tools_registered_by_name imports `mcp_app` (_mcp._tool_manager), calls sync list_tools(), asserts all 6 names via `<=`. Mutation-resistant — removing any @_mcp.tool() decorator fails the test. `name="type"` edge case correctly handled. | PASS |
| AC2 — domain allowlist via BROWSER_ALLOWED_DOMAINS | TestFromAC_DomainAllowlistEnvVar (5 tests) | Env var set, unset, empty, comma-separated, single domain. Assertions call DomainAllowlist.check() — mutation-resistant. | PASS |
| AC3 — ToolError for non-allowlisted domains | TestFromAC_NavigateToolError (5 tests) | Blocked domain, empty, unset, allowed passes, subdomain not listed. | PASS |
| AC4 — BROWSER_TOOLS_EXCLUDE removes tools | TestFromAC_ApplyToolExclusions (12 tests) | Import, single/multi exclusion, no env var, empty, whitespace strip, exception swallowing, return set[str], trailing comma, lifespan wiring. | PASS |

---

### TestFromAC_* Modification Audit
No existing tests weakened. test_app_lifespan_importable_from_server and test_mcp_server_has_lifespan_configured unchanged. test_six_tools_registered_by_name is a new addition — correct response to AC1 gap.

### Deductions
None. D1 from Cycle 1 (AC1 gap) fully resolved. D2 informational concern (navigate() rebuilds allowlist per-call, bypassing AppContext) noted in prior cycle — not a test gap, design concern tracked.

### Confidence
Base: 0.90 (25/25, ruff clean, 93% coverage)
Deductions: 0
Final: **0.95 → PASS**

### Verdict
PASS #790 → docs | confidence 0.95
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` task — only `tests/test_mcp_browser_775.py` added. No new behavior or API. copilot-instructions.md is 80 lines (branch/identity only); no mcp-browser entry needed. |
| 2 | Module docstrings | No | N/A | No implementation files created or modified. Test file is the sole deliverable. |
| 3 | External attribution | No | N/A | No external patterns, articles, or repos referenced in review evidence. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | No research phase; no `.owlbear/research/` file linked from task body. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/790-*` files found)
[[2026-04-11]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — 6 tools registered: navigate, click, type, select, read_text, snapshot | test_six_tools_registered_by_name (L58-63): imports mcp_app, calls list_tools(), asserts 6 names via <=. Mutation-resistant. + 2 lifespan tests. | PASS |
| AC2 — domain allowlist via BROWSER_ALLOWED_DOMAINS | TestFromAC_DomainAllowlistEnvVar (5 tests): env set/unset/empty/comma/single. DomainAllowlist.check() assertions. | PASS |
| AC3 — ToolError for non-allowlisted domains | TestFromAC_NavigateToolError (5 tests): blocked/empty/unset/allowed/subdomain. ToolError assertions. | PASS |
| AC4 — BROWSER_TOOLS_EXCLUDE removes tools | TestFromAC_ApplyToolExclusions (12 tests): single/multi/no-env/empty/whitespace/exception/return-type/trailing-comma/lifespan-wiring. | PASS |
| AC5 — File: tests/test_mcp_browser_775.py | File exists, 333 lines, 25 tests. | PASS |

### Test Results
- pytest: 25 passed, 0 failed (task-scoped)
- Cross-task regression: 118 adjacent browser tests passed (test_browser_content_775, test_edge_launcher_cdp_755, test_browser_package_scaffold_787, test_content_safety_735, test_content_safety_inversion_775)
- Full suite: could not complete serially in timeout; 6 pre-existing collection errors in unrelated kanban tests. No evidence of regressions from this task (single file changed).
- ruff: clean on serve/mcp-browser/src/ + tests/test_mcp_browser_775.py

### Architect Quality: 4/5
AC lines specific and mechanically verifiable. AC1 initially led to lifespan-only tests (caught by reviewer Cycle 1) — could have specified tool-name introspection explicitly. System self-corrected.

### Deduction Breakdown
- All 5 AC lines have specific evidence: no deduction
- Lint: clean — no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence section: present, detailed, PASS — no deduction
- Full suite incomplete but no task-scope failures and 118 adjacent tests clean: no deduction

### Confidence: .97
### Action: archive