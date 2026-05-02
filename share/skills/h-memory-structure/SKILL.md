---
name: h-memory-structure
description: "Handbook: Memory entry structure — tiers, entry shape, and content-quality bar"
user-invocable: false
---

# Memory Entry Structure

Structural standards for project memory entries across file-based (`/memories/`) and MCP (`owlbearMemory`) storage. Covers entry shape, tier selection, deduplication, and quality enforcement.

For tool syntax, see `h-mcp-memory`. For curation workflow, see `w-mem-curation`. For pipeline integration (pre-flight, reflection), see `r-pipeline-protocol`.

## Entry Shape

Memory entries use markdown body + YAML frontmatter. Core fields:

| Field | Type | Constraint |
|-------|------|-----------|
| `id` | str | Stable identifier (UUID recommended) |
| `title` | str | Required, non-empty |
| `categories` | list[str] | One or more values from the 9-value enum |
| `confidence` | float | Inclusive `[0.7, 1.0]` |
| `state` | str | One of: `pending`, `curated`, `approved`, `deleted` |
| `content` | str | Markdown body |
| `scope_agents` | list[str] \| null | Optional scope list |
| `created_at` | str | UTC timestamp |
| `updated_at` | str | UTC timestamp |

This schema is validated by `MemoryEntry` in the `mcp-memory` package.

**File-based entry shape** (inbox fallback):

```
# {task-id}-{agent}.md
agent: {agent_name}
task: {task_id}
date: {YYYY-MM-DD}
- {bullet}
```

## Tier-Content Fit

Per `owlbear-system.instructions.md` § Memory Governance (single source of truth):

| Content type | Tier | Store |
|-------------|------|-------|
| Tool patterns, CLI recipes, process pitfalls | User | `/memories/` |
| Task-specific context, in-progress working state | Session | `/memories/session/` |
| Agent lessons-learned (curation inbox) | Repo inbox | `/memories/repo/inbox/` |
| Agent institutional knowledge (queryable) | MCP canonical | `owlbearMemory` |
| Architecture decisions | Not memory | `.owlbear/decisions/` |
| Research findings | Not memory | `.owlbear/research/` |
| Code snippets, task-specific context | Not memory | Do not record |

**User memory** (`/memories/`) is for the human operator's preferences, not agent learnings.

## File vs. MCP Relationship

During active migration, both stores are written. After migration, MCP is sole canonical.

| Situation | Action |
|-----------|--------|
| Standard post-task reflection | Write MCP first via `store_learning`, then file-based inbox as fallback |
| MCP tool unavailable or errors | Write file-based inbox only; do not retry MCP |
| Curation pass | Read both sources (see `w-mem-curation` Step 1); merge into MCP |
| Pre-flight knowledge load | MCP only (`query_memory`) — file inbox is write-only for agents |

Dual-write procedure is defined in `r-pipeline-protocol` § Post-task Reflection. Follow it exactly.

## Deduplication Rules

These rules apply at **write time** to prevent recording near-duplicates. Curation-time dedup (grouping, merging, pruning) is handled by `w-mem-curation` Step 2 — do not replicate that logic here.

**Before calling `store_learning`:**

1. Call `query_memory()` (or `query_memory(states=["pending","curated","approved"])` for broader checks) and scan returned entries.
2. If an existing entry covers the same core insight, **do not record**. Append new evidence as a note to the task body instead.
3. If an existing entry is partially overlapping, record only the delta (what the existing entry lacks).
4. On conflict (new entry contradicts an existing approved entry), record the new entry with `categories=["knowledge"]` and note the conflict in the `content` field: `"Contradicts {entry_id}: ..."`.

**Which entry wins:** The most recently recorded entry with higher confidence wins at retrieval. The curator resolves conflicts during curation — do not delete approved entries yourself.

## Content-Quality Bar

An entry **passes** if all of the following are true:

- Cites a specific task ID, file path, or tool name (not abstract advice)
- Actionable: an agent can apply it in the next 30 seconds without further research
- Non-obvious: not in the standard Python/FastAPI/MCP documentation
- Single insight: one problem–solution pair, not a list of tips

An entry **fails** if any of the following are true:

- Generic: "always write tests", "use type hints", "be careful with async"
- No citation: no task ID, file, or tool mentioned
- Ambiguous scope: the insight only applies to a specific project but `scope_agent` is null
- Ambiguous scope: the insight only applies to a specific role but `scope_agents` is missing
- Duplicate: substantially the same as an existing approved entry

**Confidence calibration:**

| Confidence | When to use |
|-----------|------------|
| 0.7 | Single occurrence, plausible but unverified |
| 0.8 | Single occurrence, verified by test or observation (pipeline default) |
| 0.9 | Recurring pattern (2+ tasks) |
| 1.0 | Reserved — do not use |

## Anti-Patterns

1. **Storing research findings as memory entries.** Research belongs in `.owlbear/research/`; memory is for agent behavioral learnings.
2. **Writing to `/memories/` for agent learnings.** User memory is the operator's space. Agent learnings go to `owlbearMemory` and the inbox.
3. **Recording with `scope_agent=null`.** Global entries flood every agent's pre-flight. Always pass `scope_agent`.
4. **One entry per task regardless of insight count.** Record 0 entries if nothing notable happened. Record N entries for N distinct insights.
5. **Confidence below 0.7.** The server rejects it. Do not round up to bypass the floor — raise confidence only when evidence justifies it.
