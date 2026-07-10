---
description: "Start the orchestrator to read the kanban board, plan execution waves, and dispatch subagents"
agent: orchestrator
---

Orchestrate: ${input:scope_or_filter:Scope filter — e.g. 'phase-7', 'status:build', 'tag:linting', 'tasks 82-88', default: 'all'}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting dispatch choices, blockers, or continuation decisions, present exactly one decision item at a time before calling `askQuestions`.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.
