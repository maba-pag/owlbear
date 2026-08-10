# Brief C — Kickoff Prompt

**Status:** Ready for ideator (M1 entry).
**Predecessor:** Brief B (this directory) — engine API + adapter mapping (locked).
**Target audience:** the next ideation session that produces the storage-layer Brief.

---

## Use this prompt to start Brief C

Paste the body below into a new ideator session. The Working Directory must be created at `.owlbear/briefs/draft-kanban-storage-c-<DATE>/`, and the ideator must be told that **Brief B is the upstream contract** — Brief C cannot revisit any Brief B decision.

---

## Body of the kickoff prompt

> **Brief C — Kanban storage layer.**
>
> We have just locked Brief B (`.owlbear/briefs/draft-kanban-engine-b-2026-04-20/`), which defines the kanban **engine API**, role views (`AgentEngineView`, `CockpitEngineView`, `OrchestratorView`), error taxonomy, and adapter mapping for MCP and Cockpit. The engine is implemented on top of an opaque storage layer; Brief C designs that layer.
>
> ### What Brief C must produce
>
> A locked storage-layer contract that the engine implementation can build against. Specifically:
>
> 1. **Storage primitives.** Atomic ID allocation under concurrent `create_task` calls. Locking strategy for read/write contention. File-on-disk layout (or DB schema, if Brief C goes that way) for tasks, archive, sessions.
> 2. **Frontmatter format.** Field set, type discipline, ordering rules, validation timing. Must support every projection field declared in Brief B paper-integration §2 (`TaskSummary`, `TaskFull`, `DispatchEntry`, `Wave`).
> 3. **Body markdown round-trip.** Brief B D40 deferred this: byte-exact vs. normalised, list-style preservation, blank-line collapsing, heading-level preservation. Brief C must pick one and own its visible consequences (e.g. for `show_task(section=...)` and `edit_task(append_body=...)`).
> 4. **Migration plan.** Existing task files affected by Brief B D11 (drop `claimed_by`) and D14 (UTC + offset on every timestamp) must be migrated before the new engine ships. Specify the migration script's responsibilities and idempotency guarantees.
> 5. **Performance characteristics for bulk reads.** `list_tasks` and `pick_tasks` are O(n) over the task directory today. Brief C decides whether to add an index/cache and what its consistency contract is.
> 6. **Corruption surfacing.** Brief B raises `CorruptionError` (D27) on duplicate frontmatter IDs (D19). Brief C decides what other corruption modes are detected at read time, and how the storage layer signals them to the engine.
> 7. **Predicate DSL operator extensions** beyond Brief B D64 (which locks three keys: `required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`). Brief C planning may add new keys (regex matchers, frontmatter requirements, etc.) as discrete decisions.
>
> ### What Brief C must NOT touch
>
> The Brief B engine API surface is **frozen**. Brief C cannot:
>
> - Change any method signature in `paper-integration.md` §1.
> - Change the role-view exposure matrix (paper §5).
> - Change the error taxonomy or canonical error-code list (D27 + D57).
> - Add fields to `TaskSummary` / `TaskFull` / `DispatchEntry` / `Wave` projections (paper §2).
> - Change the `BoardConfig` shape (D62/D63/D64/D65) or any cross-cutting contract (paper §3).
> - Change `pick_tasks` algorithm (paper §1.3 4-step pipeline).
> - Change adapter responsibilities (brief §4).
>
> If Brief C planning surfaces a need to revisit any of these, that is a Brief B bug — file it as a Decision-Request task against Brief B; do not silently change the contract in Brief C.
>
> ### Inputs
>
> Read these into the Working Directory:
>
> - **Normative:** `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md` (Brief B contract), `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md` (Brief B D1–D65), `.owlbear/briefs/kanban-mcp-surface-v2/brief.md` (Brief A consumer surface).
> - **Code reality:** current storage code in `serve/kanban/src/owlbear_kanban/` (esp. anything that reads/writes `.owlbear/kanban/tasks/*.md`); current archive layout under `.owlbear/kanban/archive/`; existing migration scripts in `.owlbear/scripts/`.
> - **Brief C handoff notes:** Brief B `brief.md` §6 lists the four natural-extension items that are explicitly Brief C's territory.
>
> ### Tier and aperture
>
> **Studio tier, wide aperture.** Brief B set the precedent: no backwards compat, no legacy preservation for its own sake. If existing storage code is wrong, it changes. If the existing on-disk format is wrong, the migration script fixes it.
>
> ### Outcome quality bar
>
> Brief C must be self-sufficient enough that **engine implementation tasks can be derived directly from it**, the same way Brief B's `paper-integration.md` is the normative source for engine-implementation decomposition. The storage layer must have a single normative document with argument-level cells, locked decisions, and an explicit AC table.
>
> ### Forbidden in Brief C
>
> - **No `agent_name` parameter** anywhere (D33 + D43 — engine writes no log; storage layer doesn't log either).
> - **No `claimed_by` field** in frontmatter or anywhere on disk (D11).
> - **No diagnostic log written by storage** (D43 — engine is a pure state machine, storage extends that property).
> - **No partial-application paths** — storage must support engine D41 atomicity end-to-end. If a write would cause partial state on failure, that's a storage bug.
>
> ### Begin
>
> Start at M1 (Understanding). Frame the storage problem in terms of the engine consumer above; the user has already lived through three months of storage pain points (archive blindness, missing `archival_reason`, race conditions on claim, restart-eats-stale-claim) and most of those are now fixed *above* the storage layer by Brief B. Brief C must not re-solve them; it must support the fixes cleanly.

---

## Why this prompt exists

The Brief B M5 protocol calls for "engine implementation tasks decomposed by planner from `paper-integration.md`". The user explicitly chose to defer task decomposition until the briefs themselves are clear enough that decomposition is a mechanical exercise. This prompt makes Brief C the same kind of artefact: when Brief C is done, **its** `paper-integration.md` (or equivalent normative document) should be self-sufficient for storage-layer task generation.

This file is **not** a Brief itself. It is the seed for the next ideation session.
