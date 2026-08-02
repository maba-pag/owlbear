---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Implement as designed — mandatory challenge for recommendation-bearing research"
notes: ""
# >> Agent metadata (do not edit)
task_id: 469
agent: researcher
created: 2026-03-31
urgency: blocking
decision_type: feature-gate
impact_tier: 3
---

# Decision: Expand Challenger subagent to researcher agent

## Context

Task #469 extends the Challenger adversarial subagent (implemented in #467, integrated into arch-review in #468) to the researcher agent. This is Phase 2 of the expansion path defined in `docs/research/challenger-subagent-design.md` S3h.

This is T3 because it modifies agent instructions (`researcher.agent.md`), skill pipeline behavior (`research-workflow SKILL.md`), and adds a mandatory challenge step to the research pipeline.

See `docs/research/challenger-researcher-expansion.md` for full analysis.

## Options

### A: Implement as designed — mandatory challenge for recommendation-bearing research <- (rec:) recommended

- Effort: ~1 day, 1 task (modify 2 files: researcher.agent.md, research-workflow SKILL.md)
- Trade-off: adds one Opus 4.6 call per recommendation-bearing research (~60% of research tasks); catches blind spots before recommendations cascade to downstream tasks
- Risk: false challenges on well-supported recommendations waste researcher re-evaluation time; mitigated by structured input grounding

### B: Optional-only integration — researcher chooses whether to invoke

- Effort: same as A
- Trade-off: lower cost (researcher skips when confident); but self-reflection bias (Liang et al. 2024) means skip-when-most-needed
- Risk: defeats the adversarial purpose — optional challenge gives false confidence

### C: Defer — wait for arch-review feedback first

- Effort: 0 now; revisit after 10+ arch-review challenge cycles
- Trade-off: validates the pattern before expanding; delays researcher quality improvement
- Risk: no researcher blind-spot detection until deferred; research errors continue to cascade

## Recommendation

.85 confidence — Option A. The arch-review integration (#468) establishes the template. Mandatory trigger for recommendation-bearing tasks prevents self-reflection bias. Skip trigger for trivial/info-only tasks bounds cost. One-shot design keeps per-task overhead predictable.

## Impact of Deferral

Task #469 is blocked. No auto-resolve — T3 decision requires explicit user approval. No downstream tasks depend on #469 currently.
