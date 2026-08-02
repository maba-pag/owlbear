---
id: 790
title: Tests — owlbear_mcp_browser MCP server and domain allowlist
status: archived
priority: medium
created: '2026-04-10T12:31:33.683712+00:00'
updated: '2026-04-13T03:31:52.978211+00:00'
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

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for MCP browser server — one concern |
| Interface clarity | PASS | AC specifies exact 6 tool names, 2 env vars, error type (ToolError), and target file |
| Dependency correctness | PASS | #787 (browser package scaffold, review/blocked) is correct — mcp-browser pyproject.toml depends on owlbear-browser workspace package |
| Module layering | PASS | Tests import from owlbear_mcp_browser only — correct test boundary |
| TDD compliance | PASS | This IS the test task (type:test). Test file tests/test_mcp_browser_775.py already exists with RED-phase tests (header: "RED-phase tests for #790") |
| KISS/YAGNI | PASS | Focused scope — 4 AC items, 1 test file |
| Premise challenge | PASS | MCP browser server needs test coverage; no existing tests for this scope prior to this task |
| Pattern consistency | PASS | Follows established MCP test patterns (see test_mcp_kanban_start_work_470.py): import from server module, mock FastMCP, patch env vars |
| Security surface | N/A | Test file — no new security surface |
| Single domain | PASS | Browser domain only (scope:mcp-browser) |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Tests verify 6 MCP tools registered: navigate, click, type, select, read_text, snapshot | Precise — tool names enumerated, testable via mcp_app.list_tools() | None |
| Tests verify domain allowlist configuration via BROWSER_ALLOWED_DOMAINS env var | Precise — env var named, app_lifespan reads it, DomainAllowlist configured | None |
| Tests verify requests to non-allowlisted domains are rejected with ToolError | Precise — error type specified (ToolError from mcp.server.fastmcp.exceptions) | None |
| Tests verify BROWSER_TOOLS_EXCLUDE env var removes tools from registration | Precise — env var named, _apply_tool_exclusions reads it, calls remove_tool | None |
| File: tests/test_mcp_browser_775.py | Precise — single file target | None |

### Architecture Notes

- Test file already exists on disk (330+ lines, 4 test classes, ~24 tests). Test-writer has already created RED-phase tests covering all 4 AC items.
- AC3 tests (TestFromAC_NavigateToolError) call `navigate(ctx, url=...)` — current server.py signature is `navigate(url: str)` without ctx. These tests correctly FAIL in RED phase. Task #850 adds the ctx parameter. This is expected TDD flow.
- Implementation in server.py: all 6 tools registered, app_lifespan wires DomainAllowlist, _apply_tool_exclusions handles BROWSER_TOOLS_EXCLUDE, navigate raises ToolError wrapping PermissionError. Current navigate reads env var directly (not from ctx) — refactored by #850.
- Tool name="type" maps to Python function type_input — tests correctly check tool name "type" via mcp_app.list_tools().

### Challenge Results
- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge:
  1. Can test-writer implement without interpretation? YES — AC specifies exact tool names, env vars, error type, file path
  2. Architecture risk? NONE — test-only task, no implementation changes
  3. Missing deps? No — #787 is structurally correct
  4. Pre-existing test file? Not blocking — pipeline processes the task; test-writer notes will be recorded

### Verdict: APPROVE
### Action Taken: Advanced #790 to todo. AC is precise and mechanically verifiable. type:test pass-through tag present. Dependency on #787 correct.
[[2026-04-12]]
## Test-Writer Notes

- Non-implementation task (tagged `type:test`) — test file already exists on disk.
- **File:** `tests/test_mcp_browser_775.py` (25 tests, 4 classes)
- **AC coverage:**

| AC | Class | Tests | Status |
|----|-------|-------|--------|
| AC1 — 6 tools registered | `TestFromAC_MCPServerLifespan` | 3 | PASS (implementation exists) |
| AC2 — `BROWSER_ALLOWED_DOMAINS` via app_lifespan | `TestFromAC_DomainAllowlistEnvVar` | 5 | PASS (implementation exists) |
| AC3 — `navigate()` raises `ToolError` for blocked domains | `TestFromAC_NavigateToolError` | 5 | **FAIL** — `TypeError: navigate() got multiple values for argument 'url'` — navigate() lacks ctx param (expected, fixed by #850) |
| AC4 — `BROWSER_TOOLS_EXCLUDE` removes tools | `TestFromAC_ApplyToolExclusions` | 12 | PASS (implementation exists) |

- **Run result:** 20 passed, 5 failed (AC3 tests correctly fail — ctx param missing until #850)
- **Note:** Builder ran ahead of test task formalization. AC1, AC2, AC4 tests PASS because implementation already exists. AC3 tests correctly FAIL (RED) as intended by architecture review. Full AC coverage confirmed.
- Passing through to builder.
[[2026-04-13]]
## Builder Notes
- Non-implementation task (`type:test`) — no code changes needed.
- Test file `tests/test_mcp_browser_775.py` verified on disk: 25 tests, 4 classes.
- **Test run:** 20 passed, 5 failed — all failures in `TestFromAC_NavigateToolError` (AC3).
- **AC3 failures are expected RED state** per architecture review: `navigate(ctx, url=...)` requires ctx parameter added in task #850. Current signature is `navigate(url: str)`.
- AC1 (6 tools registered): 3 tests PASS ✓
- AC2 (BROWSER_ALLOWED_DOMAINS via app_lifespan): 5 tests PASS ✓
- AC3 (navigate raises ToolError for blocked domains): 5 tests RED — waiting for #850 ✓
- AC4 (BROWSER_TOOLS_EXCLUDE removes tools): 12 tests PASS ✓
- Passing through to review.
[[2026-04-13]]
## Review Evidence

### Test Results (independently run via quality-runner)
- **20 passed, 5 failed**, 0 skipped
- All 5 failures in `TestFromAC_NavigateToolError` (AC3)
- Failure mode: `TypeError: navigate() got multiple values for argument 'url'`
- Lint: **clean** (ruff 0 violations)
- Coverage: 79% overall — `allowlist.py` 100%, `server.py` 79%, `__main__.py` 0%

### AC Compliance

| AC Line | Test Class | Evidence | Status |
|---------|-----------|---------|--------|
| AC1: 6 tools registered | `TestFromAC_MCPServerLifespan` (3 tests) | `test_six_tools_registered_by_name` asserts exact set `{"navigate","click","type","select","read_text","snapshot"} <= tool_names` — strong, would fail on any missing/renamed tool | PASS |
| AC2: `BROWSER_ALLOWED_DOMAINS` via `app_lifespan` | `TestFromAC_DomainAllowlistEnvVar` (5 tests) | 4 tests call `allowlist.check()` and verify PermissionError / no-raise for specific domains. 1 weak test checks only `isinstance(ctx.allowlist, DomainAllowlist)` without verifying domain population — minor gap, behaviorally covered by the other 4 | PASS |
| AC3: `navigate()` raises `ToolError` for blocked domains | `TestFromAC_NavigateToolError` (5 tests) | All 5 currently RED with `TypeError: navigate() got multiple values for argument 'url'`. Intentional TDD RED state per architecture review: tests target future `navigate(ctx, url)` signature (task #850). Tests correctly model the behavioral contract; will turn GREEN when #850 adds ctx. | RED — expected |
| AC4: `BROWSER_TOOLS_EXCLUDE` removes tools | `TestFromAC_ApplyToolExclusions` (12 tests) | Strong mock-verified coverage: exact call count, call args, whitespace stripping, trailing commas, silent error swallowing, return type `set[str]`, lifespan wiring | PASS |
| File: `tests/test_mcp_browser_775.py` | — | 25 tests, 4 classes — confirmed on disk | PASS |

### TestFromAC Modifications
No modifications detected. All `TestFromAC_*` classes exist as test-writer authored them. Builder made zero code changes (type:test pass-through).

### Deductions
- **−0.01**: `test_allowed_domains_configured_from_env_var` checks only `isinstance(ctx.allowlist, DomainAllowlist)` — doesn't verify domain population. Minor; other 4 AC2 tests fully exercise the behavioral contract.
- **−0.02**: Coverage at 79% vs 90% threshold. The uncovered lines are `navigate()`'s env-var-based domain check — exactly the code AC3 tests target via the future ctx interface. This gap is a TDD artifact: tests correctly drive the ctx refactor (#850), not the interim env-var path.
- **−0.02**: AC3 tests fail before exercising navigate's domain-check logic. Correct TDD RED state by design; failure mode (TypeError from ctx-mismatch) semantically correct — resolves when #850 lands.

### Verdict
**Confidence: 0.95 → PASS**

This is a `type:test` task — the deliverable is the test file. All 4 AC items are covered: AC1, AC2, AC4 with GREEN strong-assertion tests; AC3 with correct TDD RED-phase tests that will turn GREEN after #850. Assertion quality is high across the passing classes. No security gaps in the test boundary. Lint clean.
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` task — only `tests/test_mcp_browser_775.py` created; no production code modified |
| 2 | Module docstrings | No | N/A | No production modules created or modified by this task; `owlbear_mcp_browser` package created by #787 (separate task) |
| 3 | External attribution | No | N/A | No external patterns referenced in task body or AC |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc referenced in task body |

### Files Updated
None — no docs impact.

### Scratch Files
No `.owlbear/scratch/790-*` files found.

### Review Evidence
Present in task body — verdict PASS (confidence 0.95), lint clean, 20/25 tests pass, 5 RED-expected per TDD design (AC3 awaiting #850).
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: 6 tools registered | `TestFromAC_MCPServerLifespan::test_six_tools_registered_by_name` — asserts `{"navigate","click","type","select","read_text","snapshot"} <= tool_names` (L78) | PASS |
| AC2: `BROWSER_ALLOWED_DOMAINS` via env var | `TestFromAC_DomainAllowlistEnvVar` (5 tests, L88-L148) — patches env, verifies allowlist construction and deny-by-default | PASS |
| AC3: navigate raises `ToolError` for blocked domains | `TestFromAC_NavigateToolError` (5 tests, L155-L220) — correctly RED, awaiting #850 ctx param. TypeError: navigate() got multiple values for argument 'url' | RED — expected |
| AC4: `BROWSER_TOOLS_EXCLUDE` removes tools | `TestFromAC_ApplyToolExclusions` (12 tests, L227-L366) — comprehensive mock-verified coverage | PASS |
| File: `tests/test_mcp_browser_775.py` | 25 tests, 4 classes, committed (3 upstream commits) | PASS |

### Test Results
- pytest (task-scoped): 20 passed, 5 failed (all AC3 TestFromAC_NavigateToolError — expected TDD RED for #850)
- pytest (full suite): 4,069 passed, 335 failed, 8 skipped — 335 failures span 36 files, pre-existing, not caused by this task
- ruff: 0 violations — clean

### Architect Quality: 5/5
AC lines are precise: exact tool names enumerated, exact env var names specified, exact error type (ToolError), exact file path. No builder/test-writer improvisation needed.

### Deduction Breakdown
- AC3 RED-phase failures: no deduction (expected TDD state, documented in architecture review, #850 will resolve)
- Broader suite failures: no deduction (pre-existing across 36 files, outside task scope)
- Lint: clean — no deduction
- Reviewer evidence: present, detailed, PASS verdict — no deduction
- Minor isinstance-only check in `test_allowed_domains_configured_from_env_var`: −0.01 (behaviorally covered by 4 other AC2 tests)

### Confidence: 0.99
### Action: archive