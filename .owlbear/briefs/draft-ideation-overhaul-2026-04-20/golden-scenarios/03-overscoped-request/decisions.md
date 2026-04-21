# Decisions

## D1 — 2026-04-20 14:05 — Project type

**Status quo:** The request mixes net-new and refactor elements and is still too broad to classify cleanly at first glance.
**Decision to make:** Is the work net-new, existing-feature/refactor, or uncertain?

**Options considered:**
- A: `uncertain`
- B: `net-new`
- C: `existing-feature/refactor`

**Chosen:** A because the scope combines multiple problem types and needs reduction before a sharper classification can hold.

**Rejected:**
- B because at least part of the request reshapes existing surfaces.
- C because part of the request also invents new surfaces that do not yet exist.

**Source inputs (when relevant):**
- User: "I want the full cockpit, docs rewrite, and memory dashboard cleaned up together."
- Discovery read: the ask mixes three different problem frames.

## D2 — 2026-04-20 14:30 — Early simplification before Phase 2

**Status quo:** Carrying the full bundle into Phase 2 would make the approach discussion noisy and misleading.
**Decision to make:** Should Phase 1 preserve the mega-request, or reduce and split it before handoff?

**Options considered:**
- A: keep one mega-brief and let Phase 2 sort it out
- B: split the work into ideation workflow, docs currency, and cockpit/dashboard follow-up tracks

**Chosen:** B because the early challenge lane showed the current bundle hides multiple unrelated problem spaces.

**Rejected:**
- A because it would defer the actual simplification work until after solution framing had already started.

**Source inputs (when relevant):**
- Simplifier: the current ask contains at least three separable deliverables.
- First-principles: only the ideation workflow problem is mature enough for this brief.
- Outsider: a single mega-brief optimizes for local convenience, not decision quality.

## D3 — 2026-04-20 14:45 — Phase 1 handoff

**Status quo:** The overscoped request has been reduced to a bounded ideation-workflow problem with supporting research.
**Decision to make:** Is the reduced scope stable enough for mediation?

**Options considered:**
- A: hand off now to `@ideation-mediator`
- B: keep collecting more discovery detail on the split-out tracks

**Chosen:** A because the current brief only needs the ideation-workflow track; the other tracks can be follow-up work.

**Rejected:**
- B because it would keep discovery attached to work that has already been intentionally excluded.

**Source inputs (when relevant):**
- Handoff artifacts: `context.md`, `decisions.md`, `research-notes.md`, `synthesis-idea-panel.md`
- Handoff note: Phase 2 starts with `@ideation-mediator` from those files.

## D4 — 2026-04-20 15:25 — O15 critic validation on phased rollout

**Status quo:** The current Phase 2 position recommends a phased rollout limited to the ideation workflow track.
**Decision to make:** How should the Critic findings change the recommendation?

**Options considered:**
- A: accept all Critic findings and reopen the whole scope
- B: classify findings with O15, keep material ones explicit, group minor ones, reject nonsense
- C: ignore the Critic because the request was already reduced once

**Chosen:** B because the Critic is useful pressure, but not every objection deserves equal weight.

**Rejected:**
- A because it would erase the Phase 1 scope reduction and reintroduce the mega-brief.
- C because one material finding remained real and needed a direct response.

**Source inputs (when relevant):**
- Critic: questioned whether docs and cockpit work were still smuggled into the rollout plan.
- Synthesis: the current recommendation stays valid if the rollout language is kept narrow.

**Material findings:**
- The recommendation still implied adjacent docs work was part of the same rollout. The phrasing had to be narrowed so the ideation workflow remained the only in-scope track.

**Minor findings (grouped):**
- clarify that later cockpit work is follow-up, not hidden scope
- make the post-handoff validation note shorter

**Nonsense findings:**
- reopen every split-out track before approving the ideation workflow brief