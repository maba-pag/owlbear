---
description: "Audit done tasks, archive confirmed, then commit changes in logical packages"
---

Audit & Commit: ${input:scope:Filter scope — e.g. 'all done', 'tag:phase-2', 'tasks >100'}

This prompt runs two phases back-to-back. The audit phase builds a complete picture of what changed; the commit phase uses that knowledge to write perfectly scoped commits.

## Phase 1 — Audit

### 1.1 Gather tasks

```powershell
kanban\kanban-md.exe list --compact --status done
```

If a scope filter was given, apply it (e.g., tag filter, ID range). Read the full AC for every matching task with `kanban\kanban-md.exe show {id}`.

### 1.2 Verify each task

For **every** AC item on **every** task, collect concrete evidence:

- **File exists:** Read the file with `read_file`. Do not assume — verify.
- **Code matches AC:** Grep or read for specific classes, functions, constants, signatures, field names.
- **Tests exist and pass:** Run `uv run pytest tests/ -m "not api and not slow" --tb=short -q` once for the full suite. For per-task confidence, check that the relevant test file exists and contains the expected test functions.
- **Lint clean:** Run `uv run ruff check src/ tests/` once.
- **AC deviations:** Note any naming, location, or design differences between the AC and the actual implementation. Minor deviations (e.g., improved naming, different file path) are acceptable if the intent is met. Major deviations (missing functionality, incomplete features) are not.

Use the `reviewer` agent for batches of ~10 tasks to parallelize verification. Trust reviewer output only after cross-checking the summary against your own AC notes.

### 1.3 Score confidence

| Score | Meaning |
|-------|---------|
| `1.0` | Every AC item verified with evidence, no deviations |
| `.90` | All AC items met, minor naming or path deviations from spec |
| `.80` | Most AC items met, one non-trivial deviation (e.g., different return type) |
| `.70` | Functional but multiple deviations from AC, needs human judgment |
| `< .70` | Incomplete or unverifiable — do not archive |

### 1.4 Archive or hold

- **Score >= .80:** Archive with `kanban\kanban-md.exe archive {id}`
- **Score < .80:** Leave in `done`. Note the specific gaps.
- **Abandoned/dead tasks:** Flag for user decision; do not archive.

### 1.5 Audit report

Present a **single summary table** sorted by confidence descending:

| ID | Content (3-8 words) | Evidence summary | Confidence | Action |
|----|---------------------|------------------|------------|--------|
| ... | ... | ... | ... | Archived / Held / Flagged |

After the table, list totals (archived / held / flagged), recurring issues, and remaining `done` tasks with recommended next steps.

---

## Phase 2 — Commit

The audit just gave you a full inventory of every task, its files, and its purpose. Use that knowledge to create logical, perfectly scoped commits. Only proceed to this phase after showing the audit report.

### 2.1 Assess working tree

```powershell
git status --short
git log --oneline -5
```

If the working tree is clean, say so and stop.

### 2.2 Group changes into commit packages

Use the audit inventory to group files by **feature cohesion** — each commit should tell one story. Apply these heuristics in priority order:

1. **Feature cohesion:** Source + tests + config for the same feature belong together. Map each commit to one or more task IDs.
2. **Layer separation:** Infra, tooling, or dependency changes separate from feature code.
3. **Kanban board separate:** Task file changes (kanban/tasks/*.md, activity.jsonl) are a `chore:` commit.
4. **Docs together:** README, copilot-instructions, sources.md grouped as `docs:`.
5. **Agent definitions together:** Agent `.md` files + matching prompts as one commit.

### 2.3 Commit message format

```
type: concise summary

- bullet details for commits with 5+ files
- reference task IDs where applicable
```

| Type | When |
|------|------|
| `feat:` | New feature (source + tests) |
| `fix:` | Bug fix |
| `refactor:` | Code restructuring, no behavior change |
| `test:` | Test-only changes |
| `chore:` | Tooling, kanban board, config, infra |
| `docs:` | Documentation updates |

### 2.4 Execute commits

For each package: stage only its files, commit, then move to the next package. After all commits, run `git log --oneline -10` and report the result.

### 2.5 Push

Run `git push` and confirm success.

---

## Rules

- **Never trust self-reports.** Read the actual code. Run the actual tests.
- **Phase 1 is read-only.** The only mutations are `kanban\kanban-md.exe archive` calls.
- **Phase 2 is git-only.** No code edits — only `git add`, `git commit`, `git push`.
- **Binary evidence only.** Each AC item is PASS or FAIL, backed by a file path and line number or test output.
- **Use `manage_todo_list`** to track progress through both phases.
- **Batch efficiently.** Read all ACs first, then verify in parallel where possible.
- **Never create a single monolithic commit.** Each commit must be independently meaningful.
- **Ask before pushing** if there are held or flagged tasks — uncommitted concerns may affect commit scope.
