# Simplifier Stance

## Core Value Identified

Eliminate LLM intermediary (scribe) from deterministic file operations. Everything else is gravy.

## Cuts

### CUT 1 — Cockpit UI (Outcome 6) is a separate brief

Cockpit DR view + resolve UI + badge indicator is a **UI feature** being smuggled into a **backend refactor**. It has its own design decisions (badge colors, layout, interaction patterns), its own frontend work (React components, API routes), and its own test surface. The core value — eliminating scribe latency and cost — is fully delivered without any Cockpit changes.

Users currently edit files. They will continue to be able to edit files. Cockpit UI is a UX improvement that should ship as P2 after the engine work proves stable.

**Defer entirely.** Separate brief.

### CUT 2 — `query_drs` MCP tool is premature

Who calls `query_drs`? Not building agents — they see "task is blocked" via the existing kanban engine and move on. Not the orchestrator — it calls `resolve_drs`. The only consumer is the Cockpit UI, which reads via REST, not MCP.

**Drop from MCP surface.** If a real consumer emerges, add it then. Ship with `create_dr` + `resolve_drs` only.

### CUT 3 — `pick_tasks` auto-resolve (Outcome 5) is implicit coupling

Folding DR resolution into `pick_tasks` creates invisible side-effects in a function whose job is task selection. The orchestrator can call `resolve_drs` explicitly at the top of its cycle — one extra line, zero magic, debuggable.

**Replace with explicit orchestrator call.** Don't modify `pick_tasks` semantics.

## Decomposition

| Phase | Outcomes | Deliverable |
|-------|----------|-------------|
| P1 | 1, 2 (minus query_drs), 3, 4, 7, 8 | Engine functions + 2 MCP tools + skill + reference cleanup + scribe deletion |
| P2 | 6 | Cockpit DR UI (separate brief, depends on P1 stability) |

Outcome 5 transforms into: "orchestrator skill calls `resolve_drs` at cycle start" — this is part of outcome 7 (reference updates), not a separate outcome.

## Remaining Scope Pressure

Even P1 has breadth: engine functions, MCP tools, format migration, new skill, reference updates across all pipeline agents. Consider whether format migration (outcome 3) can be zero-migration (new code reads both old and new format, only writes new). That eliminates a migration task and lets existing DR files age out naturally.

## Confidence

**0.85** — The Cockpit cut is unambiguous. The `query_drs` cut depends on confirming no agent actually polls for DR status outside the blocking mechanism. The `pick_tasks` coupling concern is a judgment call but the explicit-call alternative is strictly simpler.

## Summary

8 outcomes → 6 in P1, 1 deferred to P2, 1 absorbed into existing outcome. MCP surface drops from 3 tools to 2. Cockpit work gets its own brief. Net complexity reduction: ~30% less scope in this brief, cleaner boundaries.
