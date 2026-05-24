# Architect Stance — Memory Voting: Bucket Design & Slot-Efficiency

## Architectural Stance

### Q1: TWO buckets — "Out of scope" + "In scope, didn't apply"

Two buckets. Not optional.

The distinction creates two different system responses to accumulated non-use:

1. **"Out of scope"** — The entry's domain doesn't match the current task. This is a targeting problem (scope_agents is wrong), not evidence against the entry. Score unchanged. Accumulation triggers a scope-metadata review, not a quality flag.

2. **"In scope, didn't apply"** — The entry's domain matches but it wasn't useful for this specific task. This IS weak evidence against the entry's breadth or currency. Accumulation counts toward the slot-efficiency threshold.

### Q2: BINARY threshold — block for review at ratio

Binary. One threshold, one outcome: entry pulled from rotation for human review.

The slot-efficiency rule fires when BOTH ratio conditions are met (unremarkable×10 < didnt_apply AND outstanding×10 < unremarkable) with a minimum of 10 in-scope assessments. Entry is flagged `blocked_for_review` — same state used by "factually wrong."

No gradual penalty. No score-modification side-channel.

## Structural Reasoning

### Q1 — Why two buckets is architecturally load-bearing

**The corrected direction already abandons positive-only.** The assessment system has Outstanding (+X), Unremarkable (-Y), and Factually wrong (block). "Dual-signal" — the thing the user gave up — was two TIMING points (early relevance + late value). A richer single assessment is not dual-signal.

**Different accumulation patterns demand different remedies:**
- "Out of scope" piling up → fix scope_agents targeting. The entry is fine; it's being shown to the wrong audience.
- "In scope, didn't apply" piling up → entry may be too narrow or stale for its intended audience. Flag for quality review.

Merging these into one bucket forces a choice: either treat all non-use as evidence against the entry (poisons signal with scope mismatches) or treat all non-use as a no-op (loses the quality signal entirely).

**Agent reliability is sufficient.** The scope question ("does this memory's topic area match my current task?") is pattern matching on domain, not causal diagnosis. It's no harder than distinguishing "outstanding" from "unremarkable" — which the system already requires.

**The slot-efficiency formula naturally protects rare-but-valuable entries.** An entry with even ONE "outstanding" assessment blocks the formula (outstanding×10 must be < unremarkable, which fails with any outstanding signal). Entries that occasionally shine but mostly sit idle are safe.

### Q2 — Why binary is structurally superior

**One mechanism, one tunable, one outcome.** The threshold is a governance checkpoint, not a scoring function. The entry either lives in the normal scoring system or it's escalated to a human. No interaction with bucket-based score changes.

**Gradual penalty creates two competing score-mutation paths:**
1. Bucket assessments: Outstanding +X, Unremarkable -Y
2. Slot-efficiency penalty: -Z% per ratio magnitude

These interact unpredictably. Can an entry recover from accumulated penalties via positive votes? How does -10% at 10× ratio relate to +X from "outstanding"? These questions have no natural answers because the mechanisms are incommensurable.

**Binary avoids all of this.** The entry is either in rotation (scores move via assessments only) or flagged for review (human decides: delete, refine scope, or reinstate).

**The exposure discontinuity is intentional.** Unlike a score cliff (where ranking shifts suddenly), this is a governance boundary: "the system has enough evidence that this entry doesn't justify its recall slot — human, please look." That's a feature, not a bug.

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Two buckets | Clean signal separation, different remediation paths, protects rare-value entries | One extra classification choice for agents; same-scope context variation adds noise to "in scope, didn't apply" |
| Binary threshold | Single mechanism, no score-interaction edge cases, clear governance boundary | Needs minimum assessment floor (10+); requires `blocked_for_review` state addition; review queue must stay small |

## Warnings

1. **Same-scope noise is real but mitigated.** An entry about Python testing will accumulate "in scope, didn't apply" when the agent does TypeScript work — even though both are "testing." Mitigation: the formula's conservatism (requires 10× ratios on BOTH conditions) and the minimum assessment floor (10+) mean this noise washes out over sufficient volume. It's acceptable imprecision, not architectural failure.

2. **The state model needs extension.** `blocked_for_review` doesn't exist today. But it's required by "factually wrong" regardless — both Q1's scope-review and Q2's quality-review reuse the same state with a reason enum.

3. **"Out of scope" accumulation needs a response path.** If an entry is consistently out-of-scope for the agents that see it, that's a scope_agents bug. The system should surface this pattern to humans (separate from quality review). Don't let "no-op on score" become "invisible problem."

4. **Review queue economics require conservative threshold.** Every pipeline agent votes. If the threshold is too low, the human review queue floods. The dual-condition formula with 10× ratios and 10+ assessment minimum keeps the trigger rate very low — only truly dead entries fire it.

## Confidence

0.76

Reduced from theoretical maximum by:
- Same-scope context noise is mitigated but not eliminated (-0.08)
- State model extension adds implementation surface beyond "trivial" (-0.06)
- No empirical data on agent reliability for scope classification in practice (-0.10)
| Best-effort retry semantics (may double-count). Noise in a single-user system. | Idempotency keys (add task_id tracking, separate vote log — defer to V2 if needed). |
| Reserved cold slots displace warm entries from recall. | Pure formula-based cold-start (creates chicken-and-egg with recall cap). |

## Warnings

1. **Half-life is the dominant tuning parameter.** Too short (days): everything dies between tasks. Too long (months): no differentiation. 14 days is a hypothesis, not a proof. Plan to adjust after observing real vote patterns.
2. **The first-vote jump is large.** An unvoted 3-day-old entry at confidence 0.9 scores ~0.70. After one vote it scores 1.3 (warm path, age reset). This is by design — votes should matter — but agents that vote carelessly will distort ordering. Skill instructions should guide voting hygiene.
3. **Partial failure in batch votes.** The tool must report per-entry success/failure. Callers must handle mixed results.

## Confidence

0.78
