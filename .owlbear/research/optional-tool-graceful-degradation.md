# Graceful Degradation for Missing Optional Tools

> **Owning task:** #611 — Bootstrap should gracefully handle missing optional tools
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The researcher agent definition lists `knowledge` as a tool. When `qdrant-client`
isn't installed, `build_toolsets()` correctly skips the `KnowledgeToolset` (returns
`None`). However, `build_agent_registry()` builds a `_resolve` closure that raises
`KeyError` for any tool name not in the toolset map. When `AgentRegistry._build_agent()`
calls `_resolve("knowledge")`, it crashes instead of degrading gracefully.

**Root cause chain:**

1. `_build_knowledge_infra()` → catches `ImportError` → returns `None` ✓
2. `build_toolsets()` → skips knowledge toolset → not in `raw` list ✓
3. `build_agent_registry()._resolve("knowledge")` → `KeyError` ✗
4. `AgentRegistry._build_agent()` → list comprehension propagates `KeyError` ✗

The fix must be in steps 3–4. The question: **what pattern best handles this?**

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | LangChain `guard_import()` | `langchain_core/utils/utils.py` | .70 — fail-with-guidance, not skip |
| 2 | Haystack `LazyImport` | `haystack/lazy_imports.py` | .80 — deferred error via context mgr |
| 3 | OwlBear `build_toolsets()` | `src/owlbear/bootstrap.py:590-700` | .95 — existing try/except+warn+None |
| 4 | OwlBear `_build_knowledge_infra` | `src/owlbear/bootstrap.py:274-330` | .95 — existing catch-all→None |
| 5 | OwlBear `_build_web_search_toolset` | `src/owlbear/bootstrap.py:525-543` | .95 — existing catch-all→None |

## 3. Analysis

### Approach comparison

| Criterion | A: catch-skip in `_build_agent` | B: `optional_tools` field | C: resolver returns None | D: known-optional set |
|-----------|---------------------------------|---------------------------|--------------------------|----------------------|
| KISS | **High** — 5-line change | Low — schema + parser + defs | Medium — contract change | Medium — extra param |
| Typo safety | Low — masks typos | **High** — only optionals skip | Low — all names skip | High — explicit set |
| Consistency | **High** — matches `build_toolsets` | Medium — new concept | Low — new contract | Medium — new param |
| Agent def changes | **None** | All 8 files | None | None |
| Lines changed | ~10 | ~40 | ~15 | ~20 |
| YAGNI | **Best** — no new abstractions | Worst — premature field | Good | Medium |

### Risk analysis

| Risk | Mitigation |
|------|------------|
| A masks typos in tool names | Log at WARNING with tool name + agent name — typos visible in logs |
| A silently reduces agent capability | Log message makes it explicit; tests can assert warnings |
| B adds unnecessary complexity | YAGNI — we can add `optional_tools` field later if needed |
| C changes resolver contract | Would require auditing all resolver callers |

### Existing pattern in codebase

`build_toolsets()` already applies catch-and-skip to 5 conditional toolsets:

- `SkillRegistry` — try/except, log warning
- `GitHubToolset` — try/except, log warning
- `_build_knowledge_infra` → `_build_knowledge_toolset` — returns `None`, skipped
- `_build_bookmark_toolset` — returns `None`, skipped
- `_build_web_search_toolset` — returns `None`, skipped

The **same pattern** should be applied in `_build_agent` for individual tool resolution.

## 4. Recommendation (.90 confidence)

**Option A: catch-and-skip in `_build_agent`** — wrap tool resolution in try/except
per tool, log warning, continue with remaining tools.

Implementation location: `AgentRegistry._build_agent()` in
`src/owlbear/core/agent_registry.py`, lines ~170-175. Change the list comprehension
to a loop:

```python
# Before (crashes on missing optional)
toolsets = [self._resolve_tool(name) for name in defn.tools]

# After (skip + warn)
toolsets = []
for tool_name in defn.tools:
    try:
        toolsets.append(self._resolve_tool(tool_name))
    except KeyError:
        logger.warning(
            "Agent '%s': skipping unavailable tool '%s'",
            defn.name,
            tool_name,
        )
```

This is:

- **Consistent** with existing `build_toolsets()` patterns (sources 3-5)
- **KISS** — 5-line diff, no new abstractions
- **YAGNI** — no schema changes, no new fields
- **Safe** — WARNING log makes missing tools visible

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement graceful tool skip in AgentRegistry._build_agent" --priority critical --status backlog --tags "bugfix,config,phase-9" --depends-on 611 --body "Change list comprehension in _build_agent to loop with try/except KeyError. Log WARNING for each skipped tool. See docs/research/optional-tool-graceful-degradation.md §4. AC: (1) _build_agent catches KeyError per tool (2) WARNING logged with agent+tool name (3) Agent created with remaining tools (4) No behavior change when all tools present"
```

```powershell
kanban\kanban-md.exe create "Test graceful tool skip in agent registry" --priority critical --status backlog --tags "test,config,phase-9" --depends-on 611 --body "Add test: registry.get() succeeds when a tool in the definition is missing from the resolver. Assert WARNING logged. Assert agent has reduced tool set. Assert pipeline_e2e[researcher] passes without qdrant-client. See docs/research/optional-tool-graceful-degradation.md §4. AC: (1) test_missing_tool_skipped_with_warning (2) test_all_tools_present_unchanged (3) pipeline_e2e[researcher] green"
```

```powershell
kanban\kanban-md.exe create "Audit all agent definitions for optional tool dependencies" --priority needed --status backlog --tags "config,phase-9" --depends-on 611 --body "Review all 8 agent .md files in src/owlbear/agents/. Verify which tools depend on optional extras (knowledge→qdrant-client, browser→playwright, web_search→duckduckgo-search). Document in task body. Consider adding comments to agent defs noting which tools are optional. AC: (1) All optional tool dependencies documented (2) No agent definition lists a mandatory tool as optional"
```
