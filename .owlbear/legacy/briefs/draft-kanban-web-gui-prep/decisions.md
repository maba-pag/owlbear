# Kanban Web GUI Prep — Decisions

<!-- Written after each user decision point -->

## D1 — Investment Tier
**Shared.** Multi-consumer infrastructure, clean interfaces, thorough testing. Consistent with prior kanban-native brief.

## D2 — Concurrent Access
**Accepted risk.** Single-laptop, single-user system. Worst case: user overwrites an agent's quick edit. Optional future mitigation: "modified since read" check. Not in scope for this project.

## D3 — Orchestrator Planner Module
**Dead code — separate cleanup.** The CLI orchestration pipeline (planner, loop, waves, cli dispatch/run) is unused — the project moved from CLI-based dispatch to VS Code agent workflows using MCP directly. The entire `serve/orchestrator/` package is a candidate for cleanup/removal, but that's orchestrator surgery, not kanban engine work. Separate brief.

## D4 — Phase Sequencing
**Fix-then-extract.** Fix config staleness, add TaskSummary, valid_transitions(), and revision counter inside the current mcp-kanban structure first. Then extract the engine package. The engine arrives complete and authoritative, not "authoritative in shape but not in behavior."

## D5 — valid_transitions()
**This project.** Define and expose a transition map so the GUI doesn't hardcode status transitions. Low cost, high value for the data contract.

## D6 — Revision Counter
**This project.** In-memory int counter on the engine instance, incremented on every write. Trivial to include, enables cheap GUI polling when the GUI arrives.

## D7 — Phase 0 (Planner Drop) Handling
**Separate brief.** Audit revealed the planner is wired into a broader CLI/loop/waves pipeline that's all dead together. Removal scope is the orchestrator package, not kanban. This brief covers engine restructuring only (Phases 1–3).
