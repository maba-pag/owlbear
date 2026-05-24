# Data Debate Log — Memory Voting (Forced Assessment)

## Cycle 1: Initial Position → Major Revision

### Initial Position (v1)

- **Q1:** TWO buckets. "Out of scope" is recall-targeting noise and must not contribute to slot-efficiency. "In scope but not relevant" is genuine narrowness signal. Formula should use only the latter.
- **Q2:** BINARY threshold with minimum sample size (≥10 in-scope assessments). At fixed threshold (e.g., 30×), block entry for human review.
- **Confidence:** 0.80

### Critic Challenges (Cycle 1)

Seven challenges, four critical:

1. **"Out of scope" IS entry quality signal.** If an entry keeps surfacing in wrong-domain tasks, its scope metadata may be too broad. That's an entry-quality defect, not just a recall bug. The stance treated scope-targeting as purely external to the entry.

2. **Boundary is not "manageable."** The proposed cut ("is this entry's domain the same domain as my task?") collapses hard cases. Python testing vs TypeScript testing shows same broad domain isn't enough. Cross-domain memories can be useful. Agent heterogeneity under global pooling makes consistent labeling harder.

3. **Attribution noise compounds.** The context already identifies vote quality as an active tension. Adding a WHY classification on top of a DID-YOU-USE classification multiplies the noise problem the system must survive.

4. **Binary conflicts with self-improvement goals.** The context says "even a few votes must shift the recall sequence" and curation "doesn't scale." A high-count gate reintroduces curator dependency and delays automated effect.

5. **Threshold cliff.** Research notes explicitly name this as a failure mode. The stance rejected scaled for having a cliff while proposing its own cliff.

6. **Slot waste is real.** Fixed 20-entry recall cap means off-domain entries consume scarce exposure. Treating "out of scope" as purely diagnostic ignores the opportunity cost.

7. **Premature certainty on negative-evidence scheme.** The context still lists positive-only vs positive+negative as an active tension, while the slot-efficiency formula is built on negative evidence.

### Revisions Made

Accepted challenges 1-5 fully. Revised both positions:
- Q1: ONE bucket (attribution noise, ambiguous boundary, overscoped entries should face pressure)
- Q2: SCALED with minimum-assessment floor (self-improving, no cliff, preserves information)

---

## Cycle 2: Revised Position → Final Refinement

### Revised Position (v2)

- **Q1:** ONE bucket. Reduces label noise, correctly pressures overscoped entries, formula's ratio design handles domain mismatch naturally.
- **Q2:** SCALED with minimum-assessment floor (≥N total assessments before formula fires).
- **Confidence:** 0.75

### Critic Challenges (Cycle 2)

Five critical, two moderate:

1. **Schema inconsistency.** Q1 removes the "in-scope" label, but Q2's floor requires "≥N total in-scope assessments." The gate can't be computed with the declared schema. **Resolution:** Discovered that NO FLOOR IS NEEDED — the formula's mathematical structure provides natural minimum (~12 assessments). Removed the floor entirely.

2. **Attribution noise makes "correct behavior" claim unsupported.** "Didn't use" can come from attribution error, exploration policy, recall bugs, or genuine scope defects. The stance was too confident that any specific cause was identifiable. **Resolution:** Reframed: the formula only fires at EXTREME ratios where the cause doesn't matter for the appropriate response (review the entry).

3. **Counterbalancing assumes unjustified task distribution.** Rare-domain entries could be drowned by frequent off-domain exposure. **Resolution:** Key insight that "didn't use" has ZERO direct score effect. Only the extreme-ratio safety net uses it. The counterbalancing argument was wrong to frame as score competition — it's actually about whether enough "unremarkable" counts accumulate to keep the ratio healthy.

4. **Floor is still a cliff (zero to non-zero at N).** The anti-cliff argument against binary doesn't hold if the revised approach introduces its own cliff. **Resolution:** Eliminated the floor entirely. The formula's structural properties (needs ≥1 unremarkable + ≥11 didnt_use) provide natural protection without any gate.

5. **Larger denominator ≠ better signal.** More counts with mixed causes isn't inherently better data quality. Confusing variance reduction with truthfulness. **Resolution:** Dropped the "larger denominator reduces noise" argument. Replaced with the correct framing: one bucket is justified by cognitive simplicity and the formula's high threshold making cause-distinction unnecessary, not by statistical properties of the denominator.

6. **Curator dependency moved, not removed.** Binary gates curators; scaled still requires curator parameter tuning. **Resolution:** Acknowledged as a cost. Distinguished between gating dependency (curators must act for system to function) vs. observation dependency (curators can tune parameters based on observed trends). The latter scales; the former doesn't.

7. **No treatment of historical persistence, agent heterogeneity, or edge-case math.** **Resolution:** Added explicit warnings section covering zero-division, cold-start exploration noise, and pooled scoring heterogeneity.

---

## Final Assessment

Position hardened through two Critic cycles. Key evolution:
- Q1: TWO → ONE (Critic exposed boundary ambiguity and attribution noise as critical)
- Q2: BINARY → SCALED+floor → SCALED with no floor (Critic exposed schema inconsistency and cliff hypocrisy; formula analysis revealed natural protection)

The strongest remaining argument against the stance is Critic Cycle 2 Challenge 3: rare-domain entries under pooled scoring. The mitigation (zero direct score effect + only extreme ratios trigger) is sound but depends on scope targeting working well enough that rare-domain entries still get SOME correct-domain assessments. If an entry is so narrowly useful that it NEVER gets recalled into its target context, the slot-efficiency trigger is correct behavior.

Critic confidence after Cycle 2: 0.34 (high pressure maintained). Final stance confidence: 0.78.
