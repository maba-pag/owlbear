---
agent: writer
description: "Verify and update documentation for tasks in docs status — docs gate before done"
---

Docs Gate: ${input:task_or_scope:Task ID or scope — e.g. 'task #40', 'all docs', 'tag:phase-3'}

**Context for this run:**

- Read the board: `kanban\kanban-md.exe list --compact --status docs`
- For each task in scope, read full details: `kanban\kanban-md.exe show {id}`
- Run the docs-gate checklist (5 items from copilot-instructions.md):
  1. Behavior/API changed? → update copilot-instructions.md
  2. Module added/changed? → verify docstrings complete
  3. External inspiration? → update docs/sources.md
  4. CLI commands changed? → update README.md
  5. Research doc produced? → verify archived/linked
- If none apply: note "no docs impact" and move through
- Update files as needed, then advance: `kanban\kanban-md.exe move {id} done`
- Clean up: delete `docs/scratch/{task-id}-*` files
- **Never modify source code logic.** Only docstrings and documentation files.
