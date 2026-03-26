# Stale Re-export Closure Meta-tasks

> **Owning task:** #837 - Close #815 as won't-do per re-export decision
> **Date:** 2026-03-20  **Status:** Complete

## 1. Context and Question

Task #837 asks to archive #815 after Option A in `docs/decisions/resolved/813-re-export-feature-gate.md`.
This research checks whether that closure work is still needed and, if not, what the correct board action is.

## 2. Sources Studied

| Source | URL | Relevance | What we used |
|--------|-----|-----------|--------------|
| `kanban/tasks/815-add-re-exports-to-tools-browser-init-py.md` | Local task file | 1.0 | Confirms #815 is already archived with won't-do audit evidence |
| `kanban/tasks/549-add-re-exports-to-empty-__init__.py-files.md` | Local task file | 1.0 | Confirms the umbrella task already records #815 as archived |
| `kanban/tasks/823-close-813-as-won-t-do-per-re-export-research.md` | Local task file | 1.0 | Shows a sibling closure meta-task with the same stale-state pattern |
| `docs/decisions/resolved/813-re-export-feature-gate.md` | Local decision file | 1.0 | Confirms Option A was approved: do not add re-exports |
| GitHub Docs - Closing an issue | <https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/closing-an-issue> | .75 | Issues should be closed when work is resolved or not planned |
| GitLab Docs - Manage issues | <https://docs.gitlab.com/user/project/issues/managing_issues/#close-an-issue> | .80 | Issues no longer needed should be closed; duplicate closure actions are supported |

## 3. Analysis

### 3.1 Current board state

| Item | Current state | Evidence | Implication |
|------|---------------|----------|-------------|
| #815 | Archived | Task body + audit section already mark it won't-do | #837's requested action is already complete |
| #549 | Archived | Parent body already lists #815 as archived | Parent task is already the source of truth |
| #837 | Ideation | Current task file still asks to archive #815 | Stale meta-task |
| #823 | Todo | Body says complete, but status is still actionable | Confirms this is not a one-off cleanup gap |

### 3.2 Live repository evidence

Current search across `src/` and `tests/` still found zero package-level browser imports.

| Import style | Current count | Implication |
|--------------|---------------|-------------|
| `from owlbear.tools.browser import X` | 0 | No consumer demand for package-level browser re-exports |
| Deep browser import statements | 217 | The codebase continues to use explicit module imports |

This keeps the original decision intact: no new action on #815 is warranted.

### 3.3 Options

| Option | Outcome | Trade-off | Confidence |
|--------|---------|-----------|------------|
| Archive only #837 | Removes one stale task | Leaves sibling #823 stale | .70 |
| Create one cleanup task for #823 and #837 | Resolves both stale closure tasks and keeps #549 as source of truth | One extra board task | .92 |
| Re-open #815 work | Contradicts approved decision and archived parent state | Wrong action | .00 |

## 4. Recommendation (.92 confidence)

Do not perform any more closure work on #815. It is already archived, the approved decision stands,
and the umbrella task already records the final state.

The correct follow-up is a single board-cleanup task that archives the two stale closure meta-tasks
(#823 and #837) with a short note pointing back to #549 and the resolved decision.

This is the simplest path that matches the board state, preserves a single source of truth, and avoids
creating more redundant closure tasks.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Archive stale re-export closure meta-tasks (#823, #837)" --priority nice-to-have --status ideation --tags "audit,scope:core" --description "Board cleanup only. #813 and #815 are already archived, and #549 already records the resolved re-export decision. Append a one-line closure note to #823 and #837, archive both tasks, and keep #549 as the source of truth for the re-export workstream. See docs/research/re-export-closure-meta-tasks.md."
```
