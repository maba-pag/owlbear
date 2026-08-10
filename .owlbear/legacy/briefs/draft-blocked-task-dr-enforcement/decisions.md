# Decisions — Blocked Task DR Enforcement

## D1 — Path A1 (soft guidance, no hard gate)
MCP tool responses for risky operations include structured guidance text. No new MCP primitives (no elicitation, prompts, sampling). No hard validation, no `ToolError` on missing DR. Rationale: in-turn tool-response text is meaningfully more visible than buried instruction text; hard validation remains as a documented fallback if observed compliance is poor.

## D2 — Initial three users
- `edit_task(block=...)` and `end_work(outcome="block")` → "Create a Decision Request for this block" guidance.
- `move_task` to a status > 1 slot forward → "Forward-skip is unusual; confirm intent" guidance.
- `end_work(outcome="success")` → "Commit pushed?" guidance.

## D3 — Cockpit `block:user` auto-tag
- Cockpit's `edit_task` mutation route applies `block:user` whenever it transitions a task to blocked.
- Cockpit's unblock path removes the tag.
- MCP `edit_task` and `end_work` block paths remove `block:user` (an agent re-blocking takes ownership; tag would be stale).
- Agents reading a task tagged `block:user` do not create a DR — block is user-driven.

## D4 — `guidance` field on `KanbanTask`
- Add `guidance: list[str] = []` as the **first declared field** on `KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`.
- Pydantic v2 declaration-order serialization places it first in the JSON response — maximum salience to the LLM consumer.
- Existing `outputSchema` patch in `server.py:349-353` auto-propagates the schema update.
- Empty list when no guidance applies; existing consumers ignore it (Pydantic `extra="ignore"` semantics).

## D5 — `guidance.py` module
- New file: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`.
- Flat list of rules: each rule is a `(predicate, message_template)` pair.
- Single `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **op_kwargs) -> list[str]` function.
- V1: three rules. Adding a fourth rule = appending one tuple to the list.
- No classes, no decorators, no plugin discovery — KISS.

## D6 — Forward-skip detection
- MCP `move_task` pre-reads current task via existing `_show_validated()` helper before delegating to engine.
- Status ordering pulled from `engine.board_config().statuses` (must be exposed publicly if not already).
- Archived status excluded from skip detection.
- Cost: one extra read per `move_task` call. Acceptable given Shared tier.

## D7 — DR semantics
- "Decision Request" used generically in the codebase and guidance text.
- Covers both classical decisions and action requests; both are files in `.owlbear/decisions/`.
- Scribe agent's existing convention determines the file content shape.

## D8 — No numeric success metric
- User observes in practice. If guidance proves insufficient, a follow-up ideation references this Brief.
- Hard-validation fallback documented in Brief Risks section; implementation is one-helper change should it be needed.

## D9 — Skill / doc updates required
- `share/skills/h-mcp-kanban/SKILL.md` — document the `guidance` field in the tool schema section.
- `share/skills/r-pipeline-protocol/SKILL.md` — clarify DR-required-on-block + `block:user` exemption.
- `share/skills/w-decision-routing/SKILL.md` — note that block guidance points here.
