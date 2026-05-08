# Synthesis — Ideation UX Vocabulary Layer

## Summary

The architect and enduser stances are strongly aligned on WHAT the fix should achieve (purpose-driven narration, labels with context, confident tone) and diverge primarily on HOW to encode it in the instruction files. The architect provides structural placement and enforcement mechanisms; the enduser provides concrete language patterns and interaction heuristics. Most tensions are complementary rather than contradictory — but the user needs to decide where the authoritative communication guidance lives and how deterministic it should be.

---

## Convergences

### C1 — Labels Stay Visible With Context (D4 strict)

Both stances agree without reservation: internal labels (M3, M3.5, O15) remain in user-facing output but always appear with explanatory context. Neither advocates hiding structure.

- architect.md §Q2: "Per D4, the label must remain visible to the user with explanatory context — never dropped silently."
- enduser.md §2: "Internal names stay visible (per D6), but the domain descriptor leads and the internal name appears as parenthetical context."

### C2 — Compliance Signal Is Explanation Quality, Not Jargon Narration

Both stances converge on the same reframe: an agent demonstrates protocol compliance by explaining purpose clearly, not by echoing internal terminology.

- architect.md §Q4: "Internal verification is silent… narrate only the RESULT, not the mechanism."
- enduser.md Key Trade-offs: "Compliance signal is 'explained the purpose clearly,' not 'named the internal components.'"

### C3 — Before/After Examples Are Non-Negotiable

Both stances treat concrete examples as load-bearing — abstract rules alone won't change agent communication style.

- architect.md §Q5: "The D5 before/after examples serve double duty: user documentation AND regression reference."
- enduser.md §4: Provides four fully worked before/after pairs with explicit reasoning.

### C4 — Attribution Pattern: Domain Label Leads, Internal Name Parenthetical

Both stances produce the same attribution shape: `"the architecture review (structural soundness)"`.

- architect.md §Q3 replacement #2: Names each specialist with parenthetical explanation.
- enduser.md §2 Stable Labels table: Same pattern — "the architecture review (checking structural soundness)."

### C5 — Panel Leakage Needs Source-Side Fix

Both agree the Disclosure Ladder's verbatim path can reintroduce jargon, and that `h-ideation-panel` needs a companion vocabulary section to address it at source.

- architect.md §Q1: "h-ideation-panel gets a minimal 'Panel Output Phrasing' section."
- enduser.md Warning #3: "Whatever labels we establish must be consistent across discovery, mediation, panel summaries, and Brief artifacts."

### C6 — Vocabulary Map Lives in `h-ideation`

Both agree the shared skill (`h-ideation`) is the primary authoring surface for vocabulary guidance.

- architect.md §Q1: "`h-ideation` § 'User-Facing Vocabulary' as the authoritative source."
- enduser.md §2: Defines stable labels table (implicitly belongs in a shared reference location).

### C7 — Transitions Cost ~15–25 Extra Words — Worth It

Both accept the verbosity trade-off for orientation.

- architect.md §Q2: Templates add per-step narration guidance.
- enduser.md §1 Trade-off: "Pay 15–25 extra words per transition for user comprehension. Worth it."

---

## Disagreements

### T1 — Embedding Mechanism: Annotations vs. Examples Section

**Architect** proposes per-step annotations (`**Narrate as:**` for fixed phrases, `**Narration rule:**` for conditional steps) embedded directly below workflow step headers. This makes guidance co-located with the logic it governs.

**Enduser** provides standalone before/after pairs and transition templates organized by situation type (M1→M2, direction change, correction). This makes guidance organized by communication need rather than pipeline step.

**Tension:** Co-location (architect) aids implementation discipline but increases skill file length. Situation-based organization (enduser) aids agent comprehension but separates communication guidance from the step that triggers it.

### T2 — Determinism of Guidance: Templates vs. Principles

**Architect** distinguishes between fixed narration (exact phrases for simple steps) and narration principles (pattern rules for conditional steps that "depend on the agent correctly applying D4/D6 at runtime"). Acknowledges this is a risk: "whether narration principle annotations are sufficiently deterministic."

