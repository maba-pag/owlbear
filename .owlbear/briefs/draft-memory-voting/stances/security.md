# Security Stance — Memory Voting (Forced Assessment)

## Security Stance

### Q1: One bucket for "didn't use" — but the real surface is elsewhere

**Position:** ONE bucket. The "didn't use / out of scope" distinction is a classification the agent cannot reliably make under end-of-task retrospective compression, and splitting it creates no actionable differentiation for the scoring mechanism.

**Critical finding:** The two-bucket split is NOT the primary security surface of this design. The more dangerous boundaries are:

1. **"Unremarkable" as a dump for non-use.** An agent avoiding slot-efficiency triggers can mark genuinely unused entries as "Unremarkable" instead. This gets a tiny -Y penalty but doesn't count toward the "didn't use" aggregate. Self-correcting over time (repeated -Y accumulates), but slower than the slot-efficiency rule.

2. **"Factually wrong → blocked" is the highest-authority action.** A single misclassification here removes an entry from future recall entirely (pending human review). This is appropriate IF AND ONLY IF "blocked" always gates on human confirmation before permanent effect. The design states "immediately blocked for human review" — correct instinct. This must remain a human gate, never automated.

**Why one bucket is still preferred:**
- Agent classification of "in scope" vs "out of scope" is unreliable at end-of-task (retrospective compression under limited model memory)
- If both sub-buckets count identically for slot-efficiency, the split provides observability but adds classification noise — net value is marginal
- If sub-buckets are treated differently (out-of-scope exempt from slot-efficiency), that creates an unverifiable escape hatch — a subjective claim that shields entries from system governance
- Fewer inter-bucket boundaries = fewer exploit surfaces for systematic classification bias
- Diagnostic question ("why unused?") is better answered at the review layer where human has full task context, not at the agent-classification layer where attribution is already lossy

**Acknowledged trade-off:** One bucket loses diagnostic signal that could help distinguish retrieval-targeting failures from memory-quality failures. This is real but should be addressed by surfacing entry content + task metadata during review, not by asking agents to make a distinction they're unreliable at.

### Q2: Binary threshold with human review — no automated deterioration from aggregate signals

**Position:** BINARY trigger for human review. No scaled automated penalty.

**What I'm actually defending:** No automated score changes based on indirect aggregate signals. All slot-efficiency-driven score changes require human mediation.

**Why binary trigger:**
1. Slot-efficiency is an aggregate pattern (ratio of used vs. unused across tasks). Automated penalties on *individual entries* based on aggregate patterns are a category error — you cannot attribute the aggregate to any specific entry without human judgment.
2. The recall cap of 20 entries means anything outside the cap produces NO assessment signal. Ranking integrity above the cap is therefore load-bearing. Automated adjustments to ranking based on noisy within-cap signals could push valuable entries outside the cap permanently — with no mechanism to detect the error.
3. Scaled penalties create a continuous destruction mechanism that compounds with classification noise. Each misclassification is individually tiny but collectively directional. Binary + human review bounds the blast radius.
4. The human reviewer has information agents lack: their own authoring intent, project phase awareness, domain knowledge about which memories *should* be relevant. This isn't "human as oracle" — it's human as an orthogonal verification layer with access to different context.

**Trend data for the reviewer:** The threshold trigger should surface context to the human (chronic non-use counts, which entries are repeatedly unused, trend direction). This is scaled *visibility*, not scaled *automation* — the human retains the decision. The Critic correctly notes this creates governance pressure before the threshold fires; that is acceptable because the pressure operates on a *human making a decision*, not on an automated mechanism.

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| "Unremarkable" used as dump for genuinely unused entries | Medium | Self-correcting via accumulated -Y; monitor ratio of Unremarkable:Outstanding across agents |
| "Factually wrong" misclassification removes valid entry | High | Already human-gated ("blocked for review"); ensure no path bypasses this gate |
| Entries outside recall cap never receive assessment signal | Medium | Inherent to forced-assessment design; mitigate by occasionally randomizing 1-2 recall slots |
| Slot-efficiency threshold set too sensitive → review fatigue | Medium | Start conservative (high threshold); tighten based on observed signal quality |
| Agent classification noise at end-of-task | Medium | Inherent; compensated by volume (many assessments over time smooth noise) |
| Inflated "Outstanding" distorts ranking upward | Medium | Monitor Outstanding frequency per agent; flag if rate exceeds expectation |

## Compliance Implications

None specific. Single-user laptop system in a single trust domain. No PII in memory entries (they contain agent operational knowledge). No external data flow. Standard data-at-rest practices apply to the memory store but are not changed by this design.

## Least-Privilege Recommendations

1. **"Factually wrong" must remain human-gated.** No automated path from agent classification to permanent entry removal or score zeroing.
2. **Slot-efficiency deterioration must be human-gated.** No automated score changes based on aggregate non-use patterns.
3. **Assessment writes are append-only.** Agents can submit bucket assignments but cannot modify previous assessments or see other agents' assessments for the same task.
4. **No assessment of entries the agent didn't receive.** The forced-assessment contract covers only the 20 recalled entries. Agents cannot volunteer assessments of entries they weren't shown (prevents targeted manipulation).

## Warnings

1. **The "Unremarkable" boundary is the real gaming surface**, not the "didn't use" split. Monitor cross-bucket ratios.
2. **Recall cap creates an observation horizon.** Entries below rank 20 are invisible to the governance system. If ranking drift pushes a valuable entry below the cap, it becomes permanently unassessable. Consider reserving 1-2 recall slots for random sampling below the cap.
3. **"Factually wrong" is nuclear.** In a system where all agents are same-trust, this bucket should require HIGH confidence from the agent (maybe explicitly gated: "are you certain this is factually incorrect, not merely irrelevant?"). A misclassification here is the highest-cost error in the system.

## Confidence

0.80

Higher than initial (0.65) due to Critic refinement. The Q1 and Q2 positions are defensible. Remaining uncertainty is around whether the acknowledged trade-offs (lost diagnostic signal from one bucket, governance pressure from trend visibility) have second-order effects I haven't modeled.
