# Simplifier Stance — Structured Task Specification

## Verdict

The scope is ~3× larger than the stated driver justifies. "Structural cleanliness" needs a model change and MCP exposure — not cockpit UI features, atomic list-manipulation APIs, or a pipeline skill rewrite.

## Cuts

### 1. Drop Cockpit UI rendering (HIGH confidence: 0.90)

The driver is "move spec out of the body into structure." The cockpit already renders task bodies fine. A checklist widget and a "visual weight indicator" are UX features — they assume the structural change exists, but they are not the structural change. Defer to a follow-on feature that can be designed and tested independently.

**Impact:** Removes the entire `serve/cockpit/` surface from this feature. Cuts ~40% of implementation and testing scope.

### 2. Drop `add_ac` / `remove_ac` atomic operations (HIGH confidence: 0.85)

AC are written once at task creation by the planner/architect and read many times. They are not tags — tags are high-frequency, single-value mutations during execution. `edit_task` already accepts full-field replacement for every other list-shaped field. Let `ac` work the same way: pass the complete list, get it back. If atomic ops prove necessary later (evidence: agents frequently append single AC), add them then.

**Impact:** No new API pattern. `edit_task` gains one parameter (`ac`), not three (`ac`, `add_ac`, `remove_ac`).

### 3. Defer pipeline agent skill updates (MEDIUM confidence: 0.75)

The context already commits to forward-only migration: "agents improvise for legacy tasks with body-embedded AC." This same improvisation works fine for new tasks too — agents will see the `ac` field in `show_task` output. Skill updates to reference `ac` instead of parsing body text are housekeeping, not a gating dependency. Ship the infrastructure first; update skills in a follow-on sweep.

**Impact:** Removes the skill-audit and multi-file skill-editing scope. Reduces blast radius to `serve/kanban/` + `serve/mcp-kanban/` only.

## Decomposition Recommendation

Split into two phases:

| Phase | Scope | Blast radius |
|-------|-------|--------------|
| P1: Schema + MCP | Add `ac` (list[str]) and `proof_bundle` (enum) to model, expose in `create_task`/`edit_task`/`show_task` | `serve/kanban/`, `serve/mcp-kanban/` |
| P2: Consumers | Cockpit UI rendering, skill updates, optional migration script | `serve/cockpit/`, `share/skills/`, `.owlbear/kanban/` |

P1 is the structural cleanliness fix. P2 is optional polish that can be prioritized independently.

## What I did NOT cut

- **Bundling `ac` + `proof_bundle` as one feature.** Both are trivial model additions with the same motivation. Splitting them into two tasks would cost more coordination overhead than it saves.
- **`proof_bundle` itself.** It's a single enum field with a known taxonomy. Near-zero design risk.

## Remaining tension

The open design questions (AC naming convention, storage format, `list_tasks` exposure) are real but small. They only matter at the model layer and can be resolved in P1 architecture review without a full panel. Don't let format bikeshedding inflate the feature.

## Confidence

**0.85** — The three cuts are well-grounded in the stated driver. The cockpit cut is the highest-value one; the atomic-ops cut prevents API sprawl; the skill-update deferral shrinks blast radius. Risk: the user may want cockpit rendering as part of the same delivery because they value seeing the result end-to-end. If so, P2 can be bundled back in, but it should still be a separate task with its own AC.
