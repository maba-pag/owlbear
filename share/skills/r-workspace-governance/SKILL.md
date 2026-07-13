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
  scoped commit succeeds. If it fails, repair or retry the scoped commit without advancing or
  mutating other tasks; report the commit failure instead of a success verdict if it cannot be
  completed.
- Never push. The user pushes manually.

### VS Code Auto-Staging Trap

VS Code may re-serialize and stage `.agent.md` files when it detects new tool capabilities. Run
`git diff --cached share/agents/` before committing and unstage unrelated generated changes without
reverting them.

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