**Enduser** provides concrete example phrases for all situations (including conditional ones like "when one approach dominates" vs. "when genuine alternatives exist") — effectively giving the agent multiple fixed phrases indexed by runtime state.

**Tension:** The architect's principle-based approach is more maintainable but less deterministic. The enduser's state-indexed examples are more deterministic but require more enumeration and may become stale if the pipeline adds states.

### T3 — Enforcement Surface

**Architect** identifies agent `critical_rules` as THE enforcement surface: "Adding vocabulary guidance only to the skill file without touching the agent's critical_rules section risks the agent ignoring it under pressure." Proposes a one-line critical_rule addition.

**Enduser** identifies verification criteria as the enforcement surface: "The verification criteria must shift to 'did the agent explain purpose' not 'did the agent name the component.'" This targets the reviewer/auditor layer, not the agent's own rules.

**Tension:** These are complementary (belt and suspenders) but the user needs to decide: is the primary enforcement at the agent level (critical_rule) or the review level (verification criteria), or both?

### T4 — Change Isolation Model

**Architect** introduces a three-tier change model (logical flow / communication structure / vocabulary) with commit-tagging rules and regression-check tiers.

**Enduser** does not address implementation strategy — focuses entirely on the desired user experience.

**Tension level:** Low. This is additive guidance from architect, not contradicted by enduser. User decision: is the three-tier model worth the reviewer overhead for what is primarily a Tier 3 (vocabulary) change?

### T5 — Non-Happy-Path Coverage

**Enduser** explicitly warns: "Non-happy-path communication needs the same treatment. Corrections, reruns, research gaps, and stop-and-correct cases all need purpose-framed language."

**Architect** covers three narration directive replacements, all on the happy path (proposal comparison, panel invocation, phase handoff).

**Tension level:** Medium. The architect's replacements are necessary but insufficient per the enduser's standard. The user needs to decide if non-happy-path examples are in scope for the initial implementation or deferred.

### T6 — Depth Control / Progressive Disclosure Cues

**Enduser** proposes a detailed three-layer disclosure model (Summary → Reasoning → Evidence) with specific verbal cues and anti-patterns. This is new material not addressed in the architect stance.

**Architect** references the existing Disclosure Ladder but doesn't extend or modify it.

**Tension level:** Low-to-medium. The enduser's depth-control section is additive, but its relationship to the existing Disclosure Ladder (which uses different terminology: Default → Concrete → Verbatim) needs reconciliation.

---

## Recommendation

Combine both stances: use the architect's structural placement (vocabulary map in `h-ideation`, companion in `h-ideation-panel`, one-line critical_rule) as the scaffold, and populate it with the enduser's concrete language patterns (transition examples, attribution table, before/after pairs, boundary heuristic). The state-indexed examples (enduser T2) are more practical than pure principle annotations for agent behavior change.

**Confidence: 0.72**

Remaining uncertainty is on T1 (whether annotations should be co-located with steps or in a standalone section) and T6 (whether the depth-control verbal cues need reconciliation with the existing Disclosure Ladder or can coexist).

---

## Open Questions

1. **Co-location vs. standalone section (T1)?** Should narration guidance appear as annotations below each workflow step header, or as a separate "Communication Patterns" section in `h-ideation` organized by situation type? The architect favors co-location for discipline; the enduser's material is naturally situation-organized.

2. **Non-happy-path scope (T5)?** Should corrections, reruns, and research gaps get full before/after treatment in the initial implementation, or is that a follow-up task?

3. **Depth-control cue terminology (T6)?** The enduser proposes Summary/Reasoning/Evidence layers. The existing Disclosure Ladder uses Default/Concrete/Verbatim. Are these the same concept (requiring terminology alignment) or complementary mechanisms (one for agent output, one for panel evidence)?

4. **Three-tier commit discipline (T4)?** Is the architect's Tier 1/2/3 tagging model useful implementation guidance, or overhead for a primarily-vocabulary change?

5. **Boundary heuristic placement?** The enduser's "procedural vs. direction change" heuristic (§3) is high-value. Should it live in the shared skill (`h-ideation`), in agent personas, or in both?
