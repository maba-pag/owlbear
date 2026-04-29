# Decisions

## D1 — 2026-04-30 — Project Type

**Status quo:** Scribe agent exists, DR/AR system works via `.owlbear/decisions/`.
**Decision to make:** Is this net-new, refactor, or uncertain?

**Chosen:** existing-feature/refactor — the DR/AR system exists and works; the question is whether the agent layer adds value or can be replaced by deterministic code in the existing kanban engine.

## D2 — 2026-04-30 — Investment Tier

**Chosen:** Shared — cross-cutting infra (engine + MCP + Cockpit + all agents) but internal-only.

## D3 — 2026-04-30 — Storage Model

**Decision to make:** Separate decision folder vs. integrated into task files.

**Options considered:**
- A: Separate folder (engine-managed, `.owlbear/decisions/`)
- B: Integrated into task frontmatter + body

**Chosen:** A — separate folder. Multiple DRs per task exist (different concerns). Central inbox for user attention. Clean archival trail. Decoupled from task lifecycle.

**Rejected:** B because multiple DRs per task get awkward; "show all pending" requires scanning all tasks; mixes AC with decision content.

## D4 — 2026-04-30 — File Format

**Chosen:** Stay with markdown + YAML frontmatter. No new format introduced. Simplified fields.

## D5 — 2026-04-30 — Cockpit Scope

**Chosen:** Cockpit DR UI stays in this brief (not deferred). Status bar indicator (must-have) + resolve UI. Creation remains agent-only.

## D6 — 2026-04-30 — pick_tasks Integration

**Decision to make:** Explicit `resolve_drs` tool vs. side-effect in `pick_tasks`.

**Chosen:** Side-effect in `pick_tasks` — user wants no extra tool, no extra call. Backend handles it.

**Rejected:** Separate `resolve_drs` MCP tool — adds unnecessary complexity (another tool call for orchestrator).

## D7 — 2026-04-30 — Fields Dropped

**Chosen:** Drop urgency (tautological), decision_type (unused), impact_tier (only drove auto-resolve), auto-resolve (never triggered, 0 instances in history).

## D8 — 2026-04-30 — Concern Matching / Duplicate Detection

**Chosen:** Drop semantic matching. If needed, task_id-only check internal to `create_dr`. Duplicates are acceptable edge case vs. over-engineering detection.
