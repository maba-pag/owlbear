---
description: "Start the orchestrator to read the kanban board, plan execution waves, and dispatch subagents"
agent: orchestrator
---

Orchestrate all eligible work.

Use the non-default IF-015 native contract from `w-orchestration` only for an explicitly requested
admitted change and candidate revision; otherwise use its `pick_tasks` procedure.
