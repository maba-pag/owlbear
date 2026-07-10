---
name: r-project-standards
description: "Rules: Project-wide conventions — commit format, attribution, priorities, tags"
user-invocable: false
---

# Project Standards

Contributor-neutral conventions for the OwlBear project. Applies to any contributor — human or agent. Referenced by `r-pipeline-protocol` for pipeline-specific commit rules.

## 1. Commit Discipline

### Format

```
type: description (#task-id, context)
```

**Types:** `feat` (new feature), `fix` (bug fix), `test` (test additions/changes), `docs` (documentation), `chore` (tooling, deps, config), `refactor` (code restructure, no behavior change).

**Example:** `feat: implement retry logic (#480, builder)`

### Rules

- One logical commit per agent per task. No micro-commits, no multi-task batches.
- Commit only files touched by your current task. A mixed index is not a reason to skip a task-owned commit.
- Use the shared scoped helper: `uv --project ../owlbear run commit-owned -m "type: description (#task-id, agent)" -- path [path...]`.
- The helper preserves unrelated staged paths and unstages only its own paths if `git commit` fails. It rejects owned paths that were already staged, because it cannot safely distinguish user work from the agent's changes in one path.
- Pipeline agents commit their task-owned durable changes before successful lifecycle advancement. Builders own product and durable proof files, verifiers own local fixes, and collectors own Kanban/archive changes they make.
- Never push. The user pushes manually.

### VS Code Auto-Staging Trap

VS Code silently re-serializes and stages `.agent.md` files when it detects new tool capabilities. Always run `git diff --cached share/agents/` before committing and unstage any auto-generated reverts with `git reset HEAD <file>`.

## 2. File Placement

- Follow the workspace-specific file placement table in the active project instructions.
- Keep generated scratch, debug, and temporary files out of durable project locations.
- Before closing task work, delete scratch files created for that task.

## 3. Attribution

External code and patterns must be logged in `.owlbear/sources/overview.md`:

| Column | Description |
|--------|-------------|
| Source | Project or article name |
| URL | Link to the repo, article, or doc |
| What | What was taken (pattern, code snippet, architecture idea) |
| Where Used | Where it appears in OwlBear (file path or module) |
| Date | When it was adopted |

## 4. Priority Scheme

| Priority | Meaning | When to use |
|----------|---------|-------------|
| `low` | Worth keeping, no urgency | Opportunistic cleanup or later idea |
| `medium` | Normal priority **(default)** | Most planned work |
| `high` | Current blocker or strong dependency fan-out | Work that unblocks multiple tasks or active use |

## 5. Tag Taxonomy

Tags are free-form. Conventions:

| Category | Examples | Purpose |
|----------|---------|---------|
| Phase | `phase-1` … `phase-12` | Group by project phase |
| Category | `config`, `tooling`, `docs`, `test`, `cli`, `agent` | Area touched |
| Type | `type:build`, `type:test`, `type:docs`, `type:user-action` | Kind of work |
| | `type:user-action` — requires physical user action before pipeline can continue; shaper creates AR, blocks task, and records the resolved decision on re-entry (see r-pipeline-protocol §6) | |
| Scope | `scope:copilot`, `scope:core`, `scope:cli` | Codebase part |
| Rigor | `rigor:lean`, `rigor:standard`, `rigor:thorough` | Quality-vs-speed profile |
