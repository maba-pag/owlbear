# MCP Browser Server Tests — Duplicate Analysis + ToolAnnotations Gap

> **Owning task:** #770 — P1-17: Tests — MCP browser server + URL domain allowlist
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #770 specifies 5 ACs for RED-phase tests on the MCP browser server:
1. FastMCP server registers 6 tools (navigate, click, type, select, read_text, snapshot)
2. URL domain allowlist enforcement at tool level
3. Allowlist read from env var (`BROWSER_ALLOWED_DOMAINS`)
4. Tool annotations set correctly (`ToolAnnotations`)
5. `BROWSER_TOOLS_EXCLUDE` env var removes tools

**Key question:** Do these test requirements overlap with existing test work, and what is the unique gap?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Test file for #790 | `tests/test_mcp_browser_775.py` | .95 |
| 2 | Task #790 body (status: docs) | kanban task #790 | .95 |
| 3 | Task #794 AC (GREEN: MCP server) | kanban task #794 | .90 |
| 4 | mcp-kanban ToolAnnotations tests | `serve/mcp-kanban/tests/test_tool_annotations_494.py` | .90 |
| 5 | mcp-browser server.py | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | .85 |
| 6 | mcp-kanban server.py (annotation pattern) | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .80 |

## 3. Analysis — Overlap Matrix

| #770 AC | #790 AC | Tests in `test_mcp_browser_775.py` | Status |
|---------|---------|--------------------------------------|--------|
| AC1: 6 tools registered | AC1 | `TestFromAC_MCPServerLifespan` — 3 tests incl. `test_six_tools_registered_by_name` | **DUPLICATE** |
| AC2: Domain allowlist enforcement | AC2+AC3 | `TestFromAC_DomainAllowlistEnvVar` (5) + `TestFromAC_NavigateToolError` (5) | **DUPLICATE** |
| AC3: Allowlist from env var | AC2 | `TestFromAC_DomainAllowlistEnvVar` — 5 tests | **DUPLICATE** |
| AC4: ToolAnnotations set correctly | — | **No tests exist anywhere** | **UNIQUE GAP** |
| AC5: BROWSER_TOOLS_EXCLUDE | AC4 | `TestFromAC_ApplyToolExclusions` — 12 tests | **DUPLICATE** |

**Finding:** 4 of 5 ACs are exact duplicates of #790's delivered tests (25 tests, all passing, reviewed at .95 confidence). Only AC4 (ToolAnnotations) is a genuine gap.

### 3a. ToolAnnotations — Current State

The mcp-browser server uses bare `@_mcp.tool()` decorators with **no** `ToolAnnotations`. All 3 other MCP servers in the workspace have `ToolAnnotations` on every tool:

| Server | `from mcp.types import ToolAnnotations` | All tools annotated |
|--------|:---:|:---:|
| mcp-kanban | Yes | Yes (8 tools) |
| mcp-knowledge | Yes | Yes (10+ tools) |
| mcp-memory | Yes | Yes (5 tools) |
| **mcp-browser** | **No** | **No** |

### 3b. Expected ToolAnnotations for Browser Tools

Based on tool semantics and established conventions from mcp-kanban:

| Tool | readOnlyHint | idempotentHint | destructiveHint | Rationale |
|------|:---:|:---:|:---:|-----------|
| navigate | — | True | False | Navigating to same URL twice = same state |
| click | — | — | False | Clicking twice may toggle state |
| type | — | — | False | Typing twice appends duplicate text |
| select | — | True | False | Selecting same value again = same state |
| read_text | True | True | — | Pure read, no state change |
| snapshot | True | True | — | Pure read, no state change |

### 3c. Test Pattern — Established Reference

`serve/mcp-kanban/tests/test_tool_annotations_494.py` provides the exact template:
- `_get_tool_annotations(tool_name)` — helper introspecting `mcp._tool_manager.list_tools()`
- `@pytest.mark.parametrize` to assert all tools have `annotations is not None`
- Per-tool tests for specific hint values (readOnlyHint, idempotentHint, destructiveHint)

The mcp-browser version needs ~15 tests: 1 import check + 1 all-tools-have-annotations + ~13 per-hint assertions across 6 tools.

### 3d. Task #794 Already Expects ToolAnnotations

Task #794 AC states: "6 MCP tools registered... each with ToolAnnotations (readOnlyHint, idempotentHint, destructiveHint)". The RED-phase test task for #794's ToolAnnotations AC does **not exist** as a separate task — this is exactly what the unique gap in #770 fills.

## 4. Recommendation

**Descope #770 to AC4 only (ToolAnnotations tests). Confidence: .88.**

- AC1/2/3/5 are delivered by #790 (25 tests, .95 reviewer confidence). Duplicating them is waste.
- AC4 (ToolAnnotations) is the only genuine gap. It naturally pairs with #794's TDD cycle.
- The test file should be `tests/test_mcp_browser_tool_annotations_770.py` (new file, separate from #790's test file).
- Test pattern: follow `test_tool_annotations_494.py` from mcp-kanban.

Challenge: FALLBACK — challenger subagent not available.

**Tier: T1** — test structure correction, no new capability.

## 5. Follow-up Tasks

- **Descoped ACs → no new tasks needed.** Tests for AC1/2/3/5 already exist in #790.
- **AC4 (ToolAnnotations tests)** — the task #770 itself should be descoped to this single AC and advanced to backlog for the test-writer to implement the RED phase.
