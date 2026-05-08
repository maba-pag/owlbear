# Architect Debate Log

## Critic Cycle 1

### Initial Position Summary

1. Single vocabulary map in `h-ideation` as sole source of truth.
2. Headers unchanged; `**Narrate as:**` fixed annotations below each step header.
3. Three narration directive replacements that describe purpose/expertise areas without internal names.
4. Silent verification + "Narration Principles" section.
5. Binary DO/SAY separation: numbered items = behavior, annotations = phrasing only.

### Critic Challenges (7 total: 3 critical, 4 moderate)

**Challenge 1 (critical): Single vocabulary map doesn't cover panel instruction surface.**
Panelists load `h-ideation-panel`, not `h-ideation`. D7 includes panel-header cleanup. The position called one file "single source" while the locked scope spans two instruction surfaces.

**Assessment: VALID.** I missed that panelist stance output is a live jargon leak path (mediation reads stances → surfaces to user via Disclosure Ladder). Fix: two-surface vocabulary with `h-ideation` as authoritative source and `h-ideation-panel` getting a minimal companion section.

**Challenge 2 (critical): Attribution rewrite conflicts with D6.**
Position §3 replaced "which late-domain panelists you are invoking" with "which expertise areas you're consulting" — removing named internal entities in favor of abstract lenses. D6 locks "keep internal names with context."

**Assessment: VALID.** My directive replacement dropped the internal names entirely. D6 is explicit: names stay, context added. Fix: revised directives now name the reviews AND provide the parenthetical explanation.

**Challenge 3 (moderate): Header strategy drifts toward hidden labels (conflicts D4).**
The M3.5 `Narrate as` example explained purpose but dropped the label. D4 chose "labels visible with context."

**Assessment: VALID.** My example was "There are multiple viable approaches..." with no mention of M3.5. Per D4, the label must appear. Fix: all annotations now include the label with context.

**Challenge 4 (moderate): Static Narrate-as annotations are brittle for conditional steps.**
Step 2 narration depends on which panelists are selected (varies by problem signal). A fixed sentence under the header can't capture this variability.

**Assessment: PARTIALLY VALID.** True for conditional steps (Step 2 roster varies). Not true for unconditional steps (M3 always happens the same way). Fix: two annotation types — fixed narration for unconditional steps, narration principles for conditional steps.

**Challenge 5 (critical): DO/SAY separation doesn't hold — communication shape IS behavioral.**
Structured context headers, anchor-recall, attribution, and Disclosure Ladder are all "how you communicate" AND "what you do." Wording changes can change what evidence the user sees.

**Assessment: PARTIALLY VALID.** The binary is too crude. Communication structure (turn types, headers, disclosure levels) is genuinely behavioral. But vocabulary choice within an established communication structure is genuinely safe. Fix: three-tier model (logical flow → communication structure → vocabulary/phrasing) with different risk levels and review requirements for each.

**Challenge 6 (moderate): Enforcement surface misidentified — critical_rules already govern communication.**
The position dismissed agent files as "wrong layer" but both agents hard-code communication requirements in critical_rules, not persona. The vocabulary directive needs to live in critical_rules.

**Assessment: VALID.** I was wrong to say "persona section" — the real enforcement surface for communication behavior is `critical_rules`. Fix: the vocabulary directive goes in critical_rules as one line, not in persona.

**Challenge 7 (moderate): Problem framing too narrow — issue is routing announcements, not just terminology.**
The position frames it as a vocabulary problem, but the actual instructions explicitly tell agents to announce routing events. That's a structural communication pattern, not just word choice.

**Assessment: PARTIALLY VALID.** The three directive replacements DO address this, but I under-weighted them. They're Tier 2 (communication structure) changes, not Tier 3 (vocabulary). Fix: explicit tier classification in the isolation model acknowledges the directive replacements are a higher-risk change category.

### Position Updates

| Aspect | Before | After |
|--------|--------|-------|
| Vocabulary surface | One file (h-ideation) | Two files (h-ideation + h-ideation-panel companion) |
| Attribution in directives | Abstract expertise areas only | Named reviews with parenthetical explanations |
| Label visibility in annotations | Purpose-only (label dropped) | Label + context per D4 |
| Annotation type | All fixed-phrase | Fixed-phrase (unconditional) + principle (conditional) |
| Isolation model | Binary DO/SAY | Three-tier (logical → structural → vocabulary) |
| Enforcement surface | Persona section | Agent critical_rules (one-line directive) |
| Directive replacements | Classified as vocabulary | Classified as Tier 2 communication-structure changes |

### Confidence Movement

- Initial: 0.55
- Post-Critic: 0.74

The Critic surfaced genuine gaps in scope coverage (panel surface), D4/D6 compliance (label dropping, name removal), and isolation model realism (binary too crude). All materially improved the position. Remaining uncertainty: conditional narration principles are less deterministic than fixed phrases, creating a softer enforcement surface for runtime behavior.
