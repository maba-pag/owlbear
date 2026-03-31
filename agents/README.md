# agents/

All 13 agent definitions (`.agent.md` files). This is the authoritative location
following the v2 migration. The legacy `.github/agents/` directory has been deleted.

11 pipeline stage agents (planner, orchestrator, researcher, architect, test-writer,
builder, reviewer, writer, auditor, kanban-planner, curator) + 2 leaf subagents:
- code-reader — read-only adversarial code analysis, dispatched by reviewer
- challenger — adversarial pre-decision verdict challenger, dispatched by pipeline agents before committing to a verdict
