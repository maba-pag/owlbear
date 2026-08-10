# Decisions — Proof Bundle Taxonomy

_Append-only decision log._

## D1 — 2026-05-10 — Project Type

**Status quo:** Input file proposes changes to existing pipeline skills and standards.
**Decision to make:** Is this net-new or existing-feature/refactor?
**Chosen:** existing-feature/refactor — all target artifacts already exist.
**Rejected:** net-new — no new system or package is being created.
**Source:** User confirmed.

## D3 — 2026-05-10 — Phase 2 Scope

**Status quo:** Input file proposes 4 options (A through D) with A+D hybrid recommended. Early challengers propose minimal fix (td:0 split + challenger opt-in). Discoverer analysis identifies a middle ground.
**Decision to make:** What option space should Phase 2 evaluate?

**Options considered:**
- Full range (minimal fix through full 4-axis): Too broad — minimal fix is demonstrably insufficient; full 4-axis is over-dimensioned.
- 2+2 model as leading candidate: 2 primary axes (test + proof) at task-level, with 2 derivable-with-override signals (review + challenge), plus optional bundles as architect shorthand.
- Minimal fix only: Insufficient — doesn't separate smoke from behavioral routing difference.

**Chosen:** 2+2 model as leading candidate for Phase 2 evaluation.
**Rejected:** Minimal fix alone (doesn't address smoke vs. behavioral routing); full 4-axis (over-dimensioned — review and challenge are derivable).
**Source:** User accepted discoverer recommendation.

## D4 — 2026-05-10 — Per-AC-line vs Task-level Annotation

**Status quo:** Current convention annotates each AC line with `(td:N)`. Consumers aggregate to task-level (max, any, all).
**Decision to make:** Should the new model annotate per-AC-line or per-task?
**Chosen:** Task-level annotation. Per-AC-line is architect busywork; consumers already aggregate. Test-writer can read AC text for assertion granularity.
**Rejected:** Per-AC-line annotation — creates work without routing value.
**Source:** Both challengers recommended; discoverer agreed; user confirmed as settled.

**Status quo:** Reform touches core pipeline standard and propagates to 5+ workflow skills and all agent roles.
**Decision to make:** What tier governs depth for the rest of the ideation?
**Options considered:**
- Scratch: Inappropriate — this is not throwaway.
- Tool: Insufficient — multiple downstream consumers.
- Shared: Every pipeline agent consumes the convention; durability matters; internal to workspace.
- Production: Possible but over-calibrated — not external-facing.
**Chosen:** Shared — full panel and research bridge required.
**Rejected:** Production (over-calibrated for internal-only pipeline standards).
**Source:** User confirmed.

## D5 — 2026-05-11 — Axis Structure

**Status quo:** Phase 1 leading candidate was 2+2 model (2 primary axes + 2 derivable signals).
**Decision to make:** Single axis (5-value enum) or two axes (test + proof)?
**Options considered:**
- Single axis (architect + enduser proposal): One field `proof-bundle: skip|existing|smoke|behavioral|critical` with `+challenge`/`+reader` escalation modifiers. One label = one routing row. Matches 0/10 divergence evidence. Suppression structurally impossible. Confidence: 0.75.
- Two axes (data + security proposal): `test: none|smoke|full` + `proof: none|existing|scoped|full` with derivation table. More composable but axes don't diverge in practice. Redundant assignment friction. Confidence: 0.45.
**Chosen:** Single axis — speed driver, 0/10 divergence, YAGNI for axis independence.
**Rejected:** Two axes — over-dimensioned for observed usage; override modifiers handle escalation without a permanent second axis.
**Source:** User confirmed at M4.

## D6 — 2026-05-11 — Challenger Threshold for Smoke

**Status quo:** Current td:1 (smoke equivalent) triggers challenger by default.
**Decision to make:** Should the new `smoke` bundle trigger challenger?
**Chosen:** Challenger OFF for smoke — speed win; `+challenge` modifier handles exceptions.
**Rejected:** Challenger ON for smoke — adds subagent dispatch to every smoke-level task, conflicting with the primary speed driver.
**Source:** User confirmed at M4.

## D7 — 2026-05-11 — File-Path Security Guardrail

**Status quo:** No file-path-based auto-escalation exists. Security panelist proposed it.
**Decision to make:** Adopt file-path auto-escalation or reject?
**Chosen:** Not needed — rejected entirely, not deferred.
**Rejected:** Both "adopt now" and "defer as follow-up."
**Source:** User stated "not needed" at M4.
