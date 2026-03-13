# Splitting bootstrap.py into a Package

> **Owning task:** #480 — Split bootstrap.py into focused submodules
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`bootstrap.py` is 992 lines — the largest file in the project. It assembles seven
subsystems (channels, hooks, toolsets, MCP, agent registry, knowledge, projects).
Audit findings ARC-12, ARC-13, F-02, and MOD-03 all flag the same root cause:
too many concerns in one file, with `build_toolsets` carrying a C901 suppression.

**Question:** Is the proposed split into `bootstrap/` package (hooks.py, toolsets.py,
knowledge.py, registry.py) sound? Are there blockers (circular deps, import
breakage, test friction)?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python docs — Regular packages | <https://docs.python.org/3/reference/import.html#regular-packages> | .90 |
| 2 | Flask `__init__.py` re-export pattern | <https://github.com/pallets/flask/blob/main/src/flask/__init__.py> | .85 |
| 3 | Pydantic `__init__.py` lazy re-exports | <https://github.com/pydantic/pydantic/blob/main/pydantic/__init__.py> | .80 |
| 4 | PydanticAI toolsets/ package | <https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/toolsets> | .85 |

## 3. Analysis

### 3a. Natural split boundaries

The file has 6 clear functional blocks with no cross-calls between them:

| Block | Lines | Functions | Proposed file |
|-------|-------|-----------|---------------|
| Active project resolution | 86–120 | `_resolve_active_project` | `__init__.py` (stays) |
| BootstrapResult dataclass | 128–160 | `BootstrapResult` | `__init__.py` (stays) |
| Hook assembly | 161–225 | `build_hooks` | `hooks.py` (~65 lines) |
| Channel factory | 226–257 | `create_channel` | `channel.py` (~32 lines) |
| Knowledge infra + builders | 258–580 | `_KnowledgeInfra`, `_build_knowledge_infra`, `_build_knowledge_toolset`, `_build_bookmark_toolset`, `_build_knowledge_source_toolset`, `_build_web_search_toolset`, `_build_screenshot_components` | `knowledge.py` (~320 lines) |
| Toolset assembly + wrapping | 583–728 | `build_toolsets` | `toolsets.py` (~145 lines) |
| MCP registry | 730–770 | `build_mcp_registry` | `registry.py` (~40 lines) |
| Agent registry | 772–835 | `build_agent_registry` | `registry.py` (same, ~105 lines total) |
| Project toolset helpers | 837–875 | `_add_project_toolset`, `_patch_project_toolset_agent` | `toolsets.py` (combine w/ build_toolsets) |
| Main orchestrator | 877–992 | `bootstrap` | `__init__.py` (~115 lines) |

### 3b. Dependency graph between proposed submodules

```
__init__.py  →  hooks.py, channel.py, toolsets.py, registry.py
toolsets.py  →  knowledge.py  (calls _build_knowledge_infra, _build_knowledge_toolset, etc.)
registry.py  →  (no internal deps — uses only external owlbear.* imports)
hooks.py     →  (no internal deps — uses only external owlbear.* imports)
channel.py   →  (no internal deps)
knowledge.py →  (no internal deps)
```

**No circular dependency risk.** The dependency graph is a DAG: `__init__.py` at top,
submodules are leaves or at most one level deep (toolsets → knowledge).

### 3c. Backwards compatibility — consumer analysis

| Consumer | Import path | Break risk |
|----------|-------------|------------|
| `bearclaw/cli.py` | `from owlbear.bootstrap import bootstrap` | None — stays in `__init__.py` |
| `tests/test_bootstrap.py` | `BootstrapResult`, `_resolve_active_project`, `build_hooks`, `build_toolsets`, `create_channel` | None — re-export from `__init__.py` |
| `tests/test_bootstrap_integration.py` | `BootstrapResult`, `bootstrap` | None — stays in `__init__.py` |
| `tests/test_integration_e2e.py` | `bootstrap` | None |
| `tests/test_pipeline_e2e.py` | `BootstrapResult`, `bootstrap` | None |
| `tests/test_inter_doc_*.py` | `_build_knowledge_infra`, `_build_knowledge_toolset` | Re-export needed |
| `tests/test_knowledge_*.py` | `_build_knowledge_infra`, `_build_knowledge_toolset`, `build_toolsets` | Re-export needed |
| `tests/test_cli.py` etc. | `patch("owlbear.bootstrap.bootstrap", ...)` | None — `owlbear.bootstrap.bootstrap` still resolves |

