# Cheat-Sheet Tool Pattern for Complex Toolsets

> **Owning task:** #718 — Evaluate cheat-sheet tool pattern for complex toolsets
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

Excalidraw-mcp uses a `read_me` companion tool that pre-loads domain
knowledge (element format, palettes, examples) into model context before
the main `create_view` call. Should OwlBear adopt this pattern for
KanbanToolset and KnowledgeToolset?

Three strategies compared: (A) enriched inline descriptions,
(B) companion read_me tool per toolset, (C) system prompt / skill injection.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | .90 — Origin of the `read_me` pattern |
| 2 | DougTrajano/pydantic-ai-skills | <https://github.com/DougTrajano/pydantic-ai-skills> | .85 — Progressive disclosure for PydanticAI |
| 3 | Agent Skills spec (agentskills.io) | <https://agentskills.io> | .80 — Open standard for on-demand skill loading |
| 4 | PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | .75 — PreparedToolset, dynamic definitions |
| 5 | OwlBear SkillRegistry | `src/owlbear/skills/registry.py` | .95 — Existing progressive disclosure impl |
| 6 | OwlBear kanban-md skill | `.github/skills/kanban-md/SKILL.md` | .90 — Existing cheat-sheet for kanban ops |

## 3. Analysis

### 3.1 Approach Comparison

| Criterion | A: Enriched descriptions | B: Companion read_me tool | C: Skill injection |
|-----------|--------------------------|---------------------------|---------------------|
| Token cost per turn | Low (~50 extra tokens) | Medium (~500 on-demand) | High (always loaded) |
| Extra tool calls | 0 | 1 per toolset per session | 0 (or 1 via load_skill) |
| Implementation | ~50 LOC (string edits) | ~100 LOC per toolset | 0 LOC (skills exist) |
| Model must know to call | No | Yes | Only for load_skill |
| Progressive disclosure | No | Yes | Yes (via SkillRegistry) |
| KISS | Best | Over-engineering | Good |
| Duplication risk | None | Duplicates SkillRegistry | None |

### 3.2 Existing Infrastructure Assessment

OwlBear already has progressive disclosure via `SkillRegistry`:

- `list_skills()` → agent sees skill names + descriptions
- `load_skill("kanban-md")` → loads full SKILL.md (~200 lines of CLI commands,
  decision tree, format guidance)
- 7/9 agents have `kanban-md` skill in their definition; those agents get
  `list_skills`/`load_skill` tools automatically

**This is functionally identical to excalidraw-mcp's `read_me` pattern.**
The model calls `load_skill("kanban-md")` instead of `read_me()`.

### 3.3 Gap Analysis

| Gap | Impact | Fix |
|-----|--------|-----|
| KanbanToolset descriptions are terse (e.g., "Create a new kanban task") | Model may use wrong statuses/priorities | Enrich 3-4 descriptions with valid values |
| No `knowledge-ops` skill exists | Model has no format guidance for knowledge tools | Create SKILL.md |
| Researcher/curator agents have `skills: []` | Can't load kanban-md skill | Add kanban-md skill to those agents |

### 3.4 Why NOT Companion read_me Tools

1. **Duplication.** SkillRegistry already provides `list_skills`/`load_skill` —
   adding per-toolset `read_me` tools creates two mechanisms for the same
   purpose.
2. **YAGNI.** The excalidraw pattern exists because MCP servers don't have
   OwlBear's skill infrastructure. OwlBear does.
3. **Tool proliferation.** Every toolset gaining a `read_me` tool adds clutter
   to the model's tool list. Skills are opt-in and loaded on demand.
4. **PreparedToolset** (PydanticAI) could dynamically enrich descriptions, but
   adds runtime complexity for a problem solvable with static string edits.

## 4. Recommendation (.80 confidence)

**Don't add companion read_me tools. Instead:**

1. **Enrich inline tool descriptions** for high-error parameters (~50 LOC):
   - `kanban_create`: mention valid priorities and status defaults
   - `kanban_move`: list valid statuses
   - `ingest_document`: expand doc_type options with examples
2. **Create a `knowledge-ops` SKILL.md** with format guidance for
   KnowledgeToolset (query patterns, ingest workflow, scope conventions)
3. **Add `kanban-md` skill** to researcher and curator agent definitions

Risk: If skill loading proves unreliable (model forgets to call `load_skill`),
revisit with PreparedToolset for automatic description enrichment.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Enrich KanbanToolset tool descriptions with valid statuses/priorities" --priority nice-to-have --status ideation --tags "tooling,scope:core" --body "Enrich inline description strings for kanban_create (valid priorities), kanban_move (valid statuses), and kanban_edit (valid fields). ~50 LOC of string changes in src/owlbear/tools/kanban.py. See docs/research/cheat-sheet-tool.md §4."
```

```
kanban\kanban-md.exe create "Create knowledge-ops SKILL.md for KnowledgeToolset guidance" --priority nice-to-have --status ideation --tags "tooling,docs,scope:core" --body "Create .github/skills/knowledge-ops/SKILL.md with query patterns, ingest workflow (text/file/url), scope conventions, and format guidance. See docs/research/cheat-sheet-tool.md §4."
```

```
kanban\kanban-md.exe create "Add kanban-md skill to researcher and curator agent definitions" --priority nice-to-have --status ideation --tags "config,scope:core" --body "Add kanban-md to skills list in src/owlbear/agents/researcher.md and src/owlbear/agents/curator.md so they can load kanban format guidance. See docs/research/cheat-sheet-tool.md §4."
```
