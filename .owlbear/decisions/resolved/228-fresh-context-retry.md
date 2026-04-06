---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Threshold of 2 failures, builder first"
notes: ""
# >> Agent metadata (do not edit)
task_id: 228
agent: researcher
created: 2026-03-30
urgency: blocking
decision_type: approach-selection
---

# Decision: What retry threshold for fresh-context delegation (Category F)?

## Context

Category F proposes delegating to a fresh-context subagent after repeated failures in the same context. The current pipeline retries at most 2 times before blocking (orchestrator convention). Context degradation is most severe after 2+ failed attempts — retry context is cluttered with error output and dead-end reasoning. See `docs/research/subagent-nesting-architecture.md` §3e. Task #228 follow-up tasks are blocked pending this decision.

## Options

### A: Threshold of 2, builder first — (rec:) recommended

- Effect: 1st failure same-context retry; 2nd failure delegates to fresh-context Fix-Attempt subagent
- Trade-off: Aligns with orchestrator's existing 2-retry convention; balances cheap retries vs fresh-context overhead
- Risk: Low — 2 retries is the proven existing pattern

### B: Threshold of 1, aggressive fresh-context — (bp:) best practice for quality

- Effect: Any failure immediately delegates to fresh context
- Trade-off: Best quality for repair attempts; highest latency overhead (subagent startup on every failure)
- Risk: May over-use fresh context for transient errors that same-context retry would fix

### C: Threshold of 3, conservative

- Effect: 3 same-context retries before delegation
- Trade-off: Minimizes subagent overhead; risks significant context exhaustion before delegation
- Risk: By 3rd retry, context may be too polluted for useful diagnosis

### D: Defer / do nothing

- Effort: 0
- Trade-off: Retries continue in same polluted context
- Risk: Ongoing quality degradation on multi-retry tasks

## Recommendation

.75 confidence — Option A. Threshold of 2 aligns with the orchestrator's established retry convention. Most transient failures resolve on first retry; persistent failures benefit from fresh context. Builder is the primary target (most failure-prone pipeline agent with edit operations). Auditor is the secondary target for future extension.

## Impact of Deferral

Fresh-context retry implementation task is blocked. Builder continues with same-context retries only. If no decision within 5 days, auto-resolve with Option A.
