---
agent: builder
description: "Implement a kanban task or feature using TDD"
---

Build: ${input:task_or_feature:Task ID or feature description — e.g. 'task #40', 'SkillRegistry with progressive loading', 'fix TypeError in session.py'}

**Context for this run:**

- If a task ID is given, read the AC: `kanban\kanban-md.exe show {id}`
- Move to in-progress: `kanban\kanban-md.exe move {id} in-progress`
- **TDD is mandatory**: write failing tests first, then implement minimal code
- Read existing code patterns before creating new files
- Verify before advancing:
  - `uv run pytest tests/ -m "not api" --tb=short -q` — all pass
  - `uv run ruff check src/ tests/` — all clean
  - Coverage ≥ 90% on touched modules
- Move to review when verified: `kanban\kanban-md.exe move {id} review`
- Surgical changes only — smallest diff that achieves the AC
