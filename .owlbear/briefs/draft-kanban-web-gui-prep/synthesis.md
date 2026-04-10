# Kanban Web GUI Prep — Synthesis

## Convergences

### Sibling package extraction with one-way dependency
All four voices endorse splitting `serve/mcp-kanban/` into a transport-free engine package (`owlbear_kanban`) and a thin MCP adapter (`owlbear_mcp_kanban`). Dependency direction: MCP → Engine, never the reverse. The engine is already transport-free in code; the restructuring makes this explicit at the packaging level. *(Architect, Data, End-User, Security)*

### One canonical `Task` model in the engine
Rename `TaskRecord` → `Task`. The engine owns the single source-of-truth model with `extra='allow'` for round-trip YAML fidelity. MCP's `KanbanTask` becomes a boundary projection in the adapter. The hand-built lean dicts in `list_tasks` are eliminated. *(Architect, Data, End-User)*

### `TaskSummary` as a schema-validated projection
Replace the fragile hand-built `_strip` dict with an explicit Pydantic model (`TaskSummary`) for list views. Fields: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on. No body, no timestamps, no file path. *(Architect, Data, End-User)*

### No `file` field on the canonical model
`KanbanTask.file` is always `None` today. The canonical engine model should not carry it. If the MCP adapter needs file paths, it enriches at the boundary. *(Architect, Data)*

### String timestamps preserved; `extra='allow'` retained
String storage prevents lossy truncation of mixed Go/Python timestamp formats. `extra='allow'` preserves round-trip fidelity for unknown/vendor YAML keys. Both are correct trade-offs for this system. *(Architect, Data)*

### Activity log needs consumer identity (`actor` field)
Every `log_activity()` entry must identify which consumer initiated the action. Currently only claim/release actions include identity. Multi-consumer traceability requires this on all operations. *(Architect, Data, Security)*

### Agent-only methods documented, not hidden
`claim_task()`, `start_work()`, `release_task()`, `end_work()`, and `pick_dispatchable()` are agent-oriented. They remain on the engine's public API but are clearly documented as agent-specific. The GUI adapter must not expose them. Enforcement via adapter pattern, not runtime authorization. *(Architect, End-User, Security)*

### `board_config()` with defensive copy
The engine exposes board metadata (valid statuses, priorities, display order) so consumers don't hardcode values or parse config files. Returns a `model_copy()` to prevent mutation of engine internal state. *(Architect, End-User, Data — with Data flagging the staleness caveat)*

### `refresh_config()` for explicit reload
Complements `board_config()`. Consumers call it when they suspect config has changed. Coupled with existing reload-on-write in `create_task`. *(Architect, Data)*

### Drop orchestrator planner module (D3)
The `serve/orchestrator/planner/` module is dead code. All voices accept D3. The Architect warns this is a surgery, not a deletion — the planner is deeply wired into the orchestrator. *(Architect, Security, End-User, Data — implicit acceptance)*

### Schema monkey-patching accepted and isolated
Private FastMCP API access for `outputSchema` is an MCP adapter concern. It's fragile but scoped, tested, and without a better alternative until upstream support arrives. *(Architect, Security — no objections from others)*

### Phased migration with strict ordering
0 (drop planner) → 1 (extract engine) → 2 (extract dispatch) → 3 (engine improvements). Each phase independently shippable and testable. *(Architect — endorsed by others through alignment with Phase 3 features)*

### Config staleness is a pre-existing bug
`create_task` reloads config for `next_id` but doesn't update the cached `self._config`. Other methods use stale cache. This is not introduced by the restructuring but must be addressed (Phase 3). *(Architect, Data)*

### Timestamp sort ordering is broken for mixed TZ offsets
Lexicographic string comparison of timestamps with different timezone offsets produces wrong ordering. Must parse to `datetime` for sort key computation. Separate bug fix. *(Data — Architect acknowledges as deferred)*

## Disagreements

### `valid_transitions()` method — End-User vs. Architect
- **End-User** argues the GUI needs to know which "Move to" options are meaningful from a given state, and exposing `valid_transitions(status) → list[str]` prevents the GUI from hardcoding rules or showing all 42 combinations.
- **Architect** defers this to the GUI project brief, noting the engine currently allows arbitrary transitions by design and this is a new feature requiring a transition map — not a restructuring concern.

### In-memory revision counter — End-User vs. Architect
- **End-User** proposes a simple `int` counter on the engine instance, incremented on every write, so the GUI can poll cheaply without fetching the full task list every 15 seconds.
- **Architect** defers as premature: adds mutable state for a polling optimization only one future consumer needs. With only MCP as a consumer post-restructure, the counter has no consumer.

### `get_board()` convenience method — End-User vs. Architect
- **End-User** argues a board *is* columns, and grouping-by-status is a domain operation worth encoding in the engine, saving every adapter from reimplementing it.
- **Architect** considers it a 5-line dict comprehension, not a domain operation, and treats it as an adapter concern.

### Consumer identity mechanism — Security vs. Architect
- **Security** recommends a `consumer` (or `source`) parameter on `KanbanEngine.__init__` — distinct from `agent_name` — to bind the engine instance to a single consumer identity for audit purposes.
- **Architect** considers the existing `agent_name` constructor parameter sufficient for consumer identity, with no new parameter needed.

## Recommendation

**Proceed with sibling package extraction as the Architect describes, using the four-phase plan.**

The core architecture is uncontested: transport-free engine package, thin MCP adapter, one-way dependency, canonical `Task` model, `TaskSummary` projection, extracted dispatch policy. All four voices converge on these fundamentals.

**Phase 0** deserves its own brief or at minimum a thorough planning pass before execution. Every voice accepts D3 (drop planner), but the Architect's warning about deep orchestrator wiring is substantive. Begin with an audit of which runtime paths actually invoke the planner.

**Phase 3 scope** is where the disagreements cluster. The four deferred items (valid_transitions, revision counter, get_board, consumer identity naming) are all reasonable ideas that diverge on timing, not direction. None blocks the restructuring. They can be evaluated individually during Phase 3 planning or deferred to the GUI project brief.

**Confidence: 0.88** — All voices agree on the structural architecture, dependency direction, model design, and phased approach. Disagreements are limited to Phase 3 convenience features and naming — none affects the restructuring's viability or direction.

## Open Questions

1. **Should `valid_transitions()` be added in Phase 3 or deferred to the GUI brief?** The End-User argues it prevents GUI hardcoding; the Architect argues it's a new feature requiring a transition map, not a restructuring concern. *(End-User vs. Architect)*

2. **Should the engine carry a revision counter from Phase 3, or defer to the GUI project?** The End-User argues cheap polling is essential for GUI responsiveness; the Architect argues it's premature with zero GUI consumers. *(End-User vs. Architect)*

3. **Should `get_board()` live in the engine or be left to adapters?** The End-User sees it as a domain operation; the Architect sees it as trivial adapter logic. *(End-User vs. Architect)*

4. **Should consumer identity use the existing `agent_name` parameter or a separate `consumer`/`source` parameter?** Security wants explicit consumer identity distinct from agent naming; Architect considers `agent_name` sufficient. This affects the activity log `actor` field semantics. *(Security vs. Architect)*

5. **How extensive is the Phase 0 orchestrator surgery?** D3 declares the planner dead, but the Architect warns of deep wiring into CLI subcommands, dispatch loop, wave routing, and retry_hint semantics. The scope of removal must be audited before committing to a timeline. *(Architect — uncontested warning)*
