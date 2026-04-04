---
name: docs-gate
description: "Documentation gate checklist: verify and update docs before marking a task done. Use when a task reaches docs status."
user-invocable: false
---

# Docs Gate Workflow

Step-by-step process for the documentation gate (docs → done).

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append report | `kanban\kanban-md.exe edit {id} -a "## Docs Gate\n{content}" -t --claim <agent>` |
| Advance (pass) | `kanban\kanban-md.exe edit {id} --status done --release` |
| Reject to review | `kanban\kanban-md.exe edit {id} --status review --release` |
| Claim + show task (MCP) | `start_work {id}` |
| Append to task body (MCP) | `edit_task {id}` |
| Advance + release (MCP) | `end_work {id}` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Read and claim the task

1. `kanban\kanban-md.exe show {id}` — read full task details
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)

> **MCP equivalent:** `start_work(task_id="{id}")` — claim + read in one call (replaces steps 1–2).

3. Verify task is in `docs` status
4. Identify what changed: files created/modified, behavior added

## Step 2 — Run docs-gate checklist

Evaluate each item with evidence, not assumptions:

### Item 1: Behavior/API change → .github/copilot-instructions.md

- Did the task change behavior, API, or conventions?
- If yes: read `.github/copilot-instructions.md` and update the relevant tables/sections
- If no: note "no behavior change"

### Item 2: Module added/changed → docstrings

- Did the task create or modify Python modules?
- If yes: read source files, verify all public classes and functions have accurate docstrings
- Edit `.py` files for docstrings ONLY — never change application logic

### Item 3: External inspiration → docs/sources/overview.md

- Did the task use patterns from external repos, articles, or docs?
- If yes: add a row to `docs/sources/overview.md` (Source, URL, What, Where Used, Date)

### Item 4: CLI commands changed → README.md

- Did the task add or modify CLI commands?
- If yes: update usage examples in `README.md`

### Item 5: Research doc produced → archived/linked

- Did the research phase produce a `docs/research/{slug}.md`?
- If yes: verify it exists and is linked from the task body
- Verify follow-up kanban tasks were created

### Item 6: No impact

- If none of items 1–5 apply: note "no docs impact" explicitly

## Step 3 — Clean scratch files

- Look for `docs/scratch/{task-id}-*` files
- Delete any that exist

## Step 4 — Commit documentation changes

If you updated any files in Step 2, stage and commit them:

```powershell
git add {updated_files}
git commit -m "docs: update docs for {feature} (#{id}, writer)"
```

Verify only documentation files are staged (`git diff --cached --name-only`). Skip this step if no files were updated.

## Step 5 — Advance + release

Advance the task to `done` and release the claim in one atomic command:

```powershell
kanban\kanban-md.exe edit {id} --status done --release
```

> **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")`

## Docs gate output format

```
## DocsGateReport: #{id} — {title}

### Docs-Gate Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|

### Files Updated
- {list or "None"}

### Scratch Files Cleaned
- {list or "None"}

### Action Taken
kanban\kanban-md.exe edit {id} --status done --release
```

## Boundaries

- If you find untested behavior: reject to review with `kanban\kanban-md.exe edit {id} --status review --release`
  (MCP: `end_work(task_id="{id}", note="...", outcome="reject")`)

## Verification checklist

- [ ] Task is in `docs` status
- [ ] All checklist items (Items 1–5) evaluated with evidence
- [ ] For "N/A" items, explained why they don't apply
- [ ] For "Updated" items, actually made the edits
- [ ] Scratch files cleaned (`docs/scratch/{task-id}-*` deleted)
- [ ] Documentation changes committed (if any files updated in Step 2)
- [ ] Did NOT change application logic — only docstrings and documentation
- [ ] Cleaned up `docs/scratch/{task-id}-*` files
- [ ] Verified docstrings on all public API in new/changed modules
- [ ] `docs/sources/overview.md` updated if external inspiration was used
- [ ] Documentation changes committed before advancing
