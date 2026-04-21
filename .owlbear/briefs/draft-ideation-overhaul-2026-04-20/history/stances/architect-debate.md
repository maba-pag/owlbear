# Architect — Critic Debate Log

## Cycle 1: Working log and panelist attention budget

**Architect position:** The working log (`working-log.md`) is a single append-only markdown file that replaces `context.md` + `decisions.md`. Per-turn sections with consistent headers. Panelists read it instead of the two separate files.

**Critic challenge:** The working log grows unboundedly. By M4-M5 it could be 200+ turns. If panelists read the full log, you've shifted the attention-budget problem from Mediator to panelists — the exact failure mechanism you're trying to fix. context.md was curated precisely because raw logs are too long.

**Architect response:** Accepted. The working log must include **moment-boundary checkpoints** — appended (not edited) summary sections at the end of each moment that snapshot the current state (problem statement, tier, outcomes, decisions so far). Panelists scan to the latest `## Checkpoint — End of M{x}` header. They read the checkpoint (~50 lines) not the full log. Append-only property is preserved because checkpoints are new appended content, not edits to earlier sections.

**Resolution:** Position refined. Checkpoints are the retrieval mechanism.

---

## Cycle 2: Phasing — does Brief A even need to be a Brief?

**Architect position:** Two Briefs — Brief A (quick wins: F1, F2), Brief B (structural overhaul).

**Critic challenge:** Brief A is a glob pattern change and a contradiction deletion. That's a 30-minute PR with clear acceptance criteria. Wrapping it in a Brief adds overhead to a trivial change. Is this decision-laundering through process?

**Architect response:** Accepted. Brief A is over-engineered. The F1/F2 fixes should ship as a Sprint-tier kanban task with clear AC — not a Brief. The real Brief is the structural overhaul (Studio-tier). The Sprint task ships first as pre-flight cleanup.

**Resolution:** Phase 1 becomes a Sprint task. Phase 2 is the sole Brief.

---

## Cycle 3: Idea panel and pragmatist synthesis

**Architect position:** The idea panel (First-Principles, Simplifier, Outsider) invokes ideation-pragmatist for synthesis, same as domain panelists.

**Critic challenge:** The idea panel challenges the problem/outcomes — it's adversarial questioning, not domain expertise. The pragmatist's convergence/divergence/recommendation format is designed for domain stances. "Three agents converge that your problem is wrong" isn't useful synthesis. The pragmatist would be shoehorned into a shape that doesn't fit.

**Architect response:** Accepted. The idea-panel agents produce short, focused challenge documents — not lengthy domain analyses. The Mediator reads 3 idea-panel stances directly (~1-2 pages each) and presents them as numbered challenges to the user. This is a justified exception to "Mediator reads only summaries" because: (a) challenge documents are inherently compact, (b) there's no meaningful convergence/divergence to synthesize, (c) the Mediator's job at end of M2 is to present challenges, not resolve them.

The pragmatist is reserved for domain-panel synthesis (M3→M4) where 4+ overlapping domain analyses need consolidation.

**Resolution:** Position revised. Idea panel bypasses pragmatist. Mediator reads idea stances directly.

---

## Cycle 4: O14 drift check — discretionary protocol again?

**Architect position:** Drift check every 3 turns within a moment. Mediator appends a drift-check line to the working log. Protocol rule in w-ideation.

**Critic challenge:** This is discretionary protocol — the exact failure mechanism #1 from the root cause. "Must check every 3 turns" is a rule that depends on the Mediator remembering. By M4 the Mediator won't remember, because that's literally the problem diagnosis. How is this different from "ad-hoc Critic checks are may-not-must"?

**Architect response:** Partially accepted. The drift check IS discretionary — there's no way around that without hooks, which the design principle forbids. But it's a different quality of discretionary than the current system:

1. **One rule in one file** vs. rules scattered across 6 files. Attention-budget cost to remember is lower.
2. **Self-evident in the log** — the working log has sequential turn numbers per moment. If you see Turn 7 under M2 with no drift check, the absence is visible to anyone reading the log (user, auditor, future Mediator re-entry). Current system has no such trail.
3. **User can trigger it** — "where are we?" prompts the Mediator to produce a drift check. This is the ultimate fallback.

The honest assessment: drift checks reduce drift *visibility*, not drift itself. The drift still happens; the user just sees it sooner. That's the best we can do without hooks.

**Resolution:** Position held with added warning about the fundamental limitation.

---

## Cycle 5: Working log replacing decisions.md for downstream

**Architect position:** decisions.md disappears. Decisions are inline in the working log. brief.md is synthesized from the working log.

**Critic challenge:** Domain panelists currently read `context.md` + `decisions.md`. If decisions.md disappears, where do panelists find prior decisions? The checkpoint includes the decision state, but checkpoints grow over time. By M4, the latest checkpoint could be substantial — problem + tier + outcomes + landscape + multiple decisions.

**Architect response:** This is manageable. The checkpoint is a structured summary, not a narrative. Even with all M1-M3 state, a checkpoint is ~80-120 lines — comparable to the current context.md + decisions.md combined (~80-150 lines). The attention cost doesn't increase; it consolidates.

The real win: one read instead of two. The panelist opens one file, scans to the last checkpoint, and has everything. Currently they open two files and cross-reference.

**Resolution:** Position held. Checkpoint size is comparable to current multi-file total.

---

## Summary of Critic Impact

| Cycle | Challenge | Outcome |
|-------|-----------|---------|
| 1 | Panelist attention on unbounded log | **Accepted** — added checkpoint mechanism |
| 2 | Brief A is over-engineered | **Accepted** — downgraded to Sprint task |
| 3 | Pragmatist doesn't fit idea-panel shape | **Accepted** — Mediator reads idea stances directly |
| 4 | Drift check is discretionary | **Partially accepted** — held position, added honest warning |
| 5 | Checkpoint size for downstream | **Rejected** — size is comparable to current multi-file total |
