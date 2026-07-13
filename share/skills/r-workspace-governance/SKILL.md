---
name: r-workspace-governance
description: "Rules: Owned commits, OwlBear-managed artifact placement, and source attribution"
user-invocable: false
---

# Workspace Governance

Contributor-neutral rules for custody and traceability of changes in OwlBear-enabled projects.

## Commit Discipline

### Format

```text
type: description (#task-id, context)
```

**Types:** `feat` (new feature), `fix` (bug fix), `test` (test additions or changes), `docs`
(documentation), `chore` (tooling, dependencies, or configuration), and `refactor` (code restructure
without behavior change).

**Example:** `feat: implement retry logic (#480, builder)`

### Rules

- One logical commit per agent per task. No micro-commits or multi-task batches.
- Commit only files owned by the current task. A dirty worktree or mixed index is not a reason to
  skip a task-owned commit.
- Use the shared scoped helper:
  `uv --project {owlbear-root} run commit-owned -m "type: description (#task-id, agent)" -- path [path...]`.
- The helper preserves unrelated staged paths and unstages only its own paths if `git commit` fails.
  It rejects owned paths that were already staged because it cannot distinguish user work from agent
  work in the same path.
- Pipeline agents call `end_work` first so the final note, status, and archive move exist, then
  immediately commit all task-owned durable changes plus the final task record before returning a
  success verdict. Builders own product and durable proof files, verifiers own local fixes, and
  collectors own board or archive changes they make.
- Pass explicit file paths to `commit-owned`; never pass `.`, `.owlbear/kanban/`, or another broad
  directory. Include the active task path for ordinary transitions. For archival transitions,
  include both the former `.owlbear/kanban/tasks/{slug}.md` path and the resulting
  `.owlbear/kanban/archive/{slug}.md` path so Git records the move.
- `end_work` success is not agent completion. Do not return `DONE`, `PASS`, or `ARCHIVED` until the
  scoped commit succeeds. If it fails, repair or retry the same scoped commit without mutating
  another task.
- If the scoped commit still cannot succeed and the task remains on-board, immediately call
  `edit_task(id={task-id}, block_reason="COMMIT_FAILED: {concise error and recovery command}")`.
  Return `COMMIT_FAILED`, never a success verdict. The filesystem block prevents orchestrator
  redispatch even though the block itself is not yet committed. An archived task is already
  off-board; return `COMMIT_FAILED` with the same recovery command and do not claim success.
- Recover a `COMMIT_FAILED` task by completing the original explicit-path commit first. For an
  on-board task, then clear the block with `edit_task(id={task-id}, block_reason="")` and make a
  task-record-only recovery commit. These two recovery commits are the explicit exception to the
  one-commit rule because the first restores durable ownership and the second restores dispatch.
- Never push. The user pushes manually.

### VS Code Auto-Staging Trap

VS Code may re-serialize and stage `.agent.md` files when it detects new tool capabilities. Run
`git diff --cached share/agents/` before committing and unstage unrelated generated changes without
reverting them.

### Owned Auto-Staging Recovery

An editor or file watcher may stage a collector's task-to-archive rename before `commit-owned` runs.
When the helper reports that the owned task or archive path is already staged:

1. Inspect only both owned paths with
  `git diff --cached --name-status -- .owlbear/kanban/tasks/{slug}.md .owlbear/kanban/archive/{slug}.md`.
2. Prove the staged archive contains no extra content by comparing
  `git rev-parse HEAD:.owlbear/kanban/tasks/{slug}.md` with
  `git rev-parse :.owlbear/kanban/archive/{slug}.md`. Continue only when both commands succeed, the
  blob IDs are identical, and step 1 shows exactly `R100` for the current task's rename. This proves
  only the stale pure rename is staged; the collector-authored final archive content remains in the
  working tree. A mismatch, missing object, or any staged shape other than `R100` is ambiguous:
  apply `COMMIT_FAILED`; do not unstage it.
3. Unstage only those verified owned paths with
  `git reset HEAD -- .owlbear/kanban/tasks/{slug}.md .owlbear/kanban/archive/{slug}.md`.
4. Retry `commit-owned` with both paths so it stages the current working-tree archive, including the
  collector-authored final content, and commits the complete final archive state.

The reset command may print a summary of every remaining unstaged change. That output does not mean
those unrelated paths were modified or unstaged by the exact pathspec.

## OwlBear-Managed Artifact Placement

| Artifact | Location | Rule |
|----------|----------|------|
| Temporary output, debug files, and one-off scripts | `.owlbear/scratch/{task-id}-{description}.{ext}` | Untracked; delete before task closure. |
| Approved external repository clones | `.owlbear/scratch/research/{repo-name}/` | Inspect only; delete before task closure. |
| Durable research findings | `.owlbear/research/{slug}.md` | Tracked; include the task reference. |
| External source attribution | `.owlbear/sources/overview.md` | Tracked; use the Attribution schema below. |
| Decision and action requests | `.owlbear/kanban/decisions/` | Create through Kanban tools; do not hand-author alternate locations. |
| Generated navigation indexes | `.owlbear/doc-index.md`, `.owlbear/py-index.md`, `.owlbear/ts-index.md` | Regenerate with `uv run --project {owlbear-root} indexes {project-root}`. |

Project-owned source, test, documentation, and benchmark locations come from the local project map,
manifests, and existing structure. Use `h-codebase-orientation` to discover them; do not impose
OwlBear's own source layout on consuming projects.

Shared agent ecosystem assets follow `h-agent-structure`; project-local customizations live under
the corresponding `.owlbear/agents/`, `.owlbear/skills/`, `.owlbear/instructions/`, and
`.owlbear/prompts/` directories.

## Attribution

External code and patterns must be logged in `.owlbear/sources/overview.md`:

| Column | Description |
|--------|-------------|
| Source | Project or article name |
| URL | Link to the repository, article, or documentation |
| What | Pattern, code snippet, architecture idea, or other material used |
| Where Used | File path or module where it was applied |
| Date | Date adopted |
