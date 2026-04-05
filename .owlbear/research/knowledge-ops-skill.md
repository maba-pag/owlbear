# Knowledge-ops SKILL.md — Content Design Research

> **Owning task:** #774 — Create knowledge-ops SKILL.md for KnowledgeToolset guidance
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

Task #718 (cheat-sheet tool evaluation) recommended creating a `knowledge-ops`
SKILL.md to give agents format guidance when using knowledge tools. Three
toolsets expose 8 tools total. Without guidance, agents misuse `doc_type`,
scope parameters, and query formulation. What should the SKILL.md contain?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear KnowledgeToolset | `src/owlbear/tools/knowledge.py` | .95 — 3 tools: query, ingest, list |
| 2 | OwlBear KnowledgeSourceToolset | `src/owlbear/tools/knowledge_source.py` | .90 — 3 tools: add, list, refresh sources |
| 3 | OwlBear BookmarkToolset | `src/owlbear/memory/knowledge/bookmark_toolset.py` | .85 — 2 tools: bookmark, list |
| 4 | OwlBear kanban-md SKILL.md | `.github/skills/kanban-md/SKILL.md` | .90 — Template for decision tree + reference |
| 5 | LlamaIndex Tools docs | `developers.llamaindex.ai/python/.../tools/` | .75 — "tool name and description rely strongly on the tool name and description" — tuning matters |
| 6 | PydanticAI Toolsets docs | `ai.pydantic.dev/toolsets/` | .70 — FunctionToolset patterns |
| 7 | OwlBear SkillRegistry | `src/owlbear/skills/registry.py` | .85 — Glob scans `*.md` (flat), not `*/SKILL.md` |
| 8 | OwlBear knowledge models | `src/owlbear/memory/knowledge/models.py` | .80 — EntityType, RelationType, SourceType enums |

## 3. Analysis

### 3.1 What the SKILL.md Must Cover

| Section | Why | Source |
|---------|-----|--------|
| Decision tree | kanban-md SKILL.md proves decision trees reduce agent errors | #4 |
| Tool quick reference (8 tools) | LlamaIndex: tool selection depends heavily on description quality | #5 |
| Scope conventions | `global` vs `project:{id}` — agents need to know defaults | #1, #2 |
| Ingest workflow (text/file/url) | 3 `doc_type` values with different behaviors, delta checking | #1 |
| Source type configs | `url_list`, `crawl`, `file_glob` — config_json format undocumented | #2 |
| Entity/relation types | Returned in query results; agents should understand the graph model | #8 |

### 3.2 Structural Pattern (from kanban-md SKILL.md)

The kanban-md SKILL.md follows: frontmatter → rules → decision tree →
command reference. Knowledge-ops should mirror this: frontmatter → rules →
decision tree → tool reference → domain reference (scopes, types).

### 3.3 SkillRegistry Glob Gap (Critical)

The `SkillRegistry._scan()` uses `self._skills_dir.glob("*.md")` — a flat
glob that only finds files directly in the skills directory. All 17 existing
skills live in subdirectories (`kanban-md/SKILL.md`, etc.). This means the
SkillRegistry **cannot discover any existing skills** including the new one.

The VS Code Copilot skill system reads subdirectories natively, so skills work
in Copilot. But OwlBear's runtime `load_skill()` / `list_skills()` tools
are broken for the current directory layout.

**Impact:** Creating `knowledge-ops/SKILL.md` is still correct (VS Code reads
it), but the SkillRegistry glob must be fixed for runtime discovery.

### 3.4 Consuming Agents

| Agent | Has `knowledge` tool | Has `skills: []` | Needs skill |
|-------|---------------------|-------------------|-------------|
| researcher | Yes | Empty | Yes |
| curator | Yes | Empty | Yes |
| builder | No | kanban-md, tdd | No |
| orchestrator | No | kanban-md | No |

## 4. Recommendation (.85 confidence)

Create `.github/skills/knowledge-ops/SKILL.md` with:

1. **YAML frontmatter:** `name: knowledge-ops`, description referencing
   knowledge base querying, ingestion, and source management
2. **Decision tree:** 10-12 rows mapping agent intent to tool name
3. **Tool reference:** all 8 tools with parameters and valid values
4. **Scope conventions:** `global` (default), `project:{id}` when project set
5. **Domain reference:** EntityType, RelationType, SourceType valid values
6. **Ingest workflow:** text/file/url paths, delta checking, result format

Risk: Until SkillRegistry glob is fixed (#775), runtime `load_skill()` won't
find this file. VS Code copilot skills still work.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Fix SkillRegistry glob to scan subdirectory SKILL.md files" --priority needed --status ideation --tags "tooling,scope:core" --body "SkillRegistry._scan() uses skills_dir.glob('*.md') which only finds flat files. All 17 skills live in subdirectories (e.g. kanban-md/SKILL.md). Change glob to '*/SKILL.md' or '*/*.md'. See docs/research/knowledge-ops-skill.md §3.3."
```

```
kanban\kanban-md.exe create "Implement knowledge-ops SKILL.md content" --priority nice-to-have --status ideation --tags "tooling,docs,scope:core" --body "Write .github/skills/knowledge-ops/SKILL.md covering: decision tree (10-12 rows), tool reference (8 tools across 3 toolsets), scope conventions (global vs project:{id}), domain reference (EntityType/RelationType/SourceType), ingest workflow (text/file/url + delta checking). Follow kanban-md SKILL.md structure. Max ~150 lines. See docs/research/knowledge-ops-skill.md §4.\n\nAC:\n- [ ] YAML frontmatter with name: knowledge-ops and descriptive description\n- [ ] Decision tree table mapping agent intent to tool name\n- [ ] All 8 tools documented with parameters and valid values\n- [ ] Scope conventions section\n- [ ] Domain reference with valid EntityType, RelationType, SourceType values\n- [ ] SkillRegistry._parse_frontmatter() succeeds on the file"
```
