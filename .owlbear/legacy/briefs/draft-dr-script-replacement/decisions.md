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

## D9 — 2026-04-30 — Response Validation

**Options considered:**
- A: Closed enum — unknown response values → leave pending, log warning
- B: Open freeform — accept any string, classify best-effort

**Chosen:** A — closed enum. Unknown values stay unresolved. Prevents silent mis-resolution from typos or junk in file-edit fallback. Cockpit UI constrains input anyway.

## D10 — 2026-04-30 — Concurrency Guard

**Options considered:**
- A: Three-state lifecycle (`pending/` → `processing/` → `resolved/`) with rename-as-lock
- B: Skip `processing/`, accept theoretical gap, add resilience test
- C: Skip `processing/`, accept theoretical gap, no extra test

**Chosen:** C — concurrent resolves are not a real risk. Single-user, single-pipeline. Not worth any mitigation code or tests.

## D11 — 2026-04-30 — Polling Interval

**Chosen:** Leave to implementation. 60s is fine. DRs are out-of-band and asynchronous — measured in hours, not seconds.

## D12 — 2026-04-30 — Stale-State Draft Protection

**Chosen:** None. No live editing or auto-save exists. User saves manually. If a DR gets resolved during edit, that's an acceptable edge case — no mitigation needed.

## D13 — 2026-04-30 — `create_dr` Response Shape

**Chosen:** Engine blocks task internally as side-effect. Response does NOT include `task_blocked` field. Returns `{created: true, path: "..."}` only.

**Rationale:** Agents should still use `end_work` for their own flow. If agent overwrites block reason, that's desirable — agent has better context than a generic "blocked because of DR" message.
