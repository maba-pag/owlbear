# Test Coverage Analysis for Canonical Tool Registry Validation

> **Owning task:** #201 — Add tests for canonical tool registry validation
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #201 asks for tests covering the expanded `validate_agents.py` tool name validation (KNOWN_TOOLSETS, `_check_unknown_tools`). This code is being implemented by #198 (in-progress). Question: what test coverage already exists from #198's TDD phase, and what gaps remain?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `tests/test_validate_agents.py` (lines 379–747) — #198 TDD tests | .95 — defines existing coverage |
| `tests/test_rename_todo_to_todos.py` (lines 57–79) — parametrize pattern | .90 — established per-agent test idiom |
| `docs/research/canonical-tool-registry-validation.md` — #198 research | .85 — canonical tool list, implementation approach |
| Task #198 body — test-writer notes | .90 — lists 20 tests across 5 classes |
| Agent `tools:` audit (all 11 agents) | .85 — actual tool names in production |

## 3. Analysis

### 3a. Overlap: #198 TDD already covers

| #201 AC Item | #198 Coverage | Details |
|---|---|---|
| Test unknown tool names are flagged | **Full** | `TestFromAC_UnknownToolErrors` — 5 tests |
| Existing todo/resolveMemoryFileUri tests pass | **Full** | Classes from #134 remain untouched |
| ruff clean | **Full** | Standard check, already enforced |

### 3b. Genuine gaps not covered by #198

| Gap | Why missing | Impact |
|---|---|---|
| Valid toolset shorthand passes (e.g., `[agent]`, `[search]`) | #198 TDD wrote error-path tests only | No happy-path regression safety |
| Valid prefixed tools pass (e.g., `[execute/runInTerminal]`) | Same | No verification that legitimate tools pass |
| MCP server patterns pass (e.g., `[owlbear-kanban/*]`) | Same | MCP wildcards untested |
| Parametrized per-agent regression | Existing test runs all agents via subprocess but single test, not parametrized | Failure points to "some agent" not "which agent" |

### 3c. Implementation approach

| Aspect | Recommendation | Source |
|---|---|---|
| Happy-path tests | `validate_agent()` on tmp_path fixtures with valid tools → assert `[]` | Existing `_write_agent`/`_agent_content` helpers |
| Parametrize pattern | `@pytest.mark.parametrize("filename", AGENT_MD_FILES)` | `test_rename_todo_to_todos.py` lines 61–70 |
| MCP pattern test | `tools: [owlbear-kanban/*]` fixture | Agent audit: all 11 agents use this pattern |
| Multi-server test | `tools: [owlbear-kanban/*, microsoft/markitdown/*]` | researcher.agent.md uses both |

### 3d. Dependency chain

```
#193 (blocked) → #198 (in-progress) → #201 (this task)
```

`validate_agents.py` on HEAD has no `KNOWN_TOOLSETS` or `_check_unknown_tools`. #201 cannot proceed until #198 builder lands the implementation. Hard dependency: `depends_on: [198]`.

## 4. Recommendation (.90 confidence)

**Refine #201 AC:** Remove the already-covered "unknown tools flagged" item and add the specific gap tests. Add `depends_on: [198]`. The remaining scope is ~25 LOC of tests following established patterns.

The task is well-scoped and ready for backlog after AC refinement. Estimated 4 new test functions:
1. `test_valid_toolset_shorthand_passes` — parametrize over `agent`, `edit`, `search`, etc.
2. `test_valid_prefixed_tool_passes` — parametrize over `execute/runInTerminal`, `read/readFile`, etc.
3. `test_mcp_wildcard_pattern_passes` — `owlbear-kanban/*`, `microsoft/markitdown/*`
4. `test_each_agent_file_passes_validation` — parametrize over 11 agent filenames

## 5. Follow-up Tasks

No new tasks needed — #201 IS the follow-up from #198's research. AC refinement applied directly to the task body.
