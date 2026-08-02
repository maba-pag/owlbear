---
id: 771
title: 'P1-18: Impl — MCP browser server + URL domain allowlist'
status: archived
priority: medium
created: '2026-04-10T10:56:34.350906+00:00'
updated: '2026-04-12T01:00:08.032266+00:00'
tags:
- phase-1
- scope:mcp-browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. `serve/mcp-browser/` FastMCP server:
- Tools: navigate, click, type, select, read_text, snapshot
- URL domain allowlist at tool implementation level
- Follows MCP server conventions (AppContext, lifespan, error handling, annotations, tool exclusion)

All P1-17 tests pass. Convergence point for all Phase 1 tracks.

Parent: #751

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/771-mcp-browser-server.md
- Sources: 10 studied, 7 high-relevance
- Recommendation: Proceed with minimal GREEN implementation — skeleton already passes all 22 tests. Add ToolAnnotations + `__main__.py` + expand `__all__` for convention compliance. Keep current per-call env read (not ctx-based) to match test expectations. Do NOT add ctx: Context (breaks tests) or implement full browser interaction (Phase 2). (confidence: .85)
- Follow-up tasks created: #836 (refactor to ctx: Context + AppContext pattern), #837 (browser session management in AppContext)
- Decision requests: none — T1 autonomous (GREEN phase within approved architecture)

## Challenge Results
- Challenger: FALLBACK — no controversial recommendation to challenge
- Confidence in original: .85
- Key challenges: none — approach dictated by test expectations and established conventions
- Researcher response: N/A

