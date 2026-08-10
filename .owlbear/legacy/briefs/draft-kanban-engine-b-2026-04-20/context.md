# Context — Brief B: Kanban Engine API & MCP Implementation

## Initial Request

User: "Let's work on Brief B of the kanban engine. Read kanban-mcp-surface-v2 (Brief A) first, then talk about engine interface + MCP implementation. Don't take prior decisions as truth — I am probably wrong on most of them. The kanban backend, engine, MCP, and Cockpit consumers are already working products; this is a refinement, not greenfield."

## Operating Constraint (carried from Brief B failure 2026-04-19)

This is a refactor/refinement brief over an existing, shipping engine (`serve/kanban/src/owlbear_kanban/`). M3 must include a forced read of (a) the actual engine implementation, (b) the actual data files, (c) the actual consumer code (MCP server, Cockpit), before any panelist deliberation. No greenfield assumptions. No rubber-stamping panel synthesis without code citation.

## User-Brought Direction (treat as direction, not truth)

### Decisions to keep unless code contradicts

1. Brief B scope = engine API + semantics + paper integration with Brief A. NO stubs, NO implementation. Bottom-up build (storage → engine → adapters) happens after Briefs A/B/C align. Paper integration = for every Brief A AC, document the engine-call sequence that fulfills it.
2. Engine is the single source of truth. MCP and Cockpit are sibling consumers. Storage is Brief C scope.
3. Brief A is mutable. Surface contract problems → propose Brief A revisions, don't twist Brief B around them.
4. One Cockpit per project, launched from consumer cwd. No project-switcher tabs. `KanbanEngine(kanban_dir, ...)` is single-board at construction. (Verify against current code.)
5. No top-down stub strategy. Scaffolding adapters against a fake engine is rejected.
6. Archive clears claim atomically. Verify in current `engine.py`; if not, propose as a fix.
7. Active expiration at engine startup + lazy expiration during runtime. Startup sweep exists today (`engine.sweep()`). Reality gap: Cockpit doesn't call it. Propose Cockpit calls it on init.
8. AC21 drops from Brief A (no enforcement of "non-claimant cannot end_work"). User-confirmed.
9. Duplicate frontmatter IDs treated as corruption, no auto-fix. Optional `repair-duplicates` CLI as conditional follow-up (cancelled if Brief C picks DBMS).

### Prior decisions contradicted by current code — re-litigate at M4 with code citations

