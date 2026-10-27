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

- Commit only files owned by the active task or user-requested change. A dirty worktree or mixed
  index is not a reason to skip an owned commit.
- Use the shared scoped helper:
  `uv --project {owlbear-root} run commit-owned -m "type: description (#task-id, agent)" -- path [path...]`.
- The helper preserves unrelated staged paths and unstages only its own paths if `git commit` fails.
  It rejects owned paths that were already staged because it cannot distinguish user work from agent
  work in the same path.
- When a task changes an input that determines a tracked generated output, commit the generated
  output with those inputs in the same scoped commit.
- Pass explicit file paths to `commit-owned`; never pass `.`, a Delivery state root, or another
  broad directory.
- Never push, merge, or run provider mutations directly (`git push`, `gh pr merge`, `gh api` writes).
  Delivery publishes Change branches, draft pull requests and its state as system work, and merges
  only after the user approves the exact head on the Changes page. Otherwise the user pushes manually.

### VS Code Auto-Staging Trap

VS Code may re-serialize and stage `.agent.md` files when it detects new tool capabilities. Run
`git diff --cached share/agents/` before committing and unstage unrelated generated changes without
reverting them.

## OwlBear-Managed Artifact Placement

| Artifact | Location | Rule |
| --- | --- | --- |
| Temporary output, debug files, and one-off scripts | `.owlbear/scratch/{task-id}-{description}.{ext}` | Untracked; delete before task closure. |
| Approved external repository clones | `.owlbear/scratch/research/{repo-name}/` | Inspect only; delete before task closure. |
| Durable research findings | `owlbear-data/<folder>/research/{slug}.md` (OwlBear's folder: `owlbear`); OwlBear's record and unbuilt build designs: `.owlbear/research/`; its plan: the [pinned tracker issue](https://github.com/maba-pag/owlbear/issues/713) | Tracked; include the task reference; never committed into another project (TD-227, TD-347, TD-395). |
| External source attribution | `.owlbear/sources/overview.md` | Tracked; only sources whose material still ships; use the Attribution schema below. |

Project-owned source, test, documentation, and benchmark locations come from the local project map,
manifests, and existing structure. Use `h-codebase-orientation` to discover them; do not impose
OwlBear's own source layout on consuming projects.

Shared agent ecosystem assets follow `h-agent-structure`; project-local customizations live under
the corresponding `.owlbear/agents/`, `.owlbear/skills/` and `.owlbear/instructions/` directories.

## Attribution

External code, text and patterns that OwlBear adopts get a row in `.owlbear/sources/overview.md` when the
adopting change lands; the row leaves with the asset. Sources only read for research are cited in the research
document, not here.

| Column | Description |
| --- | --- |
| Source | Project or article name |
| URL | Link to the repository, article, or documentation, written `<https://…>` |
| Licence | The upstream licence, or the notice that governs the material |
| What | Pattern, code, text, or other material adopted |
| Where Used | Backticked repository paths of the files that carry it |
