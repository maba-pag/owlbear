# Context — Dep-Status Guidance in start_work

## Problem

`agent_view.start_work()` does not surface dependency-status information to agents. When an agent claims a task — whether via manual assignment (bypassing `pick_tasks`) or after a stale pick window (10-30 min between pick and start) — it proceeds with no awareness that dependencies are unresolved. The desired behavior is directive guidance in the `start_work` response telling the agent to **confirm with the user** before proceeding on dep-blocked or dep-redirected tasks.

## Trigger Scenarios

1. **Manual assignment** (primary): User tells an agent to work on a specific task ID directly, outside the normal kanban workflow, to speed things up.
2. **Stale pick window** (secondary): Normal pick→start flow, but deps change during the 10-30 min execution window between waves.

## Project Type

existing-feature/refactor

## Scope Signal

- `start_work` already validates archived/blocked status
- `_compute_dep_status()` already exists in the engine
- `SingleTaskResponse` already supports a `guidance` list
- Change is additive (~10-15 LoC in agent_view.py)
- No agent instruction changes — directive guidance at point-of-action is sufficient
- No MCP tool surface changes expected

## Outcomes (locked M2)

**Best realistic outcome:** When `start_work` claims a task whose `dep_status` is "blocked" or "redirect", the `SingleTaskResponse.guidance` list includes a directive message listing each unresolved dependency (with its current state) and asking the agent to review and confirm intent before proceeding. Tasks with resolved or no deps produce no guidance (same as today).

**Minimum viable win:** Guidance surfaces for `dep_status == "blocked"` at minimum (the most dangerous case). Listing individual dep details is included if implementation stays low-effort.

**Scope boundaries:**
- Soft gate only — task remains claimable (no hard block).
- Uses existing `guidance` field — no schema changes.
- Uses existing `_compute_dep_status()` — no new engine primitives.
- No agent instruction changes — directive guidance at point-of-action suffices.
- No MCP surface changes.
- No changes to `pick_tasks` (already filters dep-blocked tasks).

## Active Tensions

- First-principles challenged whether soft guidance is honest intervention or hope-driven design. Resolved: hard blocks create perverse incentives (user edits tasks to remove deps). Soft guardrails preserve human autonomy while surfacing risk.
- Simplifier cut scope to ~5 LoC: reuse existing `show_task` call (which already computes `dep_status`), flat message with dep IDs only, "blocked" only (drop "redirect").
