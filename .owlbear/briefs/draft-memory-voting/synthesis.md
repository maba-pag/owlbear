# Synthesis — Memory Voting: Bucket Design & Slot-Efficiency

## Summary

The panel addressed two specific design questions for the forced-assessment memory voting system. Strong convergence emerged on both:

1. **Q1 (One or two "didn't use" buckets):** 3-of-4 panelists favor ONE bucket. Only Architect advocates two.
2. **Q2 (Scaled or binary slot-efficiency):** 3-of-4 panelists favor BINARY threshold with human review. Only Data advocates scaled deterioration.

Both convergences are reinforced by different reasoning paths arriving at the same conclusion — not mere majority voting.

## Convergences

### Q1: One bucket — shared reasoning threads

- **Agent attribution is unreliable at the scope boundary.** Data, End-user, and Security all identify that classifying "was this entry in-scope for my task?" is genuinely ambiguous (Python testing during TypeScript work; tangential API touches). The Critic challenge on inter-agent agreement was persuasive.
- **"Didn't use" has no direct score effect.** The only consumer of this count is the slot-efficiency formula, which requires extreme ratios (10×) before triggering. Label impurity at lower magnitudes is irrelevant.
- **Both sub-buckets lead to the same action.** Whether non-use is caused by scope mismatch or genuine narrowness, the appropriate response is "review this entry." The diagnostic distinction is better made by the human at review time (with full task context) than by the agent at assessment time (under retrospective compression).

### Q2: Binary threshold — shared reasoning threads

- **Gradual scoring already exists through bucket assessments.** Outstanding +X, Unremarkable -Y provide continuous score movement. Slot-efficiency deterioration addresses a different problem: entries that accumulate only "didn't use" and resist gradual demotion because they're never actually applied.
- **Human as authority.** Binary block creates a clear governance checkpoint. The human sees evidence, understands context, and decides. Scaled penalties make invisible, irreversible changes without human oversight.
- **Blast-radius control.** Binary limits the damage from classification noise to a single event (reviewable, reversible). Scaled penalties compound noise directionally over time.

## Divergence Matrix

| Decision Point | Architect | Data | End-user | Security | Tension Level |
|---|---|---|---|---|---|
| Q1: Bucket count | TWO (out-of-scope + in-scope-didn't-apply) | ONE | ONE | ONE | Low — clear 3:1 |
| Q1: Rationale basis | Different remediation paths (scope fix vs. quality review) | Formula structure makes distinction moot | Boundary is ambiguous; behavioral framing preferred | Fewer exploit surfaces; unreliable classification | Low — minority position is coherent but outweighed |
| Q2: Deterioration model | BINARY (block for review) | SCALED (proportional penalty, `base_rate × (ratio - 10)`) | BINARY (circuit breaker for non-assessable entries) | BINARY (no automated changes from aggregate signals) | Low — clear 3:1 |
| Q2: What "gradual" means | Gradual penalty creates two competing score-mutation paths — incommensurable | Gradual IS the mechanism; binary reintroduces human-gating the system exists to avoid | Gradual scoring already exists via bucket assessments; binary solves a different problem | Gradual compounds classification noise directionally | Medium — Data's "self-correcting without curator gating" argument has merit |
| Minimum assessment floor | 10+ assessments (explicit parameter) | Not needed — formula's structure provides natural ~12 minimum | 10 assessments (explicit, conservative) | Start conservative, tighten based on signal quality | None — all agree ~10-12 minimum; Data shows this is inherent to the formula |
| "Unremarkable" gaming surface | Not addressed | Not addressed | Acknowledged (framing fix: "I applied or referenced this") | Primary concern — agents dump unused entries as Unremarkable to avoid slot-efficiency | Medium — Security identifies a real bypass path others don't address |

## Expectation Fit

The corrected direction (forced assessment buckets replacing time-based decay) preserves the user's stated expectations:

| User expectation | How the converged position delivers |
|---|---|
| Self-improving: useful memories rise, unhelpful sink | Outstanding +X raises score; Unremarkable -Y erodes score; binary block catches entries that resist demotion |
| No human intervention at scale | Assessment is forced (no opt-out); score movement is automatic from bucket effects; human intervenes ONLY at block threshold — rare, event-driven |
| New entries get fair trial | Cold-start entries accumulate assessments; formula cannot fire below ~12 assessments; entries with even one Outstanding are protected |
| Voting signal gives humans clarity | Block event + assessment history gives clear "why" signal; cockpit surfaces trend data before threshold fires |
| Lightweight for agents | End-of-task retrospective bucketing of 20 entries; one behavioral question per entry ("did you apply this?") |

**Key improvement over time-based decay:** No half-life tuning, no age-based score collapse during idle periods, no "everything dies between tasks" failure mode. Score movement is evidence-driven, not clock-driven.

## Open Questions

1. **"Unremarkable" as escape hatch.** Security identifies that agents can mark genuinely unused entries as "Unremarkable" (incurring tiny -Y) to avoid slot-efficiency accumulation. Is self-correction via accumulated -Y sufficient, or does this need an additional guardrail (e.g., monitor Unremarkable:Outstanding ratio per agent)?

2. **Below-cap invisibility.** Security and the formula structure both surface this: entries ranked below the recall cap of 20 produce NO assessment signal. Once pushed below, they cannot recover. Should 1-2 recall slots be reserved for random sampling below the cap?

3. **Threshold parameterization.** All panelists agree on ~10-12 minimum assessments before the slot-efficiency rule can fire. But the exact trigger ratio (10× "didn't use" to "unremarkable" AND 10× "unremarkable" to "outstanding") needs validation. Is the dual-condition formula conservative enough, or too conservative?

4. **`blocked_for_review` state.** Architect notes this state doesn't exist today but is needed regardless (for "factually wrong"). Confirm: single new state with a reason enum (`slot_efficiency | factually_wrong | scope_review`)?

5. **Confirmatory memory classification.** End-user raises: an entry read for reassurance but not directly applied — Unremarkable or Didn't-use? The instruction framing ("Did this inform your work, even as a sanity check?") determines which bucket captures this. Needs explicit guidance in the skill prompt.

## Recommendation

**Q1: ONE bucket for "didn't use."** The convergence is strong (3:1), the reasoning is multi-dimensional, and the minority position's key benefit (different remediation paths) is achievable at the human-review layer without burdening agents with an unreliable classification.

**Q2: BINARY threshold with human review.** The convergence is strong (3:1), and the dissenting position (scaled deterioration) solves a problem that's already addressed by the existing bucket-based score movement. The binary block serves as a circuit breaker for the specific failure mode that continuous scoring cannot reach: entries that accumulate only "didn't use" and never get rated Unremarkable or Outstanding.

**Confidence: 0.82**

High because: both convergences are 3:1 with independent reasoning paths; the corrected direction (forced assessment) eliminates the prior panel's dominant concern (vote compliance); the positions are mutually reinforcing (one bucket feeds cleaner data to the binary threshold).

Reduced from maximum because: the "Unremarkable" gaming surface (Security) is a real bypass that no converged position directly addresses; below-cap invisibility has no solution in the current design; threshold parameterization is unvalidated.
