# Brief — Block-Time Guidance from owlbear-kanban MCP

## Problem
Across OwlBear and consuming projects, agents repeatedly set tasks to `blocked` without creating a Decision Request. Multiple instruction-file and memory updates have failed to change the behavior. The pattern is worst for *action-needed* blocks (e.g., "user must connect VPN") that look mundane but actually require user intervention. Instructions buried on line 87 of the 13th file an agent reads have proven insufficient; we need the rule to live where the action happens.

## Outcomes
1. **In-turn block guidance.** Every `edit_task(block=...)` and `end_work(outcome="block")` returns a structured "ACTION REQUIRED: create a Decision Request for this block" message in the same tool response that commits the block. The message is the first thing the agent sees in the response payload.
2. **User vs. agent block disambiguation.** Cockpit-initiated blocks carry the `block:user` tag. Agents reading a tagged task understand the block is user-driven and skip DR creation.
3. **Reusable guidance mechanism.** The same helper serves three V1 use cases (block, forward-skip, success/commit). Adding a fourth use case is appending one tuple to a registry.

## Approach
**Path A1 — soft, in-your-face, non-breaking.** The mechanism does not raise `ToolError`, does not introduce new MCP primitives, and does not change tool signatures. It adds a single new field (`guidance: list[str]`) to the existing `KanbanTask` Pydantic model and a single new `guidance.py` module to compute the field's contents.

### Architecture (locked decisions D1–D9 in `decisions.md`)

1. **`KanbanTask.guidance: list[str] = []`** — first declared field in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`. Pydantic v2 declaration-order JSON serialization puts it first in every response. Empty list when no guidance applies.
2. **`serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`** — flat rule list. Each rule is `(predicate, message_template)`. One `collect_guidance(operation, before, after, **kwargs) -> list[str]` function. V1 ships three rules.
3. **`server.py` integration** — each affected MCP tool (`edit_task`, `end_work`, `move_task`) calls `collect_guidance(...)` after the engine call, then attaches results to the returned `KanbanTask.guidance`. `move_task` pre-reads via `_show_validated()` to get the prior status for forward-skip detection.
4. **`block:user` tag lifecycle** — Cockpit's existing `edit_task` route (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py`) adds the tag on block, removes it on unblock. MCP `edit_task`/`end_work` block branches remove the tag (an agent re-blocking takes ownership). Cockpit continues to call the engine directly; no MCP routing or new arguments introduced.
5. **No engine-layer changes.** Engine remains pure; guidance lives at the MCP boundary. Cockpit handles its own tag lifecycle. Single source of truth = the engine; single source of *guidance* = the MCP server.

## Scope (in)
- New `guidance.py` module with three V1 rules.
- `guidance` field added to `KanbanTask` model.
- `edit_task`, `end_work`, `move_task` server.py integration.
- Cockpit `block:user` tag application/removal in mutation routes.
- Tests: unit tests for each rule; integration tests for each tool that emits guidance; Cockpit mutation route tests for the tag lifecycle.
- Skill documentation updates: `h-mcp-kanban` (guidance field), `r-pipeline-protocol` (DR-on-block clarified, `block:user` exemption documented), `w-decision-routing` (entry point note).

## Out of scope
- Hard validation (`ToolError` on missing DR). Documented as fallback.
- New MCP primitives (elicitation, prompts, sampling).
- Engine-layer changes.
- Other candidate operations (create_task tag-required, edit_task body-replace warning, end_work reject explanation, etc.). Defer to follow-up Briefs.
- Numeric success metrics or telemetry.
- Any changes to scribe agent or DR file format.

## Risks
- **Critic Blocker 1 (acknowledged):** the guidance arrives *after* the block commits. Mitigation: salience via JSON field order. Watch operationally; if compliance does not improve, swap the helper to raise `ToolError` (single-file change).
- **Tag-bypass risk:** an agent could write `block:user` to a task it itself blocks, dodging DR creation. Acceptable risk; this is a self-attack on the agent's own pipeline, not a security issue.
- **Forward-skip pre-read cost:** one extra task read per `move_task`. Acceptable; `move_task` is not hot.
- **Skill drift:** if `r-pipeline-protocol` changes the DR convention later, the guidance text will go stale. Mitigation: the guidance message references the convention by name, not verbatim, so the agent re-resolves to current docs.

## Acceptance criteria
- `KanbanTask.guidance` field exists, is the first JSON-serialized field, defaults to `[]`, has tests.
- `collect_guidance()` exists in `guidance.py` with three rules; unit-tested for each rule's positive and negative case.
- `edit_task(block=...)` and `end_work(outcome="block")` return `guidance` containing the DR-required message; integration-tested.
- `move_task` returning a status > 1 slot ahead of prior status returns `guidance` with the forward-skip message; integration-tested. Forward moves of 1 slot return empty guidance. Backward moves return empty guidance.
- `end_work(outcome="success")` returns `guidance` with the commit-pushed message; integration-tested.
- Cockpit `edit_task` route adds `block:user` on block, removes it on unblock; tested.
- MCP `edit_task` and `end_work` block branches remove `block:user` if present; tested.
- `h-mcp-kanban`, `r-pipeline-protocol`, `w-decision-routing` skill files updated.
- All existing kanban MCP tests still pass (no regressions).
- Seed propagation verified (changes flow to consuming projects).

## Estimated decomposition (preview for planner)
~6–9 atomic tasks: model field + tests · guidance module + tests · `edit_task` integration · `end_work` integration · `move_task` integration + pre-read · Cockpit tag application/removal + tests · MCP block tag-removal · skill doc updates · seed/integration verification.

## Working Directory
`.owlbear/briefs/draft-blocked-task-dr-enforcement/`
- `context.md` — full M1–M3 reasoning, Critic findings, landscape from Explore
- `decisions.md` — locked decisions D1–D9
- `brief.md` — this file