## Key Findings
1. **F1:** Skeleton already passes all tests — stub implementations match test expectations. Builder's work is convention compliance only.
2. **F2:** Context parameter tension — all reference servers use ctx: Context, but tests call navigate(url=...) directly. Adding ctx breaks tests. Defer to follow-up #836.
3. **F3:** Navigate allowlist creates new DomainAllowlist per call (non-idiomatic but functional). Refactor deferred to #836.
4. **F4:** Missing `__main__.py` — must reference `_mcp` (not `mcp`) since module attribute uses underscore prefix.
5. **F5:** ToolAnnotations required but untested — add per convention regardless. Proposed: navigate/select idempotent, click/type not, read_text/snapshot readOnly.
[[2026-04-11]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module (`serve/mcp-browser/`), one concern: MCP server + URL domain allowlist |
| Interface clarity | PASS | 6 tools with typed signatures; allowlist contract via `DomainAllowlist.check()`; research findings F1–F5 provide precise builder guidance |
| Dependency correctness | PASS | No `depends_on` needed — RED-phase tests exist and pass (25/25 green). Follow-ups #836 and #837 correctly `depends_on: [771]` |
| Module layering | PASS | `mcp-browser` → `owlbear-browser` (downward); no upward imports |
| TDD compliance | PASS | `tests/test_mcp_browser_775.py` (25 tests) precedes this GREEN task |
| KISS/YAGNI | PASS | Minimal scope — convention compliance only (ToolAnnotations, `__main__.py`, `__all__`). Browser interaction deferred to #837, ctx refactor to #836 |
| Premise challenge | PASS | MCP browser server required for browser knowledge extraction pipeline (parent #751) |
| Pattern consistency | PASS | Skeleton already follows kanban/knowledge/memory MCP patterns (AppContext dataclass, lifespan, `_apply_tool_exclusions`, `ToolError` for hard errors) |
| Security surface | PASS | Deny-by-default allowlist (empty list → all blocked). `PermissionError` → `ToolError`. Subdomain enforcement tested. Per-call env read is non-idiomatic but secure — deferred to #836 |
| Single domain | PASS | `scope:mcp-browser` only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `navigate()` blocked domain | Allowlist rejects hostname | `ToolError` | YES | Agent sees error message |
| `_apply_tool_exclusions()` unknown tool | `server.remove_tool()` raises | Silently caught (`BLE001`) | YES | Tool remains available |
| `app_lifespan()` missing/empty env | Empty allowlist created | N/A | YES | Deny-by-default (secure) |

### Builder Guidance (from Research Key Findings)
- **F1:** Skeleton passes all 25 tests — builder work is convention compliance only
- **F4:** Add `__main__.py`: `from owlbear_mcp_browser.server import _mcp; _mcp.run()` (note underscore prefix)
- **F5:** Add `ToolAnnotations` to all 6 tools: navigate/select → idempotent; click/type_input → not idempotent; read_text/snapshot → readOnly
- **F2/F3:** Do NOT add `ctx: Context` — breaks existing tests. Deferred to #836
- Expand `__all__` in server.py to include `AppContext`, `app_lifespan`

### Challenge Results
- Challenger: FALLBACK — approach dictated by test expectations and established MCP conventions; no controversial recommendation
- Architect response: accepted

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC verifiable via 25 existing tests + convention inspection. Builder has precise guidance from research findings.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_server_771.py
- Classes: TestFromAC_ToolAnnotations, TestFromAC_MainEntryPoint, TestFromAC_PublicExports
- Tests per category: happy 9, edge 1, boundary 1
- Total: 11 tests, all FAIL
- ruff: clean

### AC Coverage Table
| AC | Description | Tests | Status |
|----|-------------|-------|--------|
| AC5 | ToolAnnotations on all 6 tools | 7 tests (1 boundary + 1 per tool) | All FAIL — annotations=None |
| AC6 | `__main__.py` entry point | 2 tests | All FAIL — ModuleNotFoundError |
| AC7 | `__all__` exports AppContext, app_lifespan | 2 tests | All FAIL — `__all__=['mcp_app']` only |

AC1-AC4 already covered by tests/test_mcp_browser_775.py (25 existing tests, all passing).
[[2026-04-11]]
## Builder Notes
- **Files changed:** `serve/mcp-browser/src/owlbear_mcp_browser/server.py` (2 edits), `serve/mcp-browser/src/owlbear_mcp_browser/__main__.py` (created)
- **Test results:** 36 passed (11 from test_mcp_browser_server_771.py + 25 from test_mcp_browser_775.py), 0 failed
- **Lint:** ruff clean
- **Evidence:**
  - AC5: Added `readOnlyHint=False` to `click` and `type_input`; other 4 tools already had correct annotations
  - AC6: Created `__main__.py` following `mcp-kanban` pattern; imports `_mcp` at module level (satisfies reference test), runs only under `if __name__ == "__main__"`
  - AC7: Updated `__all__ = ["AppContext", "app_lifespan", "mcp_app"]`
- **Commit:** `5ff9c228` feat(mcp-browser): add ToolAnnotations, __main__.py, expand __all__ (#771, builder)
[[2026-04-11]]
## Review Evidence

### Test Results (independent)
pytest: **36 passed, 0 failed** (test_mcp_browser_server_771.py × 11 + test_mcp_browser_775.py × 25)
ruff: **clean** (source + tests)
coverage: **92% overall** — `__init__.py` 100%, `allowlist.py` 100%, `server.py` 92%, `__main__.py` 75% (single uncovered line: `_mcp.run()` in `if __name__ == "__main__"` — unreachable in unit tests, standard entry point pattern)

### AC Compliance Table

| AC | Evidence | Mapped Test(s) | Status |
|----|----------|----------------|--------|
| AC5 — ToolAnnotations on all 6 tools | `server.py:64–100` — each `@_mcp.tool(annotations=ToolAnnotations(...))` present; navigate/select → `idempotentHint=True`; read_text/snapshot → `readOnlyHint=True`; click/type → `readOnlyHint=False` | `TestFromAC_ToolAnnotations` (7 tests) | PASS |
| AC6 — `__main__.py` entry point | `__main__.py:1–8` — module-level `from owlbear_mcp_browser.server import _mcp`; `_mcp.run()` gated under `if __name__ == "__main__"` | `TestFromAC_MainEntryPoint` (2 tests) | PASS |
| AC7 — `__all__` exports `AppContext`, `app_lifespan` | `server.py:19` — `__all__ = ["AppContext", "app_lifespan", "mcp_app"]` | `TestFromAC_PublicExports` (2 tests) | PASS |
| AC1–AC4 (pre-existing) | Covered by `test_mcp_browser_775.py` (25 tests) — all pass | Multiple `TestFromAC_*` classes | PASS |

### TestFromAC Integrity Table

| Test Class | Change | Assessment |
|------------|--------|------------|
| TestFromAC_ToolAnnotations (7) | None | PRESERVED — specific hint value assertions (`assert annotations.idempotentHint is True`); would fail on any annotation mutation |
| TestFromAC_MainEntryPoint (2) | None | PRESERVED — object identity check (`val is expected_server`) for wiring; no lazy assertions |
| TestFromAC_PublicExports (2) | None | PRESERVED — explicit string-in-`__all__` checks |
| All TestFromAC_* in test_mcp_browser_775.py | None | PRESERVED |

### Pass 1 CRITICAL Checks

| Check | Finding | Verdict |
|-------|---------|---------|
| 5.0 AC-to-test coverage | All AC lines mapped to TestFromAC tests with strong assertions; no MISSING, no LAX | PASS |
| 5.1 Security | No hardcoded secrets; URL parsed via `urlparse()` (safe); subdomain blocking via exact frozenset match (sub.example.com blocked if only example.com allowed, verified by test); no injection surface | PASS |
| 5.2 TestFromAC integrity | All 11 TestFromAC_* methods fully PRESERVED — no WEAKENED or REMOVED | PASS |
| 5.3 Test quality | STRONG — all assertions target specific field values; test names descriptive; independence maintained via fresh imports | PASS |
| 5.4 Data safety | Stateless stubs; no shared mutable state; no unbounded input; no LLM output persistence | PASS |
| 5.5 Implementation-aware gap analysis | All branches exercised: allowlist enforcement in navigate(), _apply_tool_exclusions(), lifespan, __main__ wiring, __all__ exports | PASS |
| 5.7 Loop detection | 1 builder attempt, CLEAN | PASS |

### Deductions
- **D1 (informational):** `navigate()` re-reads `BROWSER_ALLOWED_DOMAINS` env var per call instead of using `AppContext.allowlist` created in lifespan. Not a security issue (same env var, same result). Acknowledged in research (F3) and deferred to #836. −.02 confidence.

### Verdict
**Confidence: .96 → PASS**
All Pass 1 criteria met. 36/36 tests pass. Lint clean. Coverage 92%. AC5/AC6/AC7 fully implemented and verified. No TestFromAC modifications detected.
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` contains only project identity and branch info — no MCP server table or tech stack section. Convention compliance changes (ToolAnnotations, `__main__.py`, `__all__`) don't require copilot-instructions update. |
| 2 | Module docstrings | Yes | Verified | `server.py`: module docstring ✓, `AppContext` ✓, `app_lifespan` ✓, `_apply_tool_exclusions` ✓, all 6 tools (`navigate`, `click`, `type_input`, `select`, `read_text`, `snapshot`) ✓. `__main__.py`: module docstring ✓ (no public functions). `allowlist.py`: module ✓, `DomainAllowlist` class + `check()` method ✓. No updates needed — all accurate. |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already contains "MCP Browser Server Research (Task #771)" section with FastMCP Tools Documentation entry (added during research phase). No new entries needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. MCP tools only. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/771-mcp-browser-server.md` exists. Linked from task body under `## Research`. Follow-up tasks #836 (ctx refactor) and #837 (browser session management) confirmed created. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `771-*` scratch files found)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1-AC4 (tools, allowlist, lifespan, exclusions) | test_mcp_browser_775.py — 25 tests, all pass | PASS |
| AC5 — ToolAnnotations on all 6 tools | server.py:L68,82,88,94,100,105 — annotations present; TestFromAC_ToolAnnotations (7 tests) pass | PASS |
| AC6 — `__main__.py` entry point | `__main__.py` exists, imports `_mcp`, gated `_mcp.run()`; TestFromAC_MainEntryPoint (2 tests) pass | PASS |
| AC7 — `__all__` exports `AppContext`, `app_lifespan` | server.py:L19 `__all__ = ["AppContext", "app_lifespan", "mcp_app"]`; TestFromAC_PublicExports (2 tests) pass | PASS |

### Test Results
- pytest (task scope): 36 passed, 0 failed
- pytest (full suite): 3579 passed, 276 failed, 8 skipped, 6 errors — 0 failures in #771 scope. All failures traced to other tasks' RED tests or pre-existing infrastructure issues (lint-changed.ps1, AppContext kwargs, TaskSummary, package boundary reorganization).
- ruff: clean

### Architect Quality: 4/5
AC lines specific and testable. Research findings (F1–F5) provided precise builder guidance. Minor gap: AC didn't enumerate per-tool annotation hints explicitly (builder inferred from research), but research coverage compensated.

### Deduction Breakdown
- AC lines without evidence: 0 → −0
- Lint violations: 0 → −0
- AC quality ≤ 3: no (4/5) → −0
- Missing reviewer evidence: no (detailed, PASS at .96) → −0
- Full-suite failures in task scope: 0 → −0

### Confidence: .98
### Action: archive

Note: .02 discretionary deduction for 276 pre-existing failures in full suite complicating exhaustive cross-task verification, though all examined failures are clearly unrelated to #771.

### Commit Integrity
- Builder commit `5ff9c228` confirmed for deliverable files (server.py, __main__.py)
- `__main__.py` shows CRLF artifact in `git status` but no actual diff against HEAD