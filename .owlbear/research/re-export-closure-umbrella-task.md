# Re-export Closure Umbrella Task

> **Owning task:** #865 - Archive stale re-export closure meta-tasks (#823, #837)
> **Date:** 2026-03-20  **Status:** Complete

## 1. Context and Question

Task #865 proposes one cleanup task that would append closure notes to #823 and #837,
archive both, and keep #549 as the source of truth for the re-export decision.
This research checks whether that bundled cleanup is still the right board action.

## 2. Sources Studied

| Source | Type | Relevance | What we used |
|--------|------|-----------|--------------|
| `kanban/tasks/865-archive-stale-re-export-closure-meta-tasks-823-837.md` | Local task file | 1.0 | Confirms #865 is an umbrella cleanup task that asks later agents to edit #823 and #837 |
| `kanban/tasks/823-close-813-as-won-t-do-per-re-export-research.md` | Local task file | 1.0 | Shows #823 already records the closure outcome but remains actionable |
| `kanban/tasks/837-close-815-as-won-t-do-per-re-export-decision.md` | Local task file | 1.0 | Shows #837 was already reframed as a self-closure task |
| `kanban/tasks/549-add-re-exports-to-empty-init-py-files.md` | Local task file | 1.0 | Confirms #549 already records the final re-export state |
| `docs/research/re-export-closure-meta-tasks.md` | Local research doc | .95 | Confirms #865 was created as the cleanup follow-up from #837 research |
| `.github/instructions/agent-common.instructions.md` | Local instructions | 1.0 | Provides the board rule that agents must not modify tasks outside their dispatched assignment |

## 3. Analysis

### 3.1 Current board state

| Item | Current state | Evidence | Implication |
|------|---------------|----------|-------------|
| #549 | Archived | Parent body already records #813 and #815 as archived and resolved | The source-of-truth task already exists |
| #823 | Todo, body says the meta-task is complete | Research Closure note already says `This meta-task is complete` | Remaining gap is status/cleanup, not new analysis |
| #837 | Todo, self-closure AC already written | Architecture review explicitly reframed it as an atomic self-closure task | #837 no longer needs an umbrella task to close #815 |
| #865 | Ideation umbrella cleanup | Body asks one future task to edit #823 and #837 | Scope crosses task boundaries |

### 3.2 Workflow fit

| Constraint | Evidence | Effect on #865 |
|------------|----------|----------------|
| Agents may not modify tasks outside the dispatched assignment | `agent-common.instructions.md`: `Never modify tasks you were not dispatched for` | A builder/reviewer dispatched for #865 cannot legally archive #823 and #837 |
| Self-closure is the approved pattern for stale meta-tasks | #837 architecture review: `Reframing #837 as an atomic self-closure task keeps the work precise and verifiable without modifying other tasks` | The board already has a valid pattern that avoids umbrella cleanup tasks |

### 3.3 Options

| Option | Outcome | Trade-off | Confidence |
|--------|---------|-----------|------------|
| Keep #865 as the execution task | One task on paper | Violates the cross-task edit rule and duplicates #837's self-closure framing | .10 |
| Treat #865 as research-only and let existing tasks close themselves | Aligns with board rules and preserves #549 as the source of truth | Requires architect review to retire or refine #865 | .93 |
| Create another replacement cleanup task | Adds more board indirection | Pure duplication; worsens board clutter | .00 |

## 4. Recommendation (.93 confidence)

Do not execute #865 as written. The board already has the concrete cleanup tasks,
and the shared task-coordination rule forbids a later agent from editing #823 and
task #837 while dispatched only for #865.

Keep #549 as the source of truth. Let #837 remain the self-contained closure task
for its own stale meta-work, and handle #823 the same way within #823 itself rather
than through another umbrella task.

The architect should treat #865 as a redundant umbrella task: either close it as a
duplicate of the existing closure path or rewrite it into a coordination note that
does not require cross-task edits.

## 5. Follow-up Tasks

No new follow-up tasks needed. The concrete board work already exists:

1. #837 already contains atomic self-closure AC.
2. #823 already identifies the remaining stale meta-task and should be resolved in its own task.

Creating another task here would duplicate board work instead of reducing it.
