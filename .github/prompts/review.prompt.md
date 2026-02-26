---
agent: reviewer
description: "Review and verify task output with evidence"
---

Review: ${input:task_or_files:Task ID or file paths — e.g. 'task #40', 'src/owlbear/skills/registry.py', 'all review'}

**Context for this run:**

- If a task ID is given, read the AC: `kanban\kanban-md.exe show {id}`
- **Run tests yourself** — never trust self-reports:
  - `uv run pytest tests/ -m "not api" --tb=short -q`
  - `uv run ruff check src/ tests/`
  - `uv run pytest --cov=owlbear --cov-report=term-missing -q`
- Read the actual source code with `read_file`
- Verify every AC line with specific evidence (test names, line numbers, output)
- Produce an AC compliance table: AC Line | Evidence | PASS/FAIL
- Binary verdict only: PASS or FAIL (no "conditional pass")
- PASS → `kanban\kanban-md.exe move {id} docs` then check docs gate → `done`
- FAIL → `kanban\kanban-md.exe move {id} todo` with specific failure reasons
- **NEVER edit any files** — you are strictly read-only
