---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "custom: adopt 1,2,6 unchanges, 4 customized. for details see notes"
notes: "unchanged: (1) fact schema, (2) confidence threshold gating, (6) category taxonomy. customize (4) max-capacity pruning: no actual pruning, mark for deletion and hide from output, but only user may actually delete, so they can review."
# >> Agent metadata (do not edit)
task_id: 428
agent: researcher
created: 2026-03-31
urgency: blocking
decision_type: feature-gate
impact_tier: 3
---

# Decision: Adopt deer-flow memory patterns for memory-mcp (#387)?

## Context

Task #428 analyzed deer-flow's memory subsystem in depth (see `docs/research/deer-flow-memory-subagent-deep-dive.md`). Six concrete patterns were identified as transferable to OwlBear's planned memory-mcp server (#387). These patterns shape the fact storage schema, quality filtering, and injection mechanisms — foundational design choices that affect all downstream memory-mcp work.

This is T3 because adoption adds capabilities that don't currently exist in OwlBear and shapes the architecture of the memory-mcp module.

## Options

### A: Adopt all 6 deer-flow memory patterns as design inputs for #387 ← (rec:) recommended

Patterns: (1) fact schema with id/content/category/confidence/createdAt/source, (2) confidence threshold gating (0.7 default), (3) whitespace-normalized content dedup, (4) max-capacity pruning by lowest confidence, (5) token-budgeted injection, (6) category taxonomy (preference/knowledge/context/behavior/goal).

- Effort: integrated into #387 design phase, no additional tasks
- Trade-off: deer-flow's categories may not perfectly map to OwlBear's agent-centric model (architect can adapt during #387 design)
- Risk: low — these are proven patterns, not experimental

### B: Cherry-pick core 3 patterns only (schema + confidence + dedup) — (bp:) best practice

Adopt only fact schema, confidence gating, and dedup. Design pruning, injection, and taxonomy from scratch.

- Effort: same integration effort, more design work for remaining 3
- Trade-off: more OwlBear-specific design, but reinvents solved problems
- Risk: YAGNI concern — custom designs may over-engineer what deer-flow solved simply

### C: Design memory-mcp from scratch without deer-flow patterns

Ignore deer-flow patterns entirely. Design fact storage and lifecycle independently.

- Effort: significantly more design and research time
- Trade-off: fully OwlBear-optimized, but loses prior-art validation
- Risk: violates "research before implementation" principle

### D: Defer / do nothing

- Effort: 0
- Trade-off: #387 proceeds without deer-flow input; patterns may be rediscovered later
- Risk: wasted research effort; #387 designer lacks proven reference points

## Recommendation

.82 confidence — Option A. All 6 patterns are well-proven, simple (KISS-aligned), and directly applicable. The confidence threshold gating and capacity pruning patterns are particularly valuable — they solve quality-control problems OwlBear hasn't yet addressed for memory-mcp. The architect can adapt category taxonomy during #387's design phase if OwlBear's 4D scoping model requires different categories.

The 3 not-transferable aspects (LLM auto-extraction, debounced queue, 6-section context model) are already excluded — only the applicable patterns are recommended.

## Impact of Deferral

Task #428 is blocked. This is a T3 decision — it does not auto-resolve. #387 (memory-mcp design) can proceed independently but would lack these validated design inputs. No other tasks are directly blocked.
