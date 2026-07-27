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

- Commit only files owned by the current packet or user-requested change. A dirty worktree or mixed
  index is not a reason to skip an owned commit.
- Use the shared scoped helper:
  `uv --project {owlbear-root} run commit-owned -m "type: description (#task-id, agent)" -- path [path...]`.
- The helper preserves unrelated staged paths and unstages only its own paths if `git commit` fails.
  It rejects owned paths that were already staged because it cannot distinguish user work from agent
  work in the same path.
- On a same-job retry after a crash or unstructured return, treat uncommitted changes within the
  admitted packet envelope as candidate work from the interrupted attempt. Inspect the complete diff,
  validate it against the packet, and explicitly adopt it before committing. Do not
  infer an ownership conflict from a dirty path, file timestamp, or invocation boundary alone. If a
  concrete hunk conflicts with the task or cannot be safely attributed, name that path and hunk in the
  containment reason instead of describing the whole task-owned diff as mixed.
- Pass explicit file paths to `commit-owned`; never pass `.`, a native authority/work-state root, or
  another broad directory. The selected packet impact closure bounds eligible implementation paths.
- A native builder returns `BuilderSuccess` only after the scoped commit exists, its path set equals
  the packet-owned set, no packet-owned change remains outside it, and a fresh read-only review
  passes that exact commit.
- If the scoped commit cannot be created or verified, return `CommitFailed` with the bounded command,
  error, and changed paths. Do not issue completion fields, broaden the commit, or mutate lifecycle
  state. The orchestrator releases the unchanged active job identity.
- A permitted local `implementation-defect` repair uses another explicit scoped commit, reruns
  affected proof, and requires fresh review of the cumulative packet result.
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
