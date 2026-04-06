---
name: w-doc-update
description: "Workflow: Documentation update — verify and update docs for completed tasks"
user-invocable: false
---

# Documentation Update

Verify and update documentation for a task that has passed review. The doc-writer evaluates what changed, updates affected docs, cleans scratch files, and advances to done.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `docs` status.

### Step 0a — Verify Upstream Review Evidence

Check the task body for a `## Review Evidence` section. If **absent**, the reviewer skipped this mandatory section — reject via `end_work(outcome="reject", move_to="review", note="Missing ## Review Evidence section")`.

This is a recurring pipeline gap. Enforcing it here catches the defect one stage earlier than the auditor.

## Step 1 — Assess Documentation Impact

Identify what changed: files created/modified, behavior added. Then evaluate each checklist item with evidence:

### Item 1: Behavior/API Change

- Did the task change behavior, API, or conventions?
- If yes: read `.github/copilot-instructions.md` and update relevant tables/sections.
- If no: note "no behavior change."

### Item 2: Module Docstrings

- Did the task create or modify Python modules?
- If yes: read source files, verify all public classes and functions have accurate docstrings.
- Edit `.py` files for docstrings ONLY — never change application logic.

### Item 3: External Attribution

- Did the task use patterns from external repos, articles, or docs?
- If yes: add a row to `.owlbear/sources/overview.md` (see `r-project-standards` → Attribution).

### Item 4: CLI Changes

- Did the task add or modify CLI commands?
- If yes: update usage examples in `README.md`.

### Item 5: Research Doc

- Did the research phase produce a `.owlbear/research/{slug}.md`?
- If yes: verify it exists and is linked from the task body. Verify follow-up tasks were created.

### Item 6: No Impact

- If none of items 1–5 apply: note "no docs impact" explicitly.

## Step 2 — Clean Scratch Files

Look for `.owlbear/scratch/{task-id}-*` files and delete any that exist.

## Step 3 — Deliverables

If you updated any files in Step 1, commit per `r-project-standards` → Commit Discipline:

```powershell
git add {updated_files}
git commit -m "docs: update docs for {feature} (#{id}, doc-writer)"
```

Verify only documentation files are staged. Skip if no files were updated.

## Step 4 — Advance

Include the docs gate report in your `end_work` note.

Advance via `end_work` (moves to `done` + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

**Rejection:** If untested behavior is found, reject via `end_work(outcome="reject", move_to="review")`.

## Output Template

Append to task body before advancing:

```
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | {Yes/No} | {Updated/N/A} | {details} |
| 2 | Module docstrings | {Yes/No} | {Updated/N/A} | {details} |
| 3 | External attribution | {Yes/No} | {Updated/N/A} | {details} |
| 4 | CLI changes | {Yes/No} | {Updated/N/A} | {details} |
| 5 | Research doc | {Yes/No} | {Verified/N/A} | {details} |

### Files Updated
- {list or "None"}

### Scratch Files Cleaned
- {list or "None"}
```

## Verification Checklist

- [ ] Task is in `docs` status
- [ ] Upstream `## Review Evidence` present (rejected if missing)
- [ ] All checklist items (1–5) evaluated with evidence
- [ ] For N/A items, explained why they don't apply
- [ ] For updated items, actually made the edits
- [ ] Did NOT change application logic — only docstrings and documentation
- [ ] Scratch files cleaned (`.owlbear/scratch/{task-id}-*`)
- [ ] Docstrings verified on all public API in new/changed modules
- [ ] `.owlbear/sources/overview.md` updated if external inspiration was used
- [ ] Documentation changes committed before advancing

## Known Pitfalls

- **Missing Review Evidence upstream:** This is the most common rejection reason at the docs gate. Check for it first to avoid wasted work.
- **Editing application logic:** The doc-writer must ONLY edit docstrings and documentation files. Any logic change is out of scope.
- **Forgetting scratch cleanup:** Orphaned scratch files accumulate as noise. Always check and clean `.owlbear/scratch/{task-id}-*`.
- **Stale docstrings:** When verifying docstrings, read the actual code behavior. A docstring that matches the old behavior before the builder's change is stale.
