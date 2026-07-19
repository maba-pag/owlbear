---
name: h-memory-structure
description: "Handbook: Memory entry structure — tiers, entry shape, and content-quality bar"
user-invocable: false
---

# Memory Entry Structure

> **Audience:** Agents writing post-task reflections and the memory-curator agent. **When:** Before calling `save_memory` (entry shape and quality checks) and during curation sessions. **Why:** Ensures entries meet the structural and quality bar for long-lived agent knowledge.

Structural standards for project memory entries in MCP (`ob-memory`) storage. Covers entry shape, tier selection, deduplication, and quality enforcement.

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
| `scope_agents` | list[str] | Scope list (empty list allowed) |
| `source_agent` | str | Required; immutable provenance marker |
| `created_at` | str | UTC timestamp |
| `updated_at` | str | UTC timestamp |
| `approved_at` | str \| null | Approval timestamp (set on approve, cleared on downgrade/delete) |

Enumerations and ranges used by the schema:

- `categories` values: `domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`
- `state` values: `pending`, `curated`, `approved`, `deleted`
- `confidence` range: inclusive `[0.7, 1.0]`

This schema is validated by `MemoryEntry` in the `mcp-memory` package.

## Tier-Content Fit

Per `owlbear-system.instructions.md` § Memory Governance (single source of truth):

| Content type | Tier | Store |
|-------------|------|-------|
| Agent institutional knowledge (queryable) | MCP canonical | `ob-memory` |
| Task-specific context and working state | Task artifacts | Task body, `.owlbear/scratch/`, or kanban DR/AR files |
| Architecture decisions | Not memory | `.owlbear/kanban/decisions/` |
| Research findings | Not memory | `.owlbear/research/` |
| Code snippets, task-specific context | Not memory | Do not record |

The VS Code built-in `/memories/` store is retired for OwlBear agents. Do not use it for user preferences, session notes, repo inbox notes, or fallback agent learnings.

## MCP Relationship

MCP memory is canonical.

| Situation | Action |
|-----------|--------|
| Standard post-task reflection | Write MCP via `save_memory` |
| MCP tool unavailable or errors | Proceed without memory write; do not use `/memories/` fallback |
| Curation pass | Read MCP pending entries and promote durable insights into MCP |
| Pre-flight knowledge load | MCP only (`recall_memory(agent="{agent_name}")`) |

The always-loaded `owlbear-system.instructions.md` Memory Governance section triggers post-work
reflection. Pipeline recall and assessment are defined separately in `r-pipeline-protocol`.

See `share/diagrams/memory-layers.excalidraw` for a visual overview of the tier and state model.

## State Model

Lifecycle transitions are controlled by MCP tools:

| From | To | Trigger | Tool |
|------|----|---------|------|
| `pending` | `curated` | Curator assigns non-empty scope during curation | `curate_memory` |
| `curated` | `approved` | User approval | `approve_memory` |
| `approved` | `curated` | Any curation edit (auto-downgrade) | `curate_memory` |
| `pending` | `deleted` | Prune noise/duplicates (hard delete from disk) | `delete_memory` |
| `curated` | `deleted` | Prune superseded guidance (soft delete) | `delete_memory` |
| `approved` | `deleted` | Retire obsolete approved guidance (soft delete) | `delete_memory` |

Tool responses include hints describing which branch was applied (for example, pending promotion, approved downgrade, hard-delete vs soft-delete).

## Candidate Production

`save_memory` creates a pending candidate. Ordinary writers do not need `list_memories` or
`read_memory` authority and must not attempt store-wide deduplication before saving. Avoid a duplicate
only when the same insight is already visible in the current context. The memory curator performs
cross-store comparison, conflict handling, scoping, and pruning through `w-mem-curation`.

## Content-Quality Bar

An entry **passes** if all of the following are true:

- Cites a specific task ID, file path, or tool name (not abstract advice)
- Actionable: an agent can apply it in the next 30 seconds without further research
- Non-obvious: not in the standard Python/FastAPI/MCP documentation
- Single insight: one problem–solution pair, not a list of tips

An entry **fails** if any of the following are true:

- Generic: "always write tests", "use type hints", "be careful with async"
- No citation: no task ID, file, or tool mentioned
- Ambiguous scope: the insight only applies to a specific project but `scope_agents` is null
- Ambiguous scope: the insight only applies to a specific role but `scope_agents` is missing
- Duplicate: substantially the same as an existing approved entry

**Confidence calibration:**

| Confidence | When to use |
|-----------|------------|
| 0.7 | Single occurrence, plausible but unverified |
| 0.8 | Single occurrence, verified by test or observation |
| 0.9 | Recurring pattern (2+ tasks) |
| 1.0 | Reserved — do not use |

## Anti-Patterns

1. **Storing research findings as memory entries.** Research belongs in `.owlbear/research/`; memory is for agent behavioral learnings.
2. **Writing to `/memories/` for agent learnings.** The built-in store is retired. Agent learnings go to `ob-memory` only.
3. **Recording with `scope_agents=null`.** Global entries flood every agent's pre-flight. Always pass `scope_agents`.
4. **One entry per task regardless of insight count.** Record 0 entries if nothing notable happened. Record N entries for N distinct insights.
5. **Confidence below 0.7.** The server rejects it. Do not round up to bypass the floor — raise confidence only when evidence justifies it.
