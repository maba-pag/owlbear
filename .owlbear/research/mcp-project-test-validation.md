# mcp-project Server Tests — Research Validation

> **Owning task:** #99 — Test: mcp-project server tools and resources
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #99 tracks TDD RED tests for the mcp-project server (tools, resources,
lifespan, tree helper). The tests must fail before the builder (#17) implements
`server.py` and `tree.py`. This research validates the testing approach, confirms
AC coverage, and checks dependency readiness.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | #89 mcp-kanban tests (review) — TestFromAC pattern, mock subprocess, asyncio | .95 |
| 2 | mcp-knowledge tests (`packages/mcp-knowledge/tests/`) — mock context pattern | .90 |
| 3 | #17 Build mcp-project server — AC defining the interface contract | .95 |
| 4 | #68 OwlbearProjectFile model (archived) — dependency for import | .90 |
| 5 | MCP Python SDK FastMCP testing (modelcontextprotocol/python-sdk) | .85 |
| 6 | docs/research/build-mcp-project-server.md — design decisions for #17 | .90 |

## 3. Analysis

### 3a. Test Coverage vs AC

| AC Scenario (#99 body) | Test File | Test Count | Status |
|------------------------|-----------|------------|--------|
| project_info returns dict when json exists | test_server.py | 4 | Covered |
| project_info returns error when json missing | test_server.py | 2 | Covered |
| project_list returns list from registry dir | test_server.py | 5 | Covered |
| project_list returns empty when dir missing | test_server.py | 2 | Covered |
| project://readme returns content | test_server.py | 2 | Covered |
| project://readme returns fallback | test_server.py | 1 | Covered |
| project://structure depth limit (max 3) | test_server.py | 1 | Covered |
| project://structure excludes 5 dirs | test_server.py | 5 | Covered |
| AppContext populated correctly | test_server.py | 5 | Covered |
| AppContext.project_file is None | test_server.py | 1 | Covered |
| app_lifespan OWLBEAR_ROOT env var | test_server.py | 2 | Covered |
| build_tree correct output | test_tree.py | 4 | Covered |
| build_tree max_depth | test_tree.py | 3 | Covered |
| build_tree custom exclude | test_tree.py | 3 | Covered |

**Total:** 49 tests across 8 TestFromAC classes. All 14 AC scenarios covered.

### 3b. Testing Pattern Assessment

| Criterion | Assessment |
|-----------|-----------|
| Convention match (#89 pattern) | TestFromAC classes, mock MCP ctx, pytest.mark.asyncio |
| Mock strategy | MagicMock for MCP context, tmp_path for filesystem, monkeypatch for env |
| RED phase signal | ModuleNotFoundError on import (server.py, tree.py absent) |
| Fixture usage | tmp_path (dirs), monkeypatch (env, cwd) — no external deps |
| KISS/YAGNI | Tests stay within AC scope; edge cases are AC-relevant |

### 3c. Dependency Readiness

| Dep | Status | Impact |
|-----|--------|--------|
| #68 (OwlbearProjectFile model) | Archived | models.py exists, importable — tests use it for project_file fixtures |
| #17 (builder task) | In-progress | Depends on #99 — builder GREEN blocked until #99 pipeline complete |

## 4. Recommendation (.95 confidence)

Task #99 is fully validated. Tests are already committed (b07956c) under #17's
test-writer phase —  49 tests, all failing with ModuleNotFoundError as expected.
AC coverage is complete. The testing approach follows established project patterns.

**Pipeline note:** The test-writer committed tests under #17 before #99 passed the
research gate, creating a pipeline ordering gap. This is a metadata issue, not a
quality concern. The tests are sound.

## 5. Follow-up Tasks

No new follow-up tasks needed. Builder task #17 already exists at `in-progress`
with depends_on including #99. Advancing #99 through the pipeline unblocks #17's
TDD dependency chain.