1. **Claim identity (`actor` / `session_id` dropped).** Reality: `claimed_by` exists today but is theater.
3. **Wave composition algorithm.** Prior decision: two-phase, deterministic, priority weights, `agent_map` config. Current state: `pick_tasks` is flat; waves are human orchestrator work; `agent_map` doesn't exist.
4. **D9 (no locking).** Prior decision: YAGNI. Reality: `_exclusive_file_lock` already exists for `next_id`; Cockpit edits use optimistic-lock on `updated`. Re-decide: document what's already there, don't claim "no locking."
5. **TZ policy.** Prior: system local at engine init, explicit offset on output. Reality: writes are UTC. Decide: align Brief B with UTC reality, or propose behavior change (and accept migration cost on existing task files).
6. **TDD/clarity gates moved to write-time.** Prior: in-progress requires `## Test-Writer Notes` or `non-impl` tag; any active status requires `## AC` heading with ≥1 list item. Reality: clarity gate scans body anywhere not under `## AC`; escape is a 9-tag set, not single `non-impl`; statuses are hardcoded. Decide: keep gates at dispatch-time per existing reality, or move to write-time AND align predicates with what tasks actually use (most don't use `## AC` heading).
7. **`agent_map` as single dispatchability source.** Prior: config-driven status→agent. Reality: ranks live in `dispatch.py` constants. Decide: introduce `agent_map` config (net-new), or document existing rank model.

## Brief A — relevant contracts that constrain Brief B

- Engine must fulfill every tool contract in Brief A §5 with a single round trip per tool call (no internal N+1).
- Engine must compute `dep_status` per Brief A §7 semantics; consumed by both `list_tasks` and `pick_tasks`.
- Engine wave-composition: no intra-wave dep edges, no empty waves, no claimed/blocked, default `wave_size` config-sourced.
- Engine TZ resolution policy defines what `±HH:MM` value appears in projections — must be consistent within a single call.
- Engine produces `DispatchEntry.agent` (status→agent mapping).
- Cockpit GUI design picks up `list_sessions`-equivalent and admin release.
- AC21 ("end_work by non-claimant → ToolError") was user-dropped after Brief A approval.

## Investment Tier

**Studio** (confirmed M1). Multi-consumer refactor, 7 open conflicts, ~30-AC paper integration, three downstream consumers. Full panel + Explore-led code audit at M3.

## Confirmed Scope (M1)

- Engine API spec (method signatures, semantics, validation rules, projections, error model)
- MCP adapter mapping: for each Brief A tool, the engine-call sequence that fulfills it
- Cockpit-only engine surface: admin release, stuck-session inspection, claim sweep
- NO stubs, NO implementation. Bottom-up build (storage → engine → adapters) follows after Briefs A/B/C aligned.

## Out of Scope

- Storage / persistence (Brief C)
- Cockpit GUI design (separate brief)
- MCP wire schema (locked by Brief A — but Brief A is mutable; Brief B may surface revisions)

## Aperture

**Wide.** No backwards compat, no legacy code, break things, quality over everything regardless of complexity or cost. Brief B may redesign any engine surface found wanting at M3 — not constrained to "minimum to fulfill Brief A". This is consistent with Brief A's "no MCP backward compat" stance and the user's explicit instruction.

## AC21 Handling

User-confirmed: edit Brief A directly to remove AC21. To be done as part of M5/M6 alongside Brief B finalization.

## Paper Integration Format

Per-AC table in Brief B: `AC# | Brief A statement (compressed) | engine call sequence | error path | tested-by hint`. Auditor can binary-check coverage.

## Outcomes (M2 — locked after Critic + 4 architectural choices)

**O1 — Engine API is the single source of truth.** Each Brief A tool is fulfilled by exactly one caller-visible engine operation. The engine may require bulk index/snapshot capabilities from storage to honor that — those are explicit prerequisites for Brief C, not hidden assumptions. MCP becomes a mechanical translator: schema validation, error wrapping, response envelope construction. No business logic in the MCP layer.

**O2 — One engine, role-typed views.** `KanbanEngine` is the full surface. `AgentEngineView` and `CockpitEngineView` are thin facades exposing only their respective method subsets (agent-facing: claim/work lifecycle, dispatch, waves; cockpit-facing: admin release, stuck-session inspection, claim sweep, edit). Capability is a *type contract*, not a docstring or runtime guard. Both adapters (MCP server, Cockpit backend) construct the engine and select the appropriate view.

**O3 — Every reality conflict is resolved with a code citation.** The 7 user-named conflicts are the seeds; M3/M4 will surface more. Brief B records disposition (chosen direction + migration cost + file:line evidence) for every conflict found, not only the seven.

**O4 — Every Brief A AC has a paper-integration entry.** Per-AC table pinned to a specific Brief A snapshot (post-AC21-removal). Coverage is binary-checkable. Where a Brief A AC cannot be cleanly fulfilled, Brief B surfaces a Brief A revision rather than twisting the engine.

**O5 — Engine semantics are unambiguous and storage-neutral.** TZ policy, claim model, observable concurrency guarantees and failure boundaries (atomic transition postconditions, optimistic concurrency tokens, retry semantics — described as operation-level invariants, not file/DB primitives), expiration model, dispatch/clarity-gate placement, wave composition, agent_map, archive atomicity — each specified with one chosen behavior, rejected alternatives, and rationale. No "TBD" past M5.

**O6 — Canonical engine exception taxonomy.** Brief B specifies the engine's exception classes, when each is raised, and the canonical mapping to MCP `ToolError` and Cockpit HTTP status codes. The mapping table makes "MCP is mechanical translator" auditable.

**O7 — Brief B is storage-agnostic.** Engine API expressed in terms of models and operations, not files. No method signature references file paths (except `kanban_dir` at construction). No semantic relies on YAML frontmatter, markdown body parsing, JSONL activity log, or any persistence detail.

  - **Body model:** `body: list[Section]` where `Section = {heading: str | None, content: str}`. Brief A's `show_task(section=...)` becomes a filter on this structured field. Markdown is one possible render at the wire / display layer.
  - **Sessions:** derived from current claim state on tasks (`claimed_at`, `claim_timeout`). No history log in the engine semantic model. Stuck-session = `claimed_at > threshold`. Claim sweep = iterate and clear stale claims. `activity.jsonl` becomes an audit-only artifact outside Brief B's scope (and may be removed by Brief C).
  - **Locking:** described as operation semantics (atomic transition, optimistic concurrency token = `updated`), not file locks.
  - **TZ policy** governs engine runtime behavior (what offset appears in projections), not stored representation.

## Architectural Choice Implications (carry into M3)

- **A2 (structured body)**: requires re-decision on how Brief A's body wire shape and markdown editing in Cockpit interact with `list[Section]`. Brief A may need a small revision to `TaskFull.body` typing.
- **B1 (engine owns waves + agent_map)**: requires `agent_map` config schema (status → agent name + rank). Orchestrator's `waves.py` and `selector.py` retire. Larger code-impact but correct ownership.
- **C2 (role views)**: requires deciding which methods live on which view, and how shared read methods (e.g. `show_task`) are exposed to both. View construction pattern: `engine.agent_view()`, `engine.cockpit_view()`.
- **D2 (no history log)**: drops `activity.jsonl` from engine's semantic model. Activity log becomes pure audit, may disappear in Brief C. Implications for any current consumer of `list_sessions` need M3 audit.
