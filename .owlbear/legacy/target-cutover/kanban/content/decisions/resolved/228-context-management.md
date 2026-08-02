---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "need more information"
notes: "while it is true the search/searchsubagent tool containing a codebase search subagent exists to help with context management, user is unsure if it the right agent for this specific task. searching the codebase might be especially important for the architect in order to have context available for the actual architecture task and not have the context window polluted by codebase search for context. please look at this potential agent from this pov and come again with a user-decision. propbably best to do this after Category E-sub is implemented."
# >> Agent metadata (do not edit)
task_id: 228
agent: researcher
created: 2026-03-30
urgency: advisory
decision_type: scope-decision
---

# Decision: Should we build dedicated context-management subagents (Category D)?

## Context

Category D proposes subagents for context compression (builder scaffolding delegation, large-codebase summarization, research synthesis in fresh context). The Explore agent already provides codebase summarization for the researcher. See `docs/research/subagent-nesting-architecture.md` §3b for analysis. This decision is advisory — researcher continued with recommendation.

## Options

### A: Defer — subsume into E-sub and B — (rec:) recommended

- Effort: 0 additional tasks
- Trade-off: Quality-Runner (E-sub) already reduces context pollution from test output. Parallel fan-out (B) isolates sub-tasks. Category D's unique value is small once E-sub and B are implemented.
- Risk: Builder scaffolding delegation remains unaddressed; low impact since builder rarely needs boilerplate

### B: Promote Explore to mandatory first step for builder/reviewer

- Effort: ~1 task (update agent instructions)
- Trade-off: Simple change; compresses codebase context before main work begins — (bp:) best practice
- Risk: Adds latency (Explore subagent startup) to every pipeline run

### C: Build new Context-Loader subagent

- Effort: ~2 tasks (new agent + wiring)
- Trade-off: Purpose-built for context compression; more structured output than Explore
- Risk: YAGNI — Explore may be sufficient; builds for hypothetical future needs

### D: Do nothing (keep current approach)

- Effort: 0
- Trade-off: No change; agents continue reading files directly
- Risk: None immediate

## Recommendation

.65 confidence — Option A. Category D overlaps significantly with E-sub (context pollution) and B (parallel isolation). The unique residual value (builder scaffolding, synthesis in fresh context) doesn't justify dedicated implementation until E-sub and B prove their patterns. Revisit after E-sub and B are deployed.

## Impact of Deferral

No tasks blocked. Category D can be revisited after Categories E-sub and B are implemented and evaluated.
