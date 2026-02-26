---
agent: researcher
description: "Start a research investigation on a topic"
---

Research: ${input:topic:Topic or question — e.g. 'compare ChromaDB vs sqlite-vec', 'task #50', 'Teams integration options'}

**Context for this run:**

- Read the board with `kanban\kanban-md.exe list --compact` first
- If the topic references a kanban task, read it with `kanban\kanban-md.exe show {id}`
- Apply the research checklist (7 items from copilot-instructions.md)
- Follow research-docs guardrails: max 200 lines, comparison tables over prose
- Every research doc MUST produce follow-up kanban tasks — present as commands for review
- Log external sources in `docs/sources.md`
- Clean up: delete any cloned repos from `docs/research/` when done
