---
response: approved
decision: "A: Ratify the live 5-outcome contract"
notes: ""
task_id: 1124
agent: researcher
created: 2026-04-25
urgency: blocking
decision_type: approach-selection
impact_tier: 2
---

# Decision: Ratify live end_work outcome contract vs. Brief B D52

## Context

Brief B D52 explicitly dropped `fail` from AgentView.end_work valid outcomes as a deliberate design choice (citing "orphan-claim foot-gun" risk). Research task #1124 initially recommended restoring `fail` as a T1 bug fix, but this was flagged by architecture review as an authority conflict—Brief B D52 is the authoritative design source.

Re-research reveals a critical observability distinction: the live codebase uses a **5-outcome contract** across 9 of 11 system layers (`activity`, `session`, `cockpit`, engine storage, engine validation, pipeline protocol, orchestrator dispatch, agent lifecycle, MCP server), but only `AgentView` and `EndWorkParams` reject the `fail` outcome. The Brief B D52 rationale (foot-gun risk) does not account for the activity/session/cockpit observability requirement for `fail`—which is specifically used for 3 documented failure modes: TOOL_UNAVAILABLE, prerequisite handoff, and agent handoff.

**Key distinction:** `release` does NOT append timestamped notes (routes through `release_task`), while `fail` DOES append notes (raw `engine.end_work`). Pipeline protocol mandates note appending for the 3 `fail` use cases.

Two paths forward:

### A: Ratify the live 5-outcome contract — (rec:) recommended
**Confidence: 0.82**

Restore `fail` to AgentView and EndWorkParams valid_outcomes. Override D52 based on system-wide observability evidence. This is the minimal change; the system already relies on `fail` in 9 of 11 layers.

- **Effort:** Low. Add `fail` back to enums, update 2 validation lists.
- **Authority risk:** Overrides D52 intentional design. User must explicitly approve the override.
- **Migration cost:** None—the 9 layers are already working with `fail`.
- **Testing impact:** Add 3 use-case tests for `fail` in AgentView; update end-to-end pipeline tests.

### B: Fix `release` to match D52 intent + migrate agents to use `release`
**Confidence: 0.45**

Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set." Current code routes `release` through `release_task()` which does NOT append notes—a bug. Fix that bug, update pipeline protocol to use `release` instead of `fail`, and update all agents.

- **Effort:** Medium. Implement `release` note appending, update pipeline protocol, audit and fix all agent call sites (9 layers).
- **Authority alignment:** Honors D52 decision intentionally.
- **Migration cost:** High—all 9 layers must be updated in lockstep.
- **Testing impact:** Full pipeline regression suite + new `release` note semantics tests + agent behavior updates.
- **Risk:** Higher chance of deployment issues due to coordinated changes across multiple layers.

### C: Defer — maintain current state (no validation in AgentView/EndWorkParams)
**Confidence: 0.0 (not viable)**

Current state is inconsistent (9 layers expect `fail`, 2 reject it). Pipeline is already broken for `fail` use cases in AgentView context. Deferral leaves those use cases unresolved.

## Recommendation

**Option A: Ratify the live 5-outcome contract (confidence 0.82).**

The system evidence is overwhelming—9 of 11 layers already validate and use `fail`. D52's foot-gun concern is valid design thinking, but it was drafted without accounting for the observability distinction between `fail` (appends notes, logs events) and `release` (state-only). The override is justified by empirical system architecture.

## Impact of Deferral

Task #1124 remains blocked. Follow-up implementation tasks #1125 and #1126 cannot proceed. AgentView.end_work will continue rejecting `fail`, silently breaking the 3 documented failure-mode handlers that depend on it.
