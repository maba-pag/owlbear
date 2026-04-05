# Cheat-Sheet Tool Pattern for Complex Toolsets — Research

> **Owning task:** #718 — Evaluate cheat-sheet tool pattern for complex toolsets
> **Date:** 2026-07-27 **Status:** Complete

## 1. Context and Question

Task #594 research (excalidraw-mcp) identified a "cheat-sheet tool" pattern: a companion tool (`read_me`) that pre-loads domain knowledge (formats, schemas, examples) into model context before the main tool call. Should OwlBear adopt this for its complex toolsets?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | .90 — Origin of `read_me` pattern |
| 2 | yctimlin/mcp_excalidraw (1.4k★) | <https://github.com/yctimlin/mcp_excalidraw> | .85 — Evolved pattern: `read_diagram_guide` |
| 3 | PMCP (ViperJuice/pmcp) | <https://github.com/ViperJuice/pmcp> | .80 — Multi-layer progressive disclosure |
| 4 | OwlBear SkillRegistry | `src/owlbear/skills/registry.py` | .90 — Existing progressive-loading pattern |

## 3. Pattern Variants in the Wild

### 3.1 Single Cheat-Sheet Tool (excalidraw/excalidraw-mcp)

`read_me` returns a structured prompt with element format, color palettes, and usage examples. Model calls it first, then uses knowledge for `create_view`. One-shot context load, ~500 tokens.

### 3.2 Design Guide Tool (yctimlin/mcp_excalidraw)

`read_diagram_guide` returns best-practice color palettes, sizing rules, layout patterns, and anti-patterns. "Dramatically improves AI-generated diagram quality" per README. Same pattern as `read_me` but domain-scoped to design quality rather than API format.

### 3.3 Multi-Layer Progressive Disclosure (PMCP)

4 guidance layers with token budgets:

| Layer | Content | Tokens |
|-------|---------|--------|
| L0 — MCP Instructions | Brief philosophy in server instructions | ~30 |
| L1 — Code Hints | Ultra-terse hints in search results | ~8-12/card |
| L2 — Code Snippets | Minimal examples in describe output (opt-in) | ~40-80 |
| L3 — Methodology Resource | Full guide (lazy-loaded) | 0 until loaded |

Claims 80% token reduction vs loading all schemas upfront. Progressive: compact cards → detailed schemas only on request.

### 3.4 OwlBear SkillRegistry (existing)

`list_skills` returns summaries; `load_skill` fetches full content on demand. Agent-level progressive loading — the model requests detailed instructions only when needed.

## 4. OwlBear Toolset Complexity Assessment

| Toolset | Tools | Complexity | Model Error Risk | Cheat-Sheet Value |
|---------|-------|-----------|------------------|-------------------|
| KanbanToolset | 7 | High — statuses, flags, filtering syntax | High | **High** |
| KnowledgeToolset | 3 | High — doc_type param, query syntax | Medium | **Medium** |
| KnowledgeSourceToolset | 3 | Medium — config_json format | Medium | Medium |
| DiagramToolset | 1 | Medium — diagram_type + source syntax | Low | Low |
| BrowserToolset | 6 | Medium — CSS selectors | Low | Low |
| GitLocalToolset | 7 | Low — git semantics well-known | Low | None |

## 5. Analysis: Approaches Compared

| Criterion | Companion Tool | Enhanced Descriptions | SkillRegistry (existing) |
|-----------|---------------|----------------------|--------------------------|
| Token cost | ~200-500/call (on demand) | ~50-100/tool (always loaded) | ~50 summary + full on demand |
| Dev effort | ~50 LOC per toolset | ~20 LOC per tool | Already built |
| KISS | Medium — new tool per set | **High** — minimal change | **High** — already exists |
| Context scope | Tool-level format guidance | Parameter-level hints | Agent-level workflow guidance |
| When useful | Complex formats, many params | Quick parameter hints | Multi-step workflows |
| YAGNI risk | **High** if model rarely calls it | Low | None |

### Key insight: OwlBear's agents already have rich context

Unlike generic MCP servers (where the model has no system prompt), OwlBear agents have:

- `.agent.md` system prompts per agent role
- Skills loaded via SkillRegistry (e.g., `kanban-md` skill for KanbanToolset)
- `.instructions.md` files scoped via `applyTo` patterns

This means the marginal value of cheat-sheet companion tools is **lower** than in the excalidraw-mcp context, where the `read_me` tool is the _only_ source of format guidance.

## 6. Recommendation (.75 confidence)

**Tier 1 — Do now (KISS, high value):** Enhance tool descriptions for KanbanToolset and KnowledgeToolset. Add parameter examples, valid enum values, and format hints directly in tool docstrings. Cost: ~20 LOC per tool. Zero runtime overhead.

**Tier 2 — Pilot if Tier 1 insufficient (.60 confidence):** Add one `read_kanban_guide()` companion tool to KanbanToolset as a pilot. KanbanToolset has the highest complexity (7 tools, status workflow, flag combos). Measure whether models call it and whether it reduces errors. If the pilot shows no measurable improvement, don't expand.

**Do NOT:** Add cheat-sheet tools to all toolsets. Most toolsets are simple enough that enhanced descriptions suffice. YAGNI — "Just because we can" is not a reason.

### PMCP L0-L3 layers assessment

The multi-layer approach is elegant for a meta-gateway managing 50+ tools. OwlBear manages ~15 toolsets directly — the overhead of building a multi-layer disclosure system is not justified. The existing SkillRegistry already provides L3-equivalent lazy loading.

## 7. Follow-up Tasks

```
kanban\kanban-md.exe create "Enhance tool descriptions for KanbanToolset" --priority nice-to-have --status backlog --tags "tooling,scope:core" --body "Add parameter examples, valid enum values (statuses, priorities, flags), and format hints to all 7 KanbanToolset tool docstrings. Goal: reduce model errors when calling kanban tools without needing a separate cheat-sheet tool.\n\nAC:\n- [ ] All 7 tool docstrings include parameter examples\n- [ ] Status/priority enums listed in descriptions\n- [ ] Flag combinations documented (--blocked, --not-blocked, etc.)\n- [ ] No new tools or files added"
```

```
kanban\kanban-md.exe create "Enhance tool descriptions for KnowledgeToolset" --priority nice-to-have --status backlog --tags "tooling,scope:core" --body "Add parameter examples and format hints to KnowledgeToolset tool docstrings — especially ingest_document (doc_type values, expected input formats) and query_knowledge (query syntax).\n\nAC:\n- [ ] ingest_document docstring lists doc_type values with examples\n- [ ] query_knowledge docstring shows example queries\n- [ ] list_knowledge_sources shows example output format"
```
