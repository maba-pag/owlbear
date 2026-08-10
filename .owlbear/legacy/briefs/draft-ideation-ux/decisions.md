# Ideation UX — Decisions

## Project Type

Confirmed: existing-feature/refactor

## Investment Tier

Confirmed: Shared

Rationale: this affects every user who interacts with ideation agents — the fix shapes the user experience for all future ideation sessions.

## D1: Outcome Count

- **Chosen:** 3 outcomes (A: purpose-driven communication, B: oriented transitions, C: direct tone)
- Rejected: 5 outcomes (over-decomposed — five observations of one behavior, per both challengers)
- Rejected: 2 outcomes (user chose to keep tone separate as explicit outcome)

## D2: Root Cause Framing

- **Chosen:** Vocabulary starvation + compliance signaling (both challengers converged)
- Rejected: "Instruction parroting" (agents don't copy text mechanically — they reach for the only vocabulary available)
- Rejected: "Structural complexity" (first-principles challenged this but architecture is sound; problem is presentation, not structure)

## D3: Scope

- **Chosen:** Primarily communication + targeted turn-shape modifications
- Rejected: Communication-only (understates change — some turn-shape guidance in workflow skills requires modification)
- Rejected: Full structural redesign (architecture is sound, problem is presentation)

## D4: Label Visibility

- **Chosen:** Labels visible with context ("Moment 2: Outcomes — the problem is clear, now we define success")
- Rejected: Hide all labels (user explicitly said "exposing internal structure is fine, give it context")
- Rejected: Labels without context (current state — the problem we're fixing)

## D5: Before/After Examples

- **Chosen:** Include 3-4 concrete before/after pairs in the shared skill section (both challengers agreed abstract rules don't change style behavior)
- Not a decision with alternatives — both challengers agreed this is non-negotiable

## D6 — 2026-05-08 — Attribution Model (Q3)

**Status quo:** Mediator says "the architect panelist found X" or "I consulted ideation-security" — exposes internal agent names.
**Decision to make:** How should the mediator attribute insights from domain perspectives?

**Options considered:**

- A: Domain labels ("from an architecture perspective") — natural but loses agent identity
- B: Challenge framing ("we stress-tested for...") — purpose-driven but vaguer
- C: No explicit attribution — cleanest but loses transparency
- D: Keep internal names with context ("the architecture review (a structural soundness check) found...")

**Chosen:** D — keep internal names with context. User values transparency and consistently prefers "expose structure with explanation" over abstraction. Aligns with D4.

**Rejected:**

- A because user explicitly prefers seeing the internal structure rather than abstracting it away
- B because attribution becomes too vague to be useful
- C because it violates the mediator's transparency mandate

## D7 — 2026-05-08 — Subagent Scope (Q6)

**Status quo:** All agent files (user-facing and panel-facing) use internal protocol codes without alternatives.
**Decision to make:** Should the fix touch only user-facing agents, or also clean up panel output?

**Options considered:**

- A: User-facing agents only (discoverer, mediator, workflow skills)
- B: User-facing + light panel cleanup (also remove protocol codes from panel stance headers)
- C: Full rewrite of all agent personas

**Chosen:** B — user-facing + light panel cleanup. Primary fix in mediator/discoverer, plus replace protocol codes in panel stance headers with descriptive names. Low extra cost, prevents accidental jargon leakage.

**Rejected:**

- A because protocol codes in panel headers can leak when mediator reads stances
- C because panel agents are internal-facing by design; full rewrite is over-engineering

## D8 — 2026-05-08 — Narration Guidance Placement (Synthesis T1)

**Chosen:** Hybrid — co-located `**Narrate as:**` annotations for the 3 critical directives (F2 narration instructions), standalone "Communication Patterns" section in h-ideation for general patterns (transitions, attribution, depth cues).

**Rejected:**

- Pure co-location because it inflates every step header in both workflow skills
- Pure standalone because the 3 worst offenders benefit from in-place fix co-located with the logic

## D9 — 2026-05-08 — Non-Happy-Path Scope (Synthesis T5)

**Chosen:** Include now — corrections, reruns, and conditional-skip cases get before/after treatment in the initial implementation (2-3 additional pairs).

**Rejected:**

- Defer because the user's M3.5 frustration was partially a non-happy-path case; shipping without it leaves the most visible symptom untreated.

## D10 — 2026-05-08 — Depth-Control Terminology (Synthesis T6)

**Chosen:** Align with existing Disclosure Ladder (Default/Concrete/Verbatim). Add verbal cues for how agents signal each level to users.

**Rejected:**

- Replace with Summary/Reasoning/Evidence because it creates a terminology split with existing w-ideation-mediation instructions.

## D11 — 2026-05-08 — Commit Isolation Model (Synthesis T4)

**Chosen:** Skip three-tier model. Note the 3 directive replacements as "behavioral-equivalent rewrites" in the Brief.

**Rejected:**

- Three-tier model because the change is overwhelmingly vocabulary; the model adds reviewer overhead for minimal risk reduction.

## D12 — 2026-05-08 — Boundary Heuristic Placement (Synthesis T5 related)

**Chosen:** In h-ideation (shared skill). The procedural/direction/depth-change boundary heuristic lives in the shared skill accessible to both agents.

**Rejected:**

- Per-agent personas because both agents need the same heuristic and it's a communication rule, not a persona trait.
