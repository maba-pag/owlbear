# End-User Debate Log — Memory Voting (Forced Assessment)

## Critic Cycle 1

### Draft Position (pre-Critic)

**Q1: TWO buckets** — "Wrong topic" + "Right topic, didn't apply"
- Boundary is clear: "Should this have been recalled given my task?" is yes/no
- Five categories don't create decision fatigue (map to natural cognitive groups)
- Single bucket becomes lazy default; splitting forces a cognitive checkpoint
- Split provides curation intelligence: "wrong topic" signals scope misconfiguration
- Both sub-buckets have no score effect, so split is purely about signal quality

**Q2: BINARY threshold block**
- Scaled penalty is invisible to the human (can't predict when entry disappears)
- Binary creates clear curation event with clear call-to-action
- Aligns with "factually wrong" (both are threshold-based blocks)
- Respects human time: event-driven, not dashboard-monitoring
- Human curation should be inbox-of-items, not continuous score monitoring

Confidence: 0.72

### Critic Challenges (Cycle 1)

| # | Severity | Challenge | Impact |
|---|----------|-----------|--------|
| 1 | Critical | Boundary is retrospective — "should this have been recalled?" invites outcome bias. Python-vs-TypeScript proves easy case only; multi-domain tasks make boundary ambiguous. | Acknowledged but reframed |
| 2 | Critical | Diagnostic value overstated — "wrong topic" signal could mean scope issues, ranking bias, broad text, stale framing, or agent misread. Bundled symptom, not clean signal. | Partially conceded |
| 3 | Critical | Five categories overlap — "used-fine," "right topic didn't apply," and "unremarkable" are degree-of-usefulness, not kind. 20× forced after task = fatigue. | Strong challenge, revisited |
| 4 | Moderate | Splitting two no-consequence buckets doesn't eliminate laziness — just arbitrary splitting. No consequence for getting it wrong. | Valid — weakens split argument |
| 5 | Critical | Pre-threshold invisibility — weak memories occupy slots before binary block fires. Operator sees nothing while efficiency is harmed. | Reframed in Cycle 2 |
| 6 | Moderate | Factual wrongness ≠ utility failure — collapsing into one mental model hides meaningful distinction. | Accepted — refined language |
| 7 | Moderate | Cliff effects — binary can dump batch of blocks after long silence. Delayed + concentrated cost. | Acknowledged, added mitigation |

---

## Critic Cycle 2

### Revised Position (post-Cycle 1)

**Q1: Still TWO** — reframed as "Reasonable recall" vs "Mismatched recall"
- Less outcome-biased: "Was this a reasonable recall?" rather than "wrong topic"
- Boundary approximate for multi-domain tasks; signal value is aggregate, not per-instance
- "Applied" = behavioral change; resolves overlap with Unremarkable
- Both sub-buckets still no score effect; only consumer is aggregate reporting
- Approach is falsifiable: if agents split randomly with no pattern, collapse back to one

**Q2: Still BINARY** — reframed as circuit breaker
- Gradual scoring already exists via assessment effects (Outstanding adds, Unremarkable subtracts)
- Binary block is separate concern: entries that get repeated "didn't use" with no score movement
- Circuit breaker for entries that resist gradual demotion
- Pre-threshold continuation is correct: entry deserves fair trial
- Threshold is parameterizable and simpler to tune than continuous curve

Confidence: 0.65

### Critic Challenges (Cycle 2)

| # | Severity | Challenge | Impact |
|---|----------|-----------|--------|
| 1 | Critical | "Reasonable" is still subjective and retrospective. "Did this change behavior?" requires causal attribution, not simple observation. Brief itself says end-of-task attribution is guesswork. | Fatal to Q1 two-bucket position |
| 2 | Critical | "Mismatched recall" is bundled symptom — doesn't provide clean curation signal. Global pooling can't distinguish same-scope context mismatch from targeting failure. | Fatal to Q1 diagnostic value claim |
| 3 | Critical | Systematic bias, not random noise. Task-mix bias is correlated — valid Python memory during TypeScript weeks accumulates misleading "mismatched" votes that amplify rather than cancel. | Fatal to Q1 aggregate-washout argument |
| 4 | Critical | "Didn't use" path still has no gradient, then suddenly blocks. Research-notes flags threshold systems as having artificial cliffs. | Acknowledged but reframed |
| 5 | Critical | Circuit breaker overclaims statistical confidence. Observations aren't independent — clustered task mix produces correlated assessments. No time decay means temporal clustering can push threshold unfairly. | Addressed with "block is reversible + human sees context" |
| 6 | Critical | 20-item retrospective reconstruction underplayed. Forced assessment of all 20 requires retrospective reconstruction, not in-the-moment reactions. Must be lightweight. | Incorporated into final warnings |

### Blind Spots Surfaced
- Independence of evidence: correlated observations not acknowledged
- Confirmatory-memory case: "skimmed for reassurance" breaks "applied" discriminator
- Two-bucket aggregate legibility to human curator never established
- Identity continuity: agent must carry memory IDs through task execution

---

## Resolution

### Q1: Position CHANGED — TWO → ONE

The Critic successfully demonstrated across two cycles that:
1. No formulation of the boundary ("wrong topic," "reasonable recall," "mismatched") is consistently applicable by agents in retrospective forced assessment
2. Aggregate signal is corrupted by systematic task-mix bias, not corrected by it
3. The diagnostic value for human curation is unreliable because multiple causes collapse into one label
4. Five categories × 20 items at end-of-task adds cognitive cost for zero reliable signal (both sub-buckets have no score effect)

The lazy-default concern is better addressed by making Outstanding compelling and Unremarkable clearly behavioral ("I applied this"), rather than subdividing the neutral category.

### Q2: Position HELD — BINARY

The Critic's strongest challenge (clustered task-mix pushing threshold unfairly) actually strengthens the case for binary: the block creates a human decision moment for exactly the ambiguous cases where algorithmic judgment would be wrong. Scaled degradation handles these cases silently and incorrectly. The binary block respects the human as the authority.

The "circuit breaker" framing survived: gradual scoring handles entries that get Unremarkable assessments; binary block catches entries stuck in the "didn't use" zero-effect path indefinitely.

Final confidence: 0.74
