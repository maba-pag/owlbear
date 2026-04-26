---
name: w-doc-update
description: "Workflow: Documentation update — verify and update docs for completed tasks"
user-invocable: false
---

# Documentation Update (v2)

Verify and update documentation for a task that has passed review. The doc-writer classifies
scope, applies relevance gating, runs the checklist against IN-scope affected docs, handles
diagram maintenance, and proposes deletions via child tasks. Advances to `done`.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved
body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved
Decision Pre-flight.

Verify the task is in `docs` status.

### Step 0a — Verify Upstream Review Evidence

Check the task body for a `## Review Evidence` section. If **absent**, the reviewer skipped
this mandatory section — reject via `end_work(outcome="reject", move_to="review",
note="Missing ## Review Evidence section")`.

This is a recurring pipeline gap. Enforcing it here catches the defect one stage earlier
than the auditor.

### Step 0b — Load Doc-Index

Read `.owlbear/doc-index.md`. If the file is missing or a `uv run doc-index` regen fails,
log the failure and continue with a stale or empty index (advisory — do not block). The
index is used for scope classification and `describes` glob lookups in later steps.

## Step 1 — Scope Classification

Build the **changed-files set** from the task body: scan `## Files`, `## Builder Notes`,
and `## Review Evidence` sections for file paths mentioned.

Classify each file as **IN-scope** or **OUT-scope**:

**IN scope (edit + deletion-proposal):**

- Root: `README.md`, `README-consumer.md`, `SECURITY.md`
- Package READMEs: `serve/*/README.md` (9 files)
- Setup guides: `setup/setup-guide.md`, `setup/sharing-guide.md`
- Share ecosystem doc: `share/README.md`
- Diagrams: `share/diagrams/*.excalidraw`
- Research and sources: `.owlbear/research/*.md`, `.owlbear/sources/*.md`
- Docstrings in `.py` files

**OUT scope (no edit, no deletion-proposal):**

- `share/agents/*.agent.md` (agent-executable)
- `share/skills/*/SKILL.md` (agent-executable)
- `share/instructions/*.instructions.md` (agent-executable)
- `share/prompts/*.prompt.md` (agent-executable)
- `share/skills/*/references/*.md` (agent-executable)
- `.github/copilot-instructions.md` (agent-executable)
- All application source code (except docstrings)

If all changed files are OUT-scope or non-doc source files, proceed to the no-impact check
at the end of Step 2.

## Step 2 — Relevance-Gated Checklist

Evaluate only the items relevant to the IN-scope changed files. Not every item applies to
every task.

### Item 1: Descriptive Prose Docs

- Did the task change behavior, API, CLI commands, configuration, or package structure?
- Identify which IN-scope descriptive docs reference the changed area.
- If yes and IN-scope docs are affected: read each affected doc, verify accuracy, update
  as needed.
- If no IN-scope docs reference the changed area: note "no prose docs affected."

### Item 2: Module Docstrings

- Did the task create or modify Python modules?
- If yes: read source files, verify all public classes and functions have accurate
  docstrings.
- Edit `.py` files for docstrings ONLY — never change application logic.

### Item 3: External Attribution

- Did the task use patterns from external repos, articles, or docs?
- If yes: add a row to `.owlbear/sources/overview.md` (see `r-project-standards` →
  Attribution).

### Item 4: Research Doc

- Did the research phase produce a `.owlbear/research/{slug}.md`?
- If yes: verify it exists and is linked from the task body. Verify follow-up tasks were
  created.

### Item 5: Diagram Maintenance

- Consult the doc-index for `describes` entries. Does any IN-scope diagram have a
  `describes` glob that matches one or more changed files?
- If yes: update that diagram's footer text element to
  `Last verified: <today's date> (<current short commit hash>)`. Do not modify diagram
  content beyond the footer.
- If no match: note "no diagram describes-match found."

### Item 6: Explicit Diagram Creation

- Does the task body contain an explicit request to create a new diagram
  (e.g., "Create a share/diagrams/X.excalidraw diagram…")?
- If yes: create the diagram using the `h-excalidraw-diagram` skill. Include a footer
  text element: `Last verified: <today's date> (<current short commit hash>)`. Trigger
  doc-index regeneration after creation (`uv run doc-index`).
- If no: note "no explicit diagram creation request."

### Item 7: Deletion Detection

