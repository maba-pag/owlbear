# Decisions

## D1 — Investment Tier
**Shared.** Multi-surface cockpit foundation. Clean engine↔GUI contract, thorough tests, demo-ready polish. Consistent with the prep brief (also Shared) that was explicitly designed as groundwork for this project. Not Production — single laptop user, no SLOs, no external release engineering.

## D2 — Core Framing
**Steering cockpit**, not "kanban viewer." Intervention verbs (move, reprioritise, block/unblock, unclaim, edit body + allowlisted YAML) are headline features. Observability is the substrate; action is the point.

## D3 — Board / Activity Weighting (v1)
**~70 % board, ~30 % activity.** Activity is a proper panel, derived from claim state (`claimed + valid_claim == running`). No process monitoring.

## D4 — Intervention Principle
**Humans may RELEASE stuck work. Only agents may CLAIM or advance work-state.** Clean invariant that explains why unclaim is in and claim/start/end/dispatch are out.

## D5 — Display Principle
Never dump raw file contents. YAML frontmatter rendered as structured controls; markdown body rendered as markdown (with editor mode).

## D6 — Staleness Budget
**2–5 s.** Short-poll the `revision` counter; no SSE/WebSocket in v1.

## D7 — Extensibility as Shell, Not Surfaces
v1 ships the **cockpit shell** (routing, layout, engine adapter, session model, theming). v1 ships **only the kanban surface + activity panel**. Future surfaces (decision queue, knowledge search, memory curation, agent/skill/instruction editor, VS Code settings controller, DnD dispatch) are out of v1, but their shape informs the shell design.

## D8 — Project Name
**cockpit.** Working directory renamed from `draft-new` to `draft-cockpit` after M1.
