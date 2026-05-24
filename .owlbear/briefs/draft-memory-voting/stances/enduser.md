# End-User Stance — Memory Voting (Forced Assessment)

## User Experience Stance

### Q1: ONE bucket for "didn't use"

The "didn't use" category should remain a single bucket. Splitting into "out of scope" and "in scope but not relevant" adds cognitive cost for unreliable signal.

### Q2: BINARY threshold block for slot-efficiency

Slot-efficiency deterioration should trigger a binary block for human review, not a scaled penalty. The gradual scoring already exists through the assessment buckets themselves (Outstanding adds, Unremarkable subtracts). The binary block is a circuit breaker for entries that resist gradual demotion.

## Usability Reasoning

### Q1: Why ONE bucket

**The lazy-default concern is real but misdiagnosed.** The user's intuition — that one "didn't use" bucket becomes the path of least resistance — correctly identifies a risk. But the fix isn't to split the neutral bucket. It's to make the positive signal (Outstanding) easy and compelling to assign. The system extracts value from the RARE positive votes and the gradual erosion from Unremarkable. "Didn't use" being the largest bucket is expected and correct for a 20-item forced assessment.

**The boundary cannot be consistently applied.** "Was this a reasonable recall for this task?" sounds clear until you encounter real cases: a Python testing memory during a task that starts as TypeScript but touches Python CI config mid-run. A memory about API conventions during a refactoring that touches the API layer tangentially. Agents will categorize these inconsistently — not from laziness, but from genuine ambiguity.

**Systematic bias corrupts the aggregate signal.** Even if individual miscategorizations were random noise, they'd wash out. But task-mix bias is correlated: a valid Python memory during a TypeScript-heavy week accumulates systematic "wrong topic" votes that amplify bias rather than cancelling it. The human curator receives a misleading "targeting is broken" signal when in fact the entry is fine and the task mix is temporary.

**Both sub-buckets have no score effect.** If neither bucket changes the score, the only consumer is aggregate reporting for human curation. But the Critic correctly challenged whether that reporting is reliable enough to be actionable. The answer is no — too many confounds (scope issues, ranking bias, text quality, agent misread, task drift) collapse into one label.

**Four buckets are sufficient.** Outstanding, Unremarkable, Didn't use, Factually wrong. These map to natural cognitive reactions:
- "This was great" → Outstanding
- "I used this, it was fine" → Unremarkable
- "Didn't apply" → Didn't use
- "This is wrong" → Factually wrong

The boundaries are behavioral (did you apply it?) not evaluative (was it good?). This is the same framing principle from the prior stance — "which did you use?" is observable; "was this appropriately recalled?" is speculation.

### Q2: Why BINARY

**Gradual scoring already exists.** The assessment buckets provide continuous score movement: Outstanding adds, Unremarkable subtracts slightly. An entry that never gets Outstanding slowly sinks via Unremarkable decrements. That IS the scaled mechanism. It's already built into the bucket effects.

**The binary block solves a different problem.** Some entries get "didn't use" repeatedly — which has zero score effect by design. These entries resist gradual demotion because they're never rated Unremarkable (the agent didn't apply them, so they can't honestly say "I used this, it was fine"). Without the binary block, these entries persist indefinitely in recall slots, never scoring badly but never contributing.

**The binary block creates a clear curation event.** When it fires, the human sees: "This entry was assessed 15 times and never rated Outstanding or Unremarkable — only 'Didn't use'. It's not earning its slot." This is:
- Clear (one sentence explains the problem)
- Actionable (keep/edit/delete/fix targeting)
- Event-driven (human acts on flags, not dashboards)

**Scaled penalty is invisible.** A continuous degradation formula that the human can't observe, predict, or understand is worse than nothing. It creates a system where entries silently disappear without the human ever knowing why or having a chance to intervene. The binary block respects the human as the authority.

**The task-mix clustering problem argues FOR binary, not against it.** The Critic raised: "A Python memory during a TypeScript-heavy week hits threshold unfairly." But this is exactly when the human SHOULD be involved. They see the evidence, understand the context, and can say "unblock — targeting needs refinement." Scaled degradation would handle this case silently and incorrectly, permanently demoting a valid entry without human oversight.

## Key Trade-offs

| Accepted | Why |
|----------|-----|
| ONE neutral bucket loses curation signal about recall targeting | Signal was unreliable anyway; scope_agents and human review are better tools for targeting fixes |
| "Didn't use" is the largest bucket by design | System signal comes from the rare positive (Outstanding) and slight negative (Unremarkable) — not from the neutral mass |
| Binary block has a cliff effect | Cliff is acceptable because it's a HUMAN decision point, not an automated penalty. Late arrival is better than silent demotion |
| Pre-threshold slot waste continues | Correct behavior — entry deserves fair trial. Statistical confidence requires sufficient assessments before concluding "not useful" |

| Risk | Mitigation |
|------|-----------|
| Agents dump everything into "Didn't use" without thought | Make Outstanding compelling ("name what was great"); make Unremarkable require active claim of application; Didn't use is genuinely the residual |
| Binary threshold fires unfairly during task-mix clusters | Block is reversible; show assessment history with context; human can unblock immediately |
| Bursty operator load when multiple entries hit threshold simultaneously | Rate-limit surfacing (show N per curation session); oldest blocks first |
| Confirmatory memories can't be bucketed cleanly (read, got reassurance, but didn't "apply") | Classify as Unremarkable — skimming for confirmation IS using the memory. Instruction framing: "Did this inform your work, even as a sanity check?" |

## Warnings

1. **Do not add a fifth bucket unless empirical data shows agents can categorize consistently.** The two-bucket "didn't use" split is falsifiable — if implemented, measure inter-agent agreement on the boundary. But start with four.
2. **Frame the Unremarkable bucket as "I applied or referenced this" not "it was mediocre."** The distinction between Unremarkable and Didn't-use is behavioral (applied vs. didn't), not qualitative (good vs. meh). Get the prompt framing right.
3. **Binary block must show assessment history.** When the block fires, the human needs to see WHICH tasks triggered the "didn't use" assessments — this is how they distinguish "genuinely useless" from "task-mix mismatch."
4. **Set the threshold conservatively.** Better to block too late (entry wastes some slots) than too early (valid entry blocked after unlucky task run). Suggest: minimum 10 assessments AND useful-ratio below 10% before block triggers.
5. **Make Outstanding the easiest bucket to assign.** If the system's primary signal is positive votes, the UX of giving a positive vote must be frictionless. Consider: "Star any entries that were genuinely great" as the FIRST question, before bucketing the rest.

## Confidence

**0.74**

Higher than prior stance (0.71) because: (a) forced assessment eliminates the vote-compliance risk entirely — every recalled entry gets assessed, no opt-out; (b) removing time-based decay simplifies the mental model for both agents and humans; (c) the binary block creates a clear, human-respecting curation moment rather than invisible algorithmic decisions.

Not higher because: (a) 20-item retrospective bucketing at end-of-task is still a cognitive load concern — attribution quality depends on how carefully agents do this; (b) the "Unremarkable vs. Didn't use" boundary for confirmatory memories remains genuinely fuzzy; (c) threshold parameterization (how many assessments, what ratio) will determine whether blocks fire fairly or create noise.
