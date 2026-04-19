---
id: 973
title: Block-Time Guidance from owlbear-kanban MCP
status: todo
priority: needed
created: 2026-04-18T21:13:44.384255+00:00
updated: 2026-04-18T21:38:19.238321+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
- scope:cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief approved via ideator on 2026-04-18. Full Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decisions: `decisions.md`. Context (M1-M3, Critic, landscape): `context.md`.

## Problem
Across OwlBear and consuming projects, agents repeatedly set tasks to `blocked` without creating a Decision Request. Multiple instruction-file and memory updates have failed to change the behavior. Pattern is worst for action-needed blocks (e.g., "user must connect VPN"). Instructions buried in instruction files have proven insufficient; the rule needs to live where the action happens (the MCP tool response).

## Outcomes
1. In-turn block guidance: every `edit_task(block=...)` and `end_work(outcome="block")` returns a structured "ACTION REQUIRED: create a Decision Request" message in the same tool response that commits the block. The message is the first thing the agent sees in the response payload.
2. User vs. agent block disambiguation: Cockpit-initiated blocks carry the `block:user` tag. Agents reading a tagged task skip DR creation.
3. Reusable guidance mechanism: same helper serves three V1 use cases (block, forward-skip, success/commit). Adding a fourth use case is appending one tuple to a registry.

## Approach (Path A1 — soft, in-your-face, non-breaking)
- Add `guidance: list[str] = []` as first declared field on `KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`. Pydantic v2 declaration-order JSON serialization places it first.
- New module `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` with flat rule list and one `collect_guidance(operation, before, after, **kwargs) -> list[str]` function. V1 ships three rules.
- `server.py`: each affected tool (`edit_task`, `end_work`, `move_task`) calls `collect_guidance(...)` after engine call and attaches result. `move_task` pre-reads via `_show_validated()` for prior status.
- Cockpit `edit_task` route adds `block:user` on block, removes on unblock. MCP block branches remove the tag (agent re-blocking takes ownership).
- No engine changes. No new MCP arguments. No new tools. No new MCP primitives.

## Acceptance criteria
- `KanbanTask.guidance` field exists, first JSON-serialized field, defaults to `[]`, tested.
- `collect_guidance()` with three rules; positive/negative unit tests per rule.
- `edit_task(block=...)` and `end_work(outcome="block")` return guidance with DR-required message; integration-tested.
- `move_task` forward-skip > 1 slot returns guidance; 1-slot and backward moves return empty guidance.
- `end_work(outcome="success")` returns guidance with commit-pushed message.
- Cockpit `edit_task` route adds `block:user` on block, removes on unblock; tested.
- MCP `edit_task` and `end_work` block branches remove `block:user` if present; tested.
- Skill docs updated: `h-mcp-kanban`, `r-pipeline-protocol`, `w-decision-routing`.
- All existing kanban MCP tests still pass.
- Seed propagation verified.

## Out of scope
- Hard validation (`ToolError` on missing DR) — documented as fallback.
- New MCP primitives (elicitation, prompts, sampling).
- Engine-layer changes.
- Other candidate operations (create_task tag-required, etc.) — defer to follow-up Briefs.
- Numeric success metrics.
- Scribe agent or DR file format changes.

## Risks
- Guidance arrives after block commits (Critic Blocker 1, acknowledged) — mitigated by salience via JSON field order; hard-validation fallback documented.
- Tag bypass — acceptable self-attack risk.
- `move_task` pre-read cost — acceptable, not hot.
- Skill drift — guidance references convention by name, not verbatim.

