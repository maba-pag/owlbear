# Context

## Initial Request

Improve the kanban engine + MCP server in two related ways:

1. **`read_task` on archived tasks**: Currently returns "not found" because archived tasks are moved out of `tasks/` into the archive folder. Agents lose visibility. Options the user floated:
   - Return "task archived" message
   - Return "task archived, use parameter XYZ to read content"
   - Return only the YAML header (so agent sees it's archived + when + dependencies)
   - Just return the task transparently
2. **Track archival reason** in a new YAML header field. Standard pipeline-completed tasks carry the auditor's confidence. Other archival paths (deprecated, dropped from plan, superseded, duplicate) currently leave no breadcrumb.

## Stated Intent

> Give the agent using the tool the information it could need, without giving too much.

## Initial Tier Read

Re-tiered after M2: **Small / Medium**. The user explicitly opened scope to a full kanban MCP surface review, with no backwards-compat constraints, and demanded an agent-workflow-driven analysis order (workflows → needs → surface comparison). Optimization target is the **consuming agent**, not the codebase.

## M1 Findings

### Primary consumers of `read_task` on archived tasks

- **Agents resolving dependencies** — a `depends_on` ID may point at something archived; the agent needs to know it's done/dropped/superseded, not just "missing".
- **Auditor/reviewer agents tracing history** — looking back at why something was decided, what was done, what was killed.

Not a primary path: human inspection (humans use Cockpit / `ls` for that).

### Archival reason vocabulary (confirmed)

- `completed` — standard auditor flow, carries auditor confidence
- `deprecated` — superseded by newer task
- `dropped` — removed from plan, no longer wanted
- `duplicate` — merged into another task
- `wontfix` — out of scope / decided against

Not adopted: `experimental-spike` (low signal, can fold into `completed` with body notes).

## Problem Statement (M1 close)

When a task is archived, kanban MCP `read_task` returns a flat "not found" error. The two real consumers — agents resolving `depends_on` and auditor/reviewer agents tracing history — lose the signal that the task ever existed, why it ended, and what it depended on. Even when agents reach archived content via other means, the **reason** for archival is not captured in machine-readable form: standard pipeline-completed tasks carry auditor confidence, but tasks killed via deprecation, drop, duplication, or wontfix leave no structured breadcrumb. The fix lives in two places: `read_task` behavior on archived tasks, and a new YAML header field capturing archival reason.

## Outcomes (M2 close — locked)

1. An agent resolving a dependency or auditing history gets the info it needs in the **minimum number of tool calls and the minimum context window cost** — without that cost shifting into figuring out *which* tool to call or *how*.
2. **Archived tasks are first-class readable** by the kanban MCP surface — no "not found" surprises, no special incantations.
3. **Every archived task carries a structured archival reason** (`completed`, `deprecated`, `dropped`, `duplicate`, `wontfix`) so "why is this dead?" is a one-field lookup.
4. **The kanban MCP tool surface is coherent after the change** — no vestigial parameters, no overlapping tools, no ambiguity. Renames/splits/merges/drops all on the table.

*(Migration of existing archived tasks is consumer-side trivia, not a design constraint.)*

## M3 Plan — agent-workflow-first analysis

User explicit ordering:

1. **Map what agents DO** with kanban (per-role workflows: orchestrator, builder, reviewer, auditor, planner, researcher, etc.).
2. **Map what agents NEED** from kanban to do that work (reads, writes, lookups, projections).
3. **Map what we currently PROVIDE** (the 8 owlbear-kanban MCP tools + their params).
4. Gap analysis: what's missing, what's excess, what's misshapen, what would collapse multiple calls into one.
5. Only then design the new surface.

## Panelist composition (M3→M4)

- **ideation-enduser** — the consuming agent IS the end-user; ergonomics, fewest-calls, least-context are core
- **ideation-architect** — tool surface coherence, parameter design, naming
- **ideation-data** — YAML schema for archival_reason, projection shapes (TaskSummary etc)
- *Skip security* — no new trust boundary; archived tasks are not more sensitive than active ones

## M3 Findings (locked)

### Confirmed bugs / structural gaps

1. **`show_task` cannot read archived tasks.** Engine `_find_task_path` and `show_task` are scoped to `tasks_dir` only; no archive fallback. Surfaced as `FileNotFoundError` → MCP `ToolError`.
2. **`test-curator` depends on the broken path** — its Step 0 calls `show_task` per archived ID. Currently incoherent.
3. **No archival reason / no archive metadata field.** Tasks killed via deprecated/dropped/duplicate/wontfix leave no structured trace. Standard auditor flow has confidence buried in `## Audit` body section.
4. **Tool-list vs skill-text mismatches in agent frontmatter:** `architect` lacks `edit_task`; `auditor` lacks `create_task`; `challenger` has zero kanban tools but its contract advertises reading task body.

### N+1 / over-fetch patterns

| Agent | Anti-pattern | Real need |
|---|---|---|
| architect | N `show_task` per `depends_on` ID just to read `status` | Batch `{id: status}` projection |
| test-curator | N `show_task` to filter by `status==archived` | Same batch projection (incl. archived) |
| memory-curator | N `show_task` across recent tasks to grep one section | Section-aware projection or full-text |
| orchestrator (stale path) | Full body fetch per stale task to extract last note | "Last note" projection |
| reviewer | Counts `## Review Evidence` repeats in body to detect loops | First-class cycle/fail count |
| scribe (resolve) | append + unblock = 2 `edit_task` calls per resolution | Atomic compound op |
| planner | N `create_task` calls (up to 20 per cycle) | Batch create |

### Section-as-schema (cross-cutting)

Nearly every pipeline agent fetches a full body to extract one named section (`## Architecture Review`, `## Test-Writer Notes`, `## Review Evidence`, `## Decision Resolved`, `## Action Completed`, `## Builder Notes`, `## Audit`, etc.). Sections are an **implicit schema** with zero projection support — the single biggest context-window sink.

### Orphan engine capabilities (engine has, MCP doesn't expose)

`valid_transitions`, `list_sessions`, `sweep`, `board_config`, `revision`. Some legitimate to keep hidden; others (`valid_transitions`, `list_sessions`) would help agents.

## Brief Split (locked — revised)

User correction: the original Brief A bled into engine territory. Hard re-cut:

1. **Brief A — THIS ONE: MCP tool surface ONLY.**
   - Tool list, tool names, parameter shapes, input contracts.
   - **Output projection shapes** (what JSON the calling agent receives) — including the new `archival_reason` field as a contract requirement on returned task shapes and the `archived` enum value.
   - Engine is a **black box**. Brief A does NOT specify engine methods, file paths, archive directories, `tasks_dir`, `_find_task_path`, or how the data is fetched. It only specifies what the MCP **caller** sees and sends.
   - Allowed to reference the *existence* of archived tasks as a state, not as a storage location.
2. **Brief B (future stub at handoff): Engine surface + MCP/GUI wiring.**
   - Public Python API of `owlbear_kanban` engine, designed to service **both** MCP server and Cockpit FastAPI.
   - Implements MCP server + Cockpit backend against a **stubbed** engine (interface only, fixtures or NotImplemented bodies).
3. **Brief C (future stub at handoff): Backend / persistence.**
   - Real engine implementation: files vs DB vs hybrid, indexes, archive layout, migration, performance.

## Panel for Brief A (revised scope)

- **ideation-enduser** — *primary voice.* The agent IS the user; ergonomics, fewest calls, least context, clearest tool names.
- **ideation-architect** — *secondary voice.* Tool surface coherence: naming, parameter shapes, atomicity, output projection schemas, the `archival_reason` enum.
- *Data folded into architect.* Only schema concerns in scope: `archival_reason` enum values and projection field shapes.
- *Skip security.* Trust boundary unchanged.

**Engine-agnostic constraint for panelists:** stances must NOT mention engine methods, storage paths, file layout, archive directories, or implementation mechanics. They specify only the MCP caller's view: what tools exist, what params they take, what JSON comes back.
