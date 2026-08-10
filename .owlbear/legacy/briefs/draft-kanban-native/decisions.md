# Kanban Native — Decisions

## D1: YAML Library → ruamel.yaml
**Choice:** ruamel.yaml with round-trip mode (`typ='rt'`), timestamp resolver disabled.
**Rationale:** Lossless round-trip is a convergence requirement. PyYAML cannot preserve field order, comments, or quoting. ruamel.yaml adds one dependency but guarantees no diff noise on read-write cycles.
**Trade-off accepted:** One extra dependency (~160KB).

## D2: File Locking → None (YAGNI)
**Choice:** No file locking in the initial implementation.
**Rationale:** kanban-md has no locking either. Current consumers (MCP server, orchestrator CLI) don't write simultaneously in practice. Add locking later if contention materializes.
**Trade-off accepted:** Theoretical risk of concurrent write corruption, mitigated by atomic writes (temp + os.replace).

## D3: Compound Operations → In the engine
**Choice:** `start_work()` and `end_work()` are methods on KanbanEngine.
**Rationale:** These compose board primitives (show → claim, edit → advance → archive). Placing them in the engine makes MCP server a thin passthrough and centralizes lifecycle logic for testing.
**Trade-off accepted:** Larger engine surface area.

## D4: Scope → KISS replacement only
**Choice:** No new features. Can drop unused kanban-md features (class, assignee, due, estimate). GUI and feature additions are separate follow-up briefs.
**Rationale:** User directive — minimize risk of not reaching the replacement goal.

## D5: GUI → Deferred
**Choice:** TypeScript GUI is a separate follow-up project.
**Rationale:** Orthogonal to engine replacement. Get the engine right first.

## D6: Engine Placement → Inside mcp-kanban
**Choice:** Engine modules live inside `serve/mcp-kanban/src/owlbear_mcp_kanban/`, not as a separate package.
**Rationale:** Only one consumer (the MCP server). Extract to separate package later if needed. KISS.
**Trade-off accepted:** If orchestrator CLI ever needs direct engine access, the engine would need extraction.

## D7: Orchestrator CLI → Out of scope
**Choice:** `serve/orchestrator/` CLI commands (dispatch/run/status) are not migrated.
**Rationale:** User has never used the orchestrator CLI. If the dispatch loop ever needs board data, it should use MCP tools like agents do.
**Trade-off accepted:** Orchestrator CLI will break when binary is removed. Acceptable since it's unused.