**Strategy:** `__init__.py` re-exports all current `__all__` symbols + private helpers that
tests import. Flask uses exactly this pattern — 39-line `__init__.py` with `from .app import
Flask as Flask` etc. Zero breaking changes.

### 3d. Trade-off: proposed layout vs alternatives

| Criterion | A: 5-file split (proposed) | B: 3-file split (min) | C: Keep monolith |
|-----------|---------------------------|----------------------|-------------------|
| `__init__.py` LOC | ~130 | ~200 | 992 (fail AC) |
| C901 elimination | Yes (split `build_toolsets` from knowledge) | Partial | No |
| Smallest file | ~32 (channel.py) | ~280 | N/A |
| Largest submodule | ~320 (knowledge.py) | ~450 | N/A |
| Import breakage | Zero (re-exports) | Zero | N/A |
| Circular dep risk | None | None | N/A |
| Test changes | Zero (re-exports) | Zero | N/A |
| KISS | High — each file ≤1 concern | Medium | Low |

### 3e. Magic strings status

ARC-13 flagged `_destructive = {"GitLocalToolset", "TerminalToolset", "GitHubToolset"}` (string
matching). **Already fixed** — current code uses `_destructive_types = (GitLocalToolset,
TerminalToolset, GitHubToolset)` with `isinstance()`. This AC criterion is already met.

### 3f. C901 resolution path

`build_toolsets` currently has `# noqa: PLR0913, PLR0912, PLR0915, C901`. After the split:

- Knowledge builder calls move to `knowledge.py` (~320 lines)
- `build_toolsets` in `toolsets.py` becomes ~100 lines: core toolsets + conditional + wrapping
- The wrapping logic (HookedToolset + ApprovalGateToolset) can stay inline since it's sequential
- Expected: C901 suppression removable, PLR0912/PLR0915 likely also removable

## 4. Recommendation (.90 confidence)

**Option A: 5-file split** is the right approach.

Proposed layout:
```
src/owlbear/bootstrap/
    __init__.py   # BootstrapResult, _resolve_active_project, bootstrap(), re-exports
    hooks.py      # build_hooks
    channel.py    # create_channel
    knowledge.py  # _KnowledgeInfra, _build_knowledge_infra, _build_knowledge_toolset,
                  # _build_bookmark_toolset, _build_knowledge_source_toolset,
                  # _build_web_search_toolset, _build_screenshot_components
    toolsets.py   # build_toolsets, _add_project_toolset, _patch_project_toolset_agent
    registry.py   # build_mcp_registry, build_agent_registry
```

**Risk:** `knowledge.py` at ~320 lines is the largest submodule. Could split further into
`knowledge.py` + `optional_toolsets.py` (web search, screenshots), but YAGNI for now.

**Implementation approach:**
1. Create `src/owlbear/bootstrap/` directory
2. Move functions to submodules (each with its own imports)
3. `__init__.py` re-exports everything via `from .hooks import build_hooks` etc.
4. Update `__all__` in `__init__.py` to match current exports
5. Delete old `src/owlbear/bootstrap.py`
6. Run `uv run pytest` + `uv run ruff check` — expect zero failures
7. Verify: `__init__.py` < 200 lines, no C901, no magic strings

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement bootstrap/ package split" --priority needed --status backlog --tags "refactor,modularity,scope:core" --body "Move build_hooks → hooks.py, create_channel → channel.py, knowledge builders → knowledge.py, build_toolsets → toolsets.py, registries → registry.py. __init__.py re-exports all public + test-imported private symbols. See docs/bootstrap-split-research.md §4. AC: (1) bootstrap/__init__.py < 200 lines, (2) no C901/PLR0912/PLR0915 suppressions in any submodule, (3) all existing tests pass with zero import changes, (4) ruff clean."
```
