# End User Critic Debate — Pipeline Review Rethink

## Cycle 1

### Draft Position Summary

Six claims from an operator/UX perspective:

1. Batching is "strictly better" — no case where early-gating is preferable
2. AC checkpoint is the "highest-value UX improvement" in the whole proposal
3. Consolidation-test tasks must be visible and automatic
4. Iteration count / spiral detection needs proactive surfacing
5. Batch fix list improves scope awareness even when long
6. Pipeline observability should be minimal (stage, catches, iteration history, spiral flags)

### Critic Challenges (10 total, 3 critical)

**Critical challenges:**

1. **"Strictly better" overclaimed.** Archive analysis shows subtler issues emerge each round — evidence of path-dependent discovery, not withheld scope. Batching reduces round-trips but doesn't guarantee one-pass completeness. A 3x-cost comprehensive pass may be worse than an early high-signal fail when the task is clearly off track.

2. **AC checkpoint as "#1" is unsupported.** The brief foregrounds multiple pain sources (reviewer cost, test debt, tool-retry waste, proof-quality escalation). Calling the checkpoint the "highest-value" improvement isolates one cause without evidence that it's dominant.

3. **Batch list conflates blockers with adjacent work.** The brief explicitly says proof-scope creep inflates findings by mixing true blockers with quality work that should be follow-up tasks. A "complete" list is misleading if it doesn't separate these categories. The operator thinks they're seeing blockers when they're seeing mixed severity.

**Moderate challenges:**

4. Batching ignores latency — time-to-awareness matters when the task is clearly wrong
5. "Architect-approved" may be lightweight checker validation, not deep intent reinterpretation
6. "Last implementation task" is fluid — planner's task-boundary judgment is unstable per archive evidence
7. Iteration count compresses heterogeneous failure causes into one number
8. "Full picture" is overclaimed — reviewer batch can't show auditor-class defects
9. Minimal observability risks opaque labels when surfaced signals are already interpretations
10. No governing principle separates mandatory intervention from automation

### Refinements Made

1. **Dropped "strictly."** Batching is *generally* better operator UX — acknowledged latency trade-off. Added: if first finding reveals fundamental misdirection, early signal saves the user time. Position: batching is the right *default*, with a severity-escalation escape for "task is fundamentally wrong."

2. **Tempered AC checkpoint claim.** Repositioned from "highest-value" to "highest-leverage for preventing the most expensive failure mode" (intent misinterpretation → full implementation cycle wasted). Acknowledged multiple pain sources contribute; this one has disproportionate *downstream* cost, not necessarily highest frequency.

3. **Added blocker/improvement distinction to batch list.** Reviewer should categorize findings as "blocking" vs. "follow-up candidate." The operator needs scope clarity on what must be fixed NOW vs. what is quality improvement for later. This directly addresses proof-scope creep creating false urgency.

4. **Added governing principle.** User intervenes at *decision boundaries* (intent, scope, direction) and delegates within boundaries (implementation, mechanical checks). This separates the AC checkpoint (decision boundary) from consolidation-test automation (within-boundary operation) from observability (monitoring for boundary crossings).

5. **Refined architect-approved checkpoint.** The checkpoint value is not the architect's approval stamp — it's the *user seeing the AC that will drive implementation* and having a moment to correct misinterpretation. Whether architect rewrites heavily or validates lightly, the user's need is the same: see what's about to be built.

6. **Acknowledged iteration count is lossy.** Still valuable as attention trigger, but should pair with category hint (e.g., "3 cycles — proof depth" vs. "3 cycles — AC ambiguity"). Raw count alone compresses too much.

7. **Acknowledged consolidation-test timing instability.** UX requirement: the task should be visible on the board AND the user should be able to defer or retrigger it. Planner creates it at best judgment; user can override timing.

### Position After Cycle 1

Position is hardened. The core claims survive with appropriate qualification. The Critic's strongest contribution was forcing the blocker/improvement distinction in batch findings — this is a material UX design requirement I missed entirely. The governing principle (decision boundaries vs. within-boundary delegation) now provides coherence across all six claims.
