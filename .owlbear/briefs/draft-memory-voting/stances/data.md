# Data Quality Stance — Memory Voting (Forced Assessment)

## Q1: ONE Bucket ("Didn't use / Out of scope")

**Position:** Keep the four-bucket schema as specified in the corrected direction. Do not split "didn't use" into sub-categories.

### Reasoning

1. **"Didn't use" has zero direct score effect.** The corrected direction assigns no score movement to this bucket — entries are not penalized for non-use. The only mechanism that reads this count is the slot-efficiency safety net, which requires an EXTREME ratio before triggering. This makes the stakes of label impurity much lower than if "didn't use" directly decreased scores.

2. **The formula's structure prevents conflation harm.** Slot-efficiency requires BOTH `unremarkable × 10 < didnt_use` AND `outstanding × 10 < unremarkable`. An entry that triggers this has overwhelming non-use AND negligible positive signal. At that magnitude, the cause of non-use (scope mismatch vs. genuine narrowness) is irrelevant — the entry is consuming recall slots without producing value regardless of why.

3. **Agent attribution noise makes finer distinctions unreliable.** The context identifies "agents may not accurately attribute outcomes to specific memories" as an active tension. Asking agents to additionally classify WHY they didn't use an entry compounds the noise. One bucket = one simple judgment: "I didn't apply this."

4. **The boundary between "out of scope" and "in scope but not relevant" is genuinely ambiguous.** Python testing vs. TypeScript testing: same domain or different? Cross-domain memories can also be useful. Under global pooled scoring with heterogeneous agents, inconsistent boundary judgments produce noisy labels that look like signal.

5. **Entries that trigger slot-efficiency SHOULD face pressure regardless of cause.** If an entry's non-use is due to overscoping, scope refinement is needed. If due to narrowness, deprecation or promotion is needed. The appropriate curator response is "review this entry" in BOTH cases — the distinction doesn't change the action.

### Acknowledged Costs

- Rare-domain entries will accumulate "didn't use" from more common tasks within their scope. This is acceptable because: (a) "didn't use" carries no direct score penalty, (b) slot-efficiency's natural minimum threshold requires ~12 assessments before it can trigger, (c) even rare correct-domain tasks produce "outstanding" or "unremarkable" counts that prevent the ratio from becoming extreme unless the entry is truly ineffective.
- If an entry IS too narrowly scoped to justify a recall slot (useful in <10% of recalls with overwhelming non-use otherwise), slot-efficiency triggering is the CORRECT outcome — the entry should be reviewed for scope refinement or removal.

## Q2: SCALED Deterioration (No Artificial Floor Needed)

**Position:** Severity scales with ratio magnitude. No minimum-assessment floor is required because the formula's mathematical structure already provides natural small-sample protection.

### Natural Small-Sample Protection (Key Insight)

The formula `unremarkable × 10 < didnt_use AND outstanding × 10 < unremarkable` has an inherent minimum:
- Condition 2 requires `unremarkable ≥ 1` (otherwise `outstanding × 10 < 0` is impossible)
- Condition 1 then requires `didnt_use > unremarkable × 10 ≥ 10`
- Minimum trigger: outstanding=0, unremarkable=1, didnt_use=11 → at least **12 assessments**

No artificial floor is needed. The formula cannot fire on small samples. This is a structural property, not a tuning parameter.

### Scaling Function Properties

Once both conditions are satisfied:
- Input: the actual ratio `didnt_use / unremarkable` (always > 10 at trigger)
- Severity: proportional to how far beyond 10× the ratio extends
- Linear mapping: `penalty = base_rate × (ratio - 10)` where base_rate is the only tuning constant
- Cap: maximum penalty per assessment cycle prevents single-cycle score collapse
- Two parameters total: `base_rate` and `cap` — both observable in cockpit score trajectories

### Why Not Binary

- **No threshold cliff.** An entry at ratio 11× gets minimal deterioration; at 30× gets substantial deterioration. The signal is proportional to the evidence.
- **Self-improving.** Deterioration begins as soon as the formula's natural minimum is met (~12 assessments), without waiting for an arbitrary high-count gate.
- **No curator gating.** Binary would block entries for human review, reintroducing the scaling problem the system exists to solve. Scaled deterioration lets the system self-correct while curators observe trends at their own pace.
- **Interpretable.** Curator sees "slot-efficiency penalty: -0.03/cycle at 15× ratio" — clear causal chain from evidence to effect.

### Acknowledged Costs

- `base_rate` and `cap` have no empirical basis yet. They require tuning after deployment. Mitigation: both are single constants with observable effects in score trajectories, adjustable without schema changes.
- Scaled penalties can accumulate over many cycles. An entry that never recovers signal will slowly deteriorate to the floor. This is intended behavior — but curators should be alerted when entries approach the recall threshold (cockpit responsibility, not formula responsibility).

## Interaction Between Q1 and Q2

The decisions reinforce each other:
- One bucket means more assessments contribute to the ratio denominator, producing more stable ratios sooner
- Stable ratios mean scaled penalties are less likely to be noise-driven
- The formula's natural ~12-assessment minimum provides adequate protection without needing a separate "in-scope" label (which wouldn't exist under one bucket anyway)

## Warnings

- **NaN/zero-division:** If `unremarkable = 0`, Condition 2 is unsatisfiable and the formula never triggers. The scaling function's input (`didnt_use / unremarkable`) should still guard against division by zero explicitly in implementation — use the inequality form, not the ratio form, for the trigger check.
- **Cold-start exploration noise:** New entries intentionally surfaced broadly will accumulate "didn't use" during exploration. The ~12-assessment natural floor gives them runway, but entries with very narrow utility may trigger slot-efficiency legitimately during this period. This is acceptable — it means "this entry's scope needs refinement," which is a valid signal.
- **Pooled scoring heterogeneity:** One systematically memory-averse agent can inflate "didn't use" counts for all entries it assesses. Mitigation is outside this formula's scope (agent-level calibration or weighting), but the high ratio threshold (10×) provides natural robustness against one bad actor among many voters.

## Confidence

**0.78**
- Parameter defaults (boost=0.2, half_life=336) are reasoned but unvalidated
- Migration seeding is clean but conflates two signals (confidence ≠ usage history)
