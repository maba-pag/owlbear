# agents/

All 12 agent definitions (`.agent.md` files). This is the authoritative location
following the v2 migration. The legacy `.github/agents/` directory has been deleted.

11 pipeline stage agents (planner, orchestrator, researcher, architect, test-writer,
builder, reviewer, writer, auditor, kanban-planner, curator) + 1 analysis leaf
subagent (code-reader — read-only adversarial code analysis, dispatched by reviewer).
