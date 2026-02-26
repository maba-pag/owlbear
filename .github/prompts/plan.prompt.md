---
agent: kanban-planner
description: "Decompose a plan or feature description into atomic, dependency-aware kanban tasks"
---

Plan: ${input:plan_description:Feature or plan description — e.g. 'Phase 8: add law parser' or paste a section from docs/plan.md}

**Context for this run:**

- Read the current board state first: `kanban\kanban-md.exe list --compact`
- Check the highest existing task ID to avoid collisions
- Decompose into atomic TDD pairs (test task before impl task, with --depends-on)
- Every task body must include a link to the source plan/doc section
- Output ready-to-paste `kanban-md create` commands, NOT executed — user reviews first
- Include a Mermaid dependency graph
