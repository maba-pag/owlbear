---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: 3-tier classification with deterministic triggers"
notes: ""
# >> Agent metadata (do not edit)
task_id: 385
agent: researcher
created: 2026-03-30
urgency: blocking
decision_type: feature-gate
---

# Decision: How should research outcomes be classified for mandatory user approval?

## Context

Research findings currently bypass user decision-making. The decision-request skill is optional, triggered only for multi-option or low-confidence conclusions. Single-option research conclusions (the majority) flow directly into the pipeline without user approval. Task #385 researched this gap. See `docs/research/mandatory-user-decision-gate.md` for full analysis.

## Options

### A: 3-tier classification with deterministic triggers — (rec:) recommended

- **T1 (autonomous):** Bug fixes, refactors, config — proceed directly
- **T2 (advisory):** Approach selection with trade-offs — advisory DR, 5-day auto-timeout
- **T3 (mandatory):** New features, arch changes, security, process — blocking DR, no auto-timeout
- Triggers are factual (adds capability? changes architecture?), not judgment-based
- Effort: ~4 tasks updating 5 instruction/skill/agent files
- Risk: T3 tasks block until user decides; mitigated by planner surfacing pending decisions

### B: Mandatory DR for ALL research outcomes — (bp:) safest

- Every research doc creates a decision request regardless of impact
- Effort: ~2 tasks (simpler rules)
- Risk: High friction — trivial bug fix research would require user approval. Approval fatigue degrades the gate's value.

### C: Keep current system, lower confidence threshold to .70

- Decision request required when confidence < .70 (currently .85)
- Effort: ~1 task
- Risk: Still agent-judgment-based. Researcher can express .80 confidence about a bad direction. Doesn't address the structural gap.

### D: Defer / do nothing

- Effort: 0
- Trade-off: Research-driven features continue bypassing user oversight
- Risk: Agents autonomously determine project direction without user approval

## Recommendation

.85 confidence — Option A. Deterministic triggers prevent agent self-gating. T1/T2/T3 tiers balance safety with velocity: trivial research proceeds fast, feature-impacting research blocks for user approval. This matches the pattern used by GitHub Actions (required reviewers per environment) and Anthropic's recommendation for "programmatic checks on intermediate steps."

## Impact of Deferral

Task #385 is blocked. Four follow-up implementation tasks cannot be created until the classification system is approved. Research-driven features continue flowing through the pipeline without user oversight. No auto-resolution — this is a T3 process change that requires explicit user approval.