- Does the changed-files set include **deleted** files? Do any IN-scope descriptive docs
  reference the deleted features or files?
- If yes (deletion candidate detected):
  1. Do **not** delete or modify the IN-scope doc directly.
  2. Create a child kanban task:
     `ob-kanban/create_task(title="Delete stale docs in <path>", parent=<current_task_id>)`.
  3. Block the child: `ob-kanban/edit_task(task_id=<child_id>, blocked=true,
block_reason="awaiting deletion DR")`.
  4. Invoke scribe: `Scribe: task_id=<current_task_id>, mode=check-or-create,
concern="delete stale <path> — references deleted <feature>"`. Scribe writes a DR to
     `.owlbear/decisions/pending/`.
  5. Record the child task id in `## Docs Gate`.
  6. **The current task advances to `done` without waiting for DR resolution.**
- If no deletion candidates: note "no orphaned IN-scope docs detected."

**No-impact case:** If all seven items resolve to N/A, write "no docs impact" explicitly
in the `## Docs Gate` section and advance — no busywork.

## Step 3 — Clean Scratch Files

Look for `.owlbear/scratch/{task-id}-*` files and delete any that exist.

## Step 4 — Deliverables

If you updated any files in Step 2, commit per `r-project-standards` → Commit Discipline:

```shell
git add {updated_files}
git commit -m "docs: update docs for {feature} (#{id}, doc-writer)"
```

Verify only documentation files are staged — no application code, no test files. Skip if
no files were updated.

If you created a new diagram or updated the doc-index, include those files in the commit.

## Step 5 — Advance

Include the docs gate report in your `end_work` note.

Advance via `end_work` (moves to `done` + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

**Rejection:** If untested behavior is found, reject via
`end_work(outcome="reject", move_to="review")`.

## Output Template

Append to task body before advancing:

```
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | {Yes/No} | {Updated/N/A} | {details} |
| 2 | Module docstrings | {Yes/No} | {Updated/N/A} | {details} |
| 3 | External attribution | {Yes/No} | {Updated/N/A} | {details} |
| 4 | Research doc | {Yes/No} | {Verified/N/A} | {details} |
| 5 | Diagram maintenance (describes match) | {Yes/No} | {Updated/N/A} | {details} |
| 6 | Explicit diagram creation | {Yes/No} | {Created/N/A} | {details} |
| 7 | Deletion detection | {Yes/No} | {Child task created/N/A} | {details} |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| {path} | IN/OUT | {Updated / N/A / Child task #{id}} |

### Files Updated
- {list or "None"}

### Child Tasks Created
- {list or "None"}

### Scratch Files Cleaned
- {list or "None"}
```

## Verification Checklist

- [ ] Task is in `docs` status
- [ ] Upstream `## Review Evidence` present (rejected if missing)
- [ ] Doc-index loaded (advisory; continue on failure)
- [ ] Changed-files set built from task body; each file classified IN/OUT scope
- [ ] All checklist items (1–7) evaluated with evidence for IN-scope files
- [ ] For N/A items, explained why they don't apply
- [ ] For updated items, actually made the edits
- [ ] Did NOT change application logic — only docstrings and documentation
- [ ] Did NOT edit any OUT-of-scope agent-executable file
- [ ] Diagram maintenance applied only where `describes` glob matched
- [ ] Deletion candidates handled via child task + DR, not direct modification
- [ ] Scratch files cleaned (`.owlbear/scratch/{task-id}-*`)
- [ ] Documentation changes committed before advancing

## Known Pitfalls

- **Missing Review Evidence upstream:** Most common rejection at the docs gate. Check
  first to avoid wasted work.
- **Scope creep into agent-executable files:** SKILL.md, .agent.md, .instructions.md,
  .prompt.md, and `.github/copilot-instructions.md` are OUT of scope. Never edit them.
- **Editing application logic:** Doc-writer edits docstrings and documentation only.
- **Forgetting scratch cleanup:** Always check `.owlbear/scratch/{task-id}-*`.
- **Stale docstrings:** Read the actual code behavior; a docstring matching the pre-task
  behavior is stale even if it looks plausible.
- **Deleting docs directly:** Always create a child task + DR. Never delete autonomously.
- **False-positive diagram trigger:** Only update a diagram if a `describes` glob match
  exists in the doc-index. Do not autonomously decide a diagram needs updating.
