# Decisions

## D1 — 2026-04-20 09:15 — Project type

**Status quo:** The request is for a new export surface; nothing equivalent exists in the current ideation flow.
**Decision to make:** Is this net-new, existing-feature/refactor, or uncertain?

**Options considered:**
- A: `net-new`
- B: `existing-feature/refactor`
- C: `uncertain`

**Chosen:** A because there is no existing export surface to reshape; this is a new capability attached to the current workflow.

**Rejected:**
- B because there is no legacy export command or prompt to audit first.
- C because the current surface area is clear enough to classify without more research.

**Source inputs (when relevant):**
- User: "I need a way to get the final brief decisions back out without reopening everything."
- Research: current ideation files expose no export entrypoint.

## D2 — 2026-04-20 09:30 — Outcome boundary

**Status quo:** The request could expand into a wizard, formatter pack, and export history mechanism.
**Decision to make:** What is the smallest useful outcome for Phase 1 to hand forward?

**Options considered:**
- A: one minimal export command that reads the approved brief and decision history
- B: a multi-step export wizard with presets and formatting profiles

**Chosen:** A because it satisfies the user outcome without creating a second orchestration layer.

**Rejected:**
- B because it solves presentation breadth before proving the core export need.

**Source inputs (when relevant):**
- Simplifier: the wizard is packaging, not the need.
- First-principles: the user needs a stable artifact, not a workflow makeover.

## D3 — 2026-04-20 09:45 — Phase 1 handoff

**Status quo:** Problem, outcomes, and first-pass research are stable enough for a fresh-context mediation pass.
**Decision to make:** Should discovery continue, or should it stop and hand off?

**Options considered:**
- A: stop discovery and hand off to `@ideation-mediator`
- B: continue discovery into approach selection

**Chosen:** A because discovery already has a sharp problem, bounded outcomes, and a usable research bridge.

**Rejected:**
- B because it would blur the phase boundary and recreate the old monolithic ideator behavior.

**Source inputs (when relevant):**
- Handoff artifacts: `context.md`, `decisions.md`, `research-notes.md`
- Handoff note: start Phase 2 with `@ideation-mediator` from those three files.