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
- Commit only files touched by your current task. Check `git status --short` and `git diff --cached` before committing.
- Never push. The user pushes manually.

### VS Code Auto-Staging Trap

VS Code silently re-serializes and stages `.agent.md` files when it detects new tool capabilities. Always run `git diff --cached share/agents/` before committing and unstage any auto-generated reverts with `git reset HEAD <file>`.

## 2. Attribution

External code and patterns must be logged in `.owlbear/sources/overview.md`:

| Column | Description |
|--------|-------------|
| Source | Project or article name |
| URL | Link to the repo, article, or doc |
| What | What was taken (pattern, code snippet, architecture idea) |
| Where Used | Where it appears in OwlBear (file path or module) |
| Date | When it was adopted |

## 3. Priority Scheme

| Priority | Meaning | When to use |
|----------|---------|-------------|
| `someday` | Future vision, no commitment | Ideas we might never build |
| `nice-to-have` | Useful improvement, no urgency | Build when everything important is done |
| `important` | Clear value, scheduled **(default)** | Most feature work |
| `needed` | Core capability, do soon | Required for next milestone |
| `critical` | Can't function without it | Current blocker |

## 4. Tag Taxonomy

Tags are free-form. Conventions:

| Category | Examples | Purpose |
|----------|---------|---------|
| Phase | `phase-1` … `phase-12` | Group by project phase |
| Category | `config`, `tooling`, `docs`, `test`, `cli`, `agent` | Area touched |
| Type | `type:build`, `type:test`, `type:docs`, `type:user-action` | Kind of work |
| | `type:user-action` — requires physical user action before pipeline can continue; architect creates AR, blocks task, and uses fast-path on re-entry (see r-pipeline-protocol §5) | |
| Scope | `scope:copilot`, `scope:core`, `scope:cli` | Codebase part |
| Rigor | `rigor:lean`, `rigor:standard`, `rigor:thorough` | Quality-vs-speed profile |
