---
agent: orchestrator
description: "Start the orchestrator to read the kanban board, plan execution waves, and dispatch subagents"
---

Orchestrate: ${input:scope_or_filter:Scope filter — e.g. 'phase-7', 'all todo', 'tag:linting', 'tasks 82-88'}

**Context for this run:**

- Read the board with `kanban\kanban-md.exe list --compact` first
- Apply the scope filter above to select tasks
- For each relevant task, read its full AC with `kanban\kanban-md.exe show {id}`
- Build the dependency graph, run all 5 gate checks, then plan execution waves
- Remember: deliverables are working code, passing tests, and verified documentation
- Dispatch `reviewer` subagent before moving any task review → docs
- Dispatch `writer` subagent before moving any task docs → done
- Dispatch `closer` subagent for done tasks — verifies, archives, commits, pushes
- Do NOT run pytest or ruff yourself — the reviewer handles verification
- Your sanity check is lightweight: verify files exist, spot-check subagent reports
