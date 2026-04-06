# Clean Up Dispatcher References After pick_tasks Migration

> **Owning task:** #629 — Clean up dispatcher references after pick_tasks migration
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

After #622 wires `pick_tasks` into the orchestrator and #623 deprecates the dispatcher agent file, cross-cutting references to the dispatcher remain in 5 docs files. #629 cleans them up.

**Key questions:** (1) Is the current AC complete? (2) What should each reference be replaced with? (3) Does AC item 6 (dispatcher.agent.md) overlap with #623?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `share/instructions/agent-common.instructions.md` L14 | .95 | Dispatcher row in Per-Agent Section Mapping table |
| S2 | `share/skills/r-pipeline-protocol/SKILL.md` L97, L186 | .95 | Two dispatcher prose references |
| S3 | `share/agents/README.md` L1-10 | .95 | Dispatcher in T1 tier row; agent count says 14, actual is 16 |
| S4 | `share/skills/h-agent-structure/SKILL.md` L38 | .95 | Dispatcher in T1 tier row |
| S5 | `share/agents/dispatcher.agent.md` L1-30 | .90 | Current: not yet deprecated (#623 at todo) |
| S6 | `share/skills/w-task-decomposition/SKILL.md` L19 | .90 | "dispatcher-dispatched" — gap noted in #623 research |
| S7 | `.owlbear/research/deprecate-dispatcher-agent.md` | .85 | #623 research: 38-ref inventory, scope boundaries |
| S8 | #623 task body (architect review) | .85 | Conflict note: #629 should narrow dispatcher.agent.md item to verification |
| S9 | #622 AC (task body) | .80 | Scope boundary: orchestrator.agent.md and w-orchestration handled by #622 |

## 3. Analysis

### 3.1 AC Completeness

| AC Item | File | Line | Current Text | Status |
|---------|------|:----:|-------------|--------|
| 1 | agent-common.instructions.md | 14 | `\| dispatcher \| (JSON plan) \| (none) \|` | Valid — remove row |
| 2 | r-pipeline-protocol/SKILL.md | 97 | "the dispatcher will dispatch the planner" | Valid — update |
| 3 | r-pipeline-protocol/SKILL.md | 186 | "blocked for triage by dispatcher" | Valid — update |
| 4 | agents/README.md | 7 | `orchestrator, dispatcher` in T1 tier | Valid — remove dispatcher |
| 5 | h-agent-structure/SKILL.md | 38 | `orchestrator, dispatcher` in T1 tier | Valid — remove dispatcher |
| 6 | dispatcher.agent.md | — | "add deprecated header OR delete" | **Overlap** — #623 handles deprecation |
| 7 (GAP) | w-task-decomposition/SKILL.md | 19 | "dispatcher-dispatched" | Missing from AC |

### 3.2 AC Refinements Needed

| Item | Issue | Recommendation |
|------|-------|---------------|
| 6 | Overlaps #623 which deprecates the file (at todo, depends on #622) | Narrow to **verify #623 applied deprecation** — if #629 runs after #623. If #629 runs first, skip this item. |
| 7 | Gap: "dispatcher-dispatched" not in any task AC | Add: `w-task-decomposition/SKILL.md` L19 — replace "dispatcher-dispatched" with "orchestrator-dispatched" |
| 4 (minor) | README says "14 agent definitions" but 16 exist on disk | Builder should update count while editing the file |

### 3.3 Replacement Text Matrix

| AC | Current | Replacement | Rationale |
|----|---------|-------------|-----------|
| 1 | Dispatcher row in table | DELETE ROW | Dispatcher no longer participates in Channel B |
| 2 | "the dispatcher will dispatch the planner" | "the orchestrator will route the task to the planner" | Orchestrator now does DECOMP detection via show_task post-filter |
| 3 | "blocked for triage by dispatcher" | "blocked for triage by orchestrator" | Stale detection moved to orchestrator's last_dispatched tracking |
| 4 | `orchestrator, dispatcher` | `orchestrator` | Dispatcher deprecated; not a tier-1 active agent |
| 5 | `orchestrator, dispatcher` | `orchestrator` | Same as item 4 |
| 7 | "dispatcher-dispatched" | "orchestrator-dispatched" | Planner is now dispatched by orchestrator, not dispatcher |

### 3.4 Dependency & Ordering

#629 depends on #622 (wiring pick_tasks). #623 also depends on #622 and handles dispatcher.agent.md deprecation. The expected execution order is: #622 → #623 → #629. This means by the time #629 runs, the dispatcher file should already be deprecated by #623. AC item 6 becomes a verification step.

If #629 executes before #623 completes (unlikely given dep chain), item 6 should be skipped — not duplicated.

## 4. Recommendation (.92 confidence)

Proceed with #629 as a straightforward docs cleanup task. Two AC refinements needed before building:

1. **Narrow AC item 6** to verification of #623's deprecation (not a duplicate edit)
2. **Add AC item 7**: `w-task-decomposition/SKILL.md` L19 — "dispatcher-dispatched" → "orchestrator-dispatched"
3. **Minor**: Update agent count in README.md (14 → 16) while editing

Challenge: SKIP — T1 autonomous docs cleanup within approved migration plan (#619). No new capability, no architecture change, no security implications. All replacement text is mechanical substitution.

Tier: **T1 (Autonomous)** — reference cleanup, no decisions required.

## 5. Follow-up Tasks

No new tasks needed. The AC refinements (items 6, 7) belong to #629 itself and should be applied by the architect during review.
