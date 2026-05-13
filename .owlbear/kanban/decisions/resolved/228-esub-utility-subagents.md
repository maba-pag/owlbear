---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Build Quality-Runner first, then Git-Ops, defer kanban-Writer"
notes: ""
# >> Agent metadata (do not edit)
task_id: 228
agent: researcher
created: 2026-03-30
urgency: blocking
decision_type: approach-selection
---

# Decision: Which utility subagents to build and in what order?

## Context

Category E-sub proposes three specialized utility subagents (Quality-Runner, Git-Ops, kanban-Writer) that encapsulate error-prone, context-heavy operations. Each currently handled independently by multiple pipeline agents. See `docs/research/subagent-nesting-architecture.md` for full analysis. Task #228 is blocked pending this decision.

**Cross-cutting:** Should utility subagents use inherit mode (gets ~43 tools including MCP) or assign mode (~30 tools, tighter boundary)?

## Options

### A: Build Quality-Runner first, then Git-Ops, defer kanban-Writer — (rec:) recommended

- Effort: ~3 tasks, ~2-3 sessions per subagent
- Trade-off: Quality-Runner benefits 4 pipeline agents immediately; Git-Ops addresses commit failures; kanban-Writer may be superseded by MCP kanban improvements
- Risk: Assign mode may lack a needed tool discovered during implementation
- Inherit vs assign: Assign mode for all utility subagents — tighter security, predictable toolset

### B: Build all three in parallel

- Effort: ~6 tasks simultaneously
- Trade-off: Faster completion, but higher risk of wasted effort if kanban-Writer becomes redundant
- Risk: Implementation bandwidth constraint; parallel implementation increases review burden

### C: Build Quality-Runner only, evaluate before continuing

- Effort: ~2 tasks
- Trade-off: Lowest risk; validates the pattern before investing in more subagents — (bp:) best practice
- Risk: Delays Git-Ops and kanban-Writer benefits; may lose momentum

### D: Defer / do nothing

- Effort: 0
- Trade-off: Pipeline agents continue handling pitfalls independently; context pollution persists
- Risk: Ongoing quality issues from repeated pitfall handling

## Recommendation

.90 confidence — Option A. Quality-Runner has the highest single-agent ROI (4 consumers, 10+ pitfalls encapsulated). Git-Ops addresses the second most common failure mode (commit scope violations, auto-staging trap). kanban-Writer's value may decrease as MCP kanban tools improve. Assign mode is recommended for all utility subagents — they need only 6 tools each, and inherit adds 17 unnecessary tools.

## Impact of Deferral

Task #228 follow-up implementation tasks are blocked. No downstream tasks affected until unblocked. If no decision within 5 days, auto-resolve with Option A.
