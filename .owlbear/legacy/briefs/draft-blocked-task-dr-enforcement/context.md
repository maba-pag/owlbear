# Context — Blocked Task DR Enforcement (and MCP-returned guidance pattern)

## Working Directory
`.owlbear/briefs/draft-blocked-task-dr-enforcement/`

## Problem Statement (M1, in progress)
Across OwlBear and consuming projects, agents repeatedly set tasks to `blocked` without creating a Decision Request, even when one is required. Instructions and memory entries have been added multiple times to fix this — they have not stuck. The pattern is worst for *action-needed* blocks (e.g., "user must connect VPN") rather than *decision-needed* blocks. User's hypothesis: enforce at the MCP boundary — when `block` is set, the MCP server returns text in its response that the calling agent cannot ignore. Open question: should this generalize to other recurring agent compliance failures the MCP could mitigate the same way?

## M1 Decisions (locked)
- **Scope: Option B** — General "MCP returns guidance text on risky operations" pattern.
- **Investment Tier:** Shared (touches owlbear-kanban MCP server, used by all consuming projects; needs tests, SKILL doc updates, seed propagation).
- **Block→DR rule:** Hard requirement, no exemptions, no `block_justification` escape hatch. Rationale: the supposed exemption cases all reduce to other tools — parent/subtask is `add_dep`; superseded is `move_task("archived")` after a DR; external action is a DR with `type:user-action`.
- **Initial mechanism users:** (1) `edit_task(block=...)` and `end_work(outcome="block")` → mandatory DR text; (2) `move_task` forward-skip > 1 slot → "unusual, confirm intent" reminder; (3) `end_work(outcome="success")` → commit-pushed reminder.
- **Diagnostic depth:** Minimal. A separate full agent/skill audit is already running in parallel; M3 landscape will only glance for newly introduced errors.

## Findings — kanban MCP surface
- 8 tools: `list_tasks`, `show_task`, `create_task`, `move_task`, `edit_task`, `start_work`, `end_work`, `pick_tasks`.
- Block can be set via `edit_task(block="reason")` or `end_work(outcome="block", block_reason="...")` — both code paths must emit the DR mandate.
- `end_work` already auto-timestamps notes — no agent-supplied claim timestamp exists or is needed. Old "claim with [[date]]" guidance refers to manual `edit_task(append_body, timestamp=true)` patterns, not the standard lifecycle.

## Investment Tier
**Shared** (locked).

## M2 Outcomes (locked)
1. **Block guidance reaches the agent in-turn.** Every `edit_task(block=...)` and `end_work(outcome="block")` returns a structured "ACTION REQUIRED: create a Decision Request for this block" message in the same tool response that commits the block. The message names the task and points to the scribe convention; it is the first thing the agent sees in the response payload.
2. **User-initiated blocks are distinguishable from agent-initiated blocks.** Cockpit's block path (`serve/cockpit/.../routes/mutation.py`) automatically applies tag `block:user` to any task it blocks. Agents reading a task with this tag understand the block is user-driven and skip DR creation.
3. **Mechanism reusable for the other two operations.** The same guidance-emission helper serves `move_task` forward-skip > 1 slot ("unusual, confirm intent") and `end_work(outcome="success")` ("commit pushed?"). Adding a fourth user is a small, contained change.

## M3 Landscape (from Explore subagent)
- FastMCP v1.26 in use; codebase uses `@mcp.tool`, `@mcp.resource`, `lifespan`, `ToolError`, structured Pydantic outputs, manual `output_schema`/param patches.
- **Not yet used:** `@mcp.prompt`, elicitation, sampling, `ctx.info/warn`, `ctx.report_progress`. (User has rejected adding these — keep mechanism within existing patterns.)
- Closest existing convention for agent-facing soft guidance: the `"error: ..."` string-return idiom in `mcp-memory/tools.py:141-144` and `mcp-knowledge/server.py:340,358`. `mcp-kanban` currently uses only `ToolError` — no agent-facing guidance channel exists.
- Cockpit hole: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:132,134` writes block state directly without going through MCP. Solution chosen: classification (the `block:user` tag), not enforcement.
- Engine layer (`serve/kanban/src/owlbear_kanban/engine.py`) is the shared layer between MCP and Cockpit; it would be the chosen layer if we ever needed hard validation as a fallback.

## Critic findings — addressed
- **Blocker 1 (mutation commits before reminder):** Acknowledged. Mitigated by user's reasoning: in-turn tool-response text is meaningfully more visible than buried instruction text. Will be observed in practice; hard validation remains as a documented fallback in the Brief.
- **Blocker 2 (DR vs AR semantics):** User clarified DR/AR are interchangeable from their perspective — both are files in `.owlbear/decisions/`. Brief uses "DR" generically; agent-facing message will phrase as "Decision Request" but include AR semantics by reference to scribe convention.
- **Blocker 3 (Cockpit hole):** Closed via `block:user` auto-tag.
- **Measurability:** No numeric target. User observes operationally and will return via a follow-up ideation if guidance proves insufficient.