## Estimated decomposition
~6-9 atomic tasks. Planner subagent will decompose.
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/block-time-guidance-mcp-973.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with Brief Path A1 and locked decisions D1–D9 (confidence: .88)
- Challenge: SKIPPED — approach locked via 3-round architect debate
- Follow-up tasks created: #986 (model field), #987 (guidance module), #985 (edit_task integration), #989 (end_work integration), #991 (move_task integration), #990 (cockpit block:user), #988 (skill docs)
- Decision requests: none — T1 autonomous (all decisions locked in Brief)
- Dependency graph: #986 → #987 → {#985, #989, #991} (parallel) → #988; #990 independent
[[2026-04-18]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent is umbrella; each of 7 subtasks has one responsibility |
| Interface clarity | PASS | `collect_guidance(operation, before, after, **kwargs) -> list[str]` — clear I/O |
| Dependency correctness | PASS (with note) | Dependency graph documented in body but `depends_on` fields empty on subtasks — must be wired during individual subtask architect reviews per graph: #986 then #987 then {#985, #989, #991} then #988; #990 independent |
| Module layering | PASS | New `guidance.py` in mcp-kanban layer, no upward imports; cockpit tag injection in route layer |
| TDD compliance | PASS | Each subtask specifies test files; subtasks flow through test-writer |
| KISS/YAGNI | PASS | Flat `(predicate, message_template)` rule list, no classes, no decorators, 3 rules for V1 |
| Premise challenge | PASS | Real problem (agents skip DR creation); no existing capability addresses this; instruction-file approach proven insufficient |
| Pattern consistency | PASS | Pydantic v2 models, `_record_to_task` conversion, `_show_validated` patterns all respected |
| Security surface | PASS | No new system boundaries; tags and guidance are internal to the pipeline |
| Single domain | PASS | MCP kanban domain primary; cockpit tag injection is ancillary (already split as #990) |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `collect_guidance()` raises | Guidance lost, operation already committed | RuntimeError | No (must be caught in server.py) | Operation succeeds, no guidance shown |
| `_show_validated` pre-read fails (move_task) | move_task fails before engine call | ToolError | Yes (existing pattern) | Clean error, no state change |
| Tag removal fails (block:user) | Stale tag persists | ValueError | Tolerable | Agent may skip DR creation unnecessarily |
| TOCTOU on move_task pre-read | Guidance reports stale status delta | N/A | By design (advisory) | Possible spurious forward-skip warning |

### Challenge Results
- Challenger: `reconsider` (confidence 0.72)
- Four challenges raised: C1 (end_work tag removal non-atomic), C2 (cockpit tag-diff edge case), C3 (in-place re-block tracing), C4 (move_task TOCTOU)
- Architect response: REBUTTED all four

**C1 rebuttal:** `engine.edit_task()` does not require a claim. After `engine.end_work()` releases the claim, `engine.edit_task(task_id, remove_tags=["block:user"])` is a valid sequential call in the same handler. Non-atomicity is acceptable: `block:user` is advisory. Worst case = stale tag = agent skips DR creation, same risk class as tag bypass (already accepted in Brief). No engine change needed.

**C2 rebuttal:** Edge case requires a Cockpit user to explicitly include/exclude `block:user` in their tag set while simultaneously blocking. `block:user` is a system-managed tag; frontend should not expose it for manual editing. Subtask #990 architect should add AC: "Cockpit frontend filters `block:user` from user-editable tag list, or route handler strips it from set-diff before injection." Acceptable V1 edge case.

**C3 rebuttal:** MCP `edit_task` block branch can issue `engine.edit_task(task_id, blocked=True, block_reason=block, remove_tags=["block:user"])` as a single atomic engine call. Traced and confirmed: engine processes all kwargs in one read-mutate-write cycle.

**C4 rebuttal:** Acknowledged, acceptable for advisory guidance. Brief R1.4 explicitly accepts this.

### Implementation Guidance for Subtask Architects

1. **Dependency wiring required.** All subtasks have `depends_on: []`. Wire per documented graph: #986 (no deps) then #987 (depends #986) then {#985, #989, #991} (each depends #986, #987) then #988 (depends #985, #989, #991). #990 has no deps.

2. **#989 (end_work integration):** `end_work` tag removal uses two sequential engine calls: `engine.end_work()` then `engine.edit_task(task_id, remove_tags=["block:user"])` then re-read. AC is achievable without engine changes.

3. **#985 (edit_task integration):** Block branch combines blocking + tag removal in single `engine.edit_task` call (atomic). Straightforward.

4. **#990 (cockpit block:user):** Note C2 edge case — if frontend allows manual `block:user` in tag sets, add handling or filtering. Consider AC line: "route handler strips `block:user` from set-diff computed tags before injection."

5. **#987 (guidance module):** Wrap `collect_guidance` callers in try/except to prevent guidance failures from breaking tool operations. Add defensive AC line.

6. **Parent task is an umbrella.** All implementation is in subtasks #985-#991. #973 tracks aggregate completion.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Subtask dependency wiring and implementation notes documented for downstream architects.