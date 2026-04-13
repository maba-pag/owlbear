---
id: 790
title: Tests — owlbear_mcp_browser MCP server and domain allowlist
status: in-progress
priority: needed
created: '2026-04-10T12:31:33.683712+00:00'
updated: '2026-04-12T22:06:17.457108+00:00'
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