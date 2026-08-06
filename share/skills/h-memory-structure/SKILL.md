---
name: h-memory-structure
description: "Handbook: Memory entry structure — tiers, entry shape, and content-quality bar"
user-invocable: false
---

# Memory Entry Structure

> **Audience:** Agents writing post-task reflections and the memory-curator agent. **When:** Before calling `save_memory` (entry shape and quality checks) and during curation sessions. **Why:** Ensures entries meet the structural and quality bar for long-lived agent knowledge.

Structural standards for project memory entries in MCP (`owlbear-memory`) storage. Covers entry shape, tier selection, deduplication, and quality enforcement.

For tool syntax, see `h-mcp-memory`. For curation workflow, see `w-mem-curation`.

## Entry Shape

Memory entries use markdown body + YAML frontmatter. Core fields:

| Field | Type | Constraint |
|-------|------|-----------|
| `id` | str | Stable identifier (UUID recommended) |
| `title` | str | Required, non-empty |
| `categories` | list[str] | One or more values from the 9-value enum |
| `confidence` | float | Inclusive `[0.7, 1.0]` |
| `state` | str | One of: `pending`, `curated`, `approved`, `contested`, `disputed`, `stale`, `deleted` |
| `content` | str | Markdown body |
| `scope_agents` | list[str] | Scope list (empty list allowed) |
| `source_agent` | str | Required; immutable provenance marker |
| `created_at` | str | UTC timestamp |
| `updated_at` | str | UTC timestamp |
| `approved_at` | str \| null | Approval timestamp (set on approve, cleared on downgrade/delete) |

Enumerations and ranges used by the schema:

- `categories` values: `domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`
- `state` values: `pending`, `curated`, `approved`, `contested`, `disputed`, `stale`, `deleted`
- `confidence` range: inclusive `[0.7, 1.0]`

This schema is validated by `MemoryEntry` in the `memory-mcp` package.

## Tier-Content Fit

Per `owlbear-system.instructions.md` § Memory Governance (single source of truth):

| Content type | Tier | Store |
|-------------|------|-------|
| Agent institutional knowledge (queryable) | MCP canonical | `owlbear-memory` |
| Job-specific context and working state | Native artifacts | Change/job records or `.owlbear/scratch/` |
| Architecture decisions | Not memory | Native change decisions and requests |
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
reflection.

See `share/diagrams/memory-layers.excalidraw` for a visual overview of the tier and state model.

## State Model

Lifecycle transitions are controlled by the memory service. MCP tools expose ordinary curation,
approval, assessment, and deletion; Cockpit is the human resolution surface for exceptional states.

| From | To | Trigger | Tool |
|------|----|---------|------|
| `pending` | `curated` | Curator assigns non-empty scope during curation | `curate_memory` |
| `curated` | `approved` | User approval | `approve_memory` |
| `approved` | `curated` | Any curation edit (auto-downgrade) | `curate_memory` |
| `curated` / `approved` | `contested` | First factually-wrong assessment | `assess_memories` |
| `contested` | `disputed` | A second task reports the entry factually wrong | `assess_memories` |
| `curated` / `approved` / `contested` | `stale` | Non-use exceeds the slot-efficiency threshold | `assess_memories` |
| `contested` / `disputed` / `stale` | `approved` | User resolves the exceptional state | Cockpit (`MemoryEngine.resolve`) |
| `pending` | `deleted` | Prune noise/duplicates (hard delete from disk) | `delete_memory` |
| `curated` / `approved` / `contested` / `disputed` / `stale` | `deleted` | Retire guidance (soft delete) | `delete_memory` |

`contested` remains recallable at curated priority. `disputed` and `stale` are excluded from recall.
MCP curation edits are blocked for all three exceptional states until the user resolves them in
Cockpit. Tool responses include hints describing the transition or deletion branch applied.

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
2. **Writing to `/memories/` for agent learnings.** The built-in store is retired. Agent learnings go to `owlbear-memory` only.
3. **Recording with `scope_agents=null`.** Global entries flood every agent's pre-flight. Always pass `scope_agents`.
4. **One entry per task regardless of insight count.** Record 0 entries if nothing notable happened. Record N entries for N distinct insights.
5. **Confidence below 0.7.** The server rejects it. Do not round up to bypass the floor — raise confidence only when evidence justifies it.
