# Decisions

## D1 — 2026-04-20 11:10 — Project type

**Status quo:** The request is to restructure an existing ideation workflow that already ships in the repo.
**Decision to make:** Is the work net-new, existing-feature/refactor, or uncertain?

**Options considered:**
- A: `existing-feature/refactor`
- B: `net-new`
- C: `uncertain`

**Chosen:** A because the work is directly reshaping the current ideation entrypoint and supporting files.

**Rejected:**
- B because the current ideation flow already exists and is the thing being changed.
- C because the current codebase makes the brownfield nature explicit.

**Source inputs (when relevant):**
- Existing files: `share/agents/ideator.agent.md`, `share/skills/w-ideation/SKILL.md`
- User: "This is the same ideation system, but the phases need to be genuinely separate."

## D2 — 2026-04-20 11:35 — Phase split shape

**Status quo:** The current entrypoint mixes discovery, synthesis, and handoff inside one voice.
**Decision to make:** Should the redesign keep one user-facing agent with hidden modes, or split the phases visibly?

**Options considered:**
- A: explicit `ideation-discoverer` and `ideation-mediator`, with `ideator` as a router
- B: keep one visible ideator and switch modes internally

**Chosen:** A because the handoff needs to be visible to the user and restart cleanly from the blackboard artifacts.

**Rejected:**
- B because it preserves the old ambiguity about when discovery actually ends.

**Source inputs (when relevant):**
- Research: the old surface collapsed freeform discovery into later structured choice work.
- Panel synthesis: a visible phase boundary reduces instruction load and user confusion.

## D3 — 2026-04-20 11:55 — Phase 1 handoff

**Status quo:** Discovery has locked the problem, outcomes, and first-pass research.
**Decision to make:** Is discovery complete enough for a fresh-context Phase 2 start?

**Options considered:**
- A: hand off now to `@ideation-mediator`
- B: continue discovery until the approach is already chosen

**Chosen:** A because `context.md`, `decisions.md`, and `research-notes.md` are strong enough to support a fresh-context mediation pass.

**Rejected:**
- B because it would keep approach choice inside discovery and erase the point of the split.

**Source inputs (when relevant):**
- Handoff artifacts: `context.md`, `decisions.md`, `research-notes.md`
- Handoff note: Phase 2 starts from those files in a fresh context.

## D4 — 2026-04-20 12:25 — Phase 2 recommendation

**Status quo:** Phase 2 started from the handoff artifacts and produced a late-panel synthesis.
**Decision to make:** Which migration path should be recommended to the user?

**Options considered:**
- A: split the workflow into discoverer and mediator, keep `ideator` as a thin router
- B: keep one visible ideator and add more internal rules

**Chosen:** A because the synthesis showed convergence around explicit phase ownership, thinner instruction surfaces, and cleaner handoff behavior.

**Rejected:**
- B because it keeps the old mental model while only moving text around.

**Source inputs (when relevant):**
- Late-panel synthesis: `synthesis.md`
- User-facing outcome: phase split should be visible and restartable.

## D5 — 2026-04-20 12:40 — Qualitative review

**Status quo:** One full end-to-end scenario now exists from discovery through brief drafting.
**Decision to make:** Is the artifact trail clear enough for a human reviewer to follow without replaying the whole chat?

**Options considered:**
- A: yes, with the current handoff and synthesis shape
- B: no, more narrative carry-over is needed in `context.md`

**Chosen:** A because the handoff is explicit, `context.md` stays narrow, and `decisions.md` preserves the real choices.

**Rejected:**
- B because adding more narrative history would bloat the blackboard and make subagent reads worse.

**Source inputs (when relevant):**
- Human review note: clarity good, drift low, live runtime behavior still unproven.