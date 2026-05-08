# Architectural Stance — Ideation UX Vocabulary Layer

## Architectural Stance

The vocabulary fix requires a **two-surface, three-tier** architecture: a primary vocabulary map in `h-ideation` for the phase agents, a lightweight companion vocabulary in `h-ideation-panel` for panelists whose output leaks through mediation's stance-reading path, and a three-tier change-isolation model (logical flow → communication structure → vocabulary/phrasing) that replaces the naive DO/SAY binary.

## Structural Reasoning

### Q1 — Vocabulary Layer Placement

**Position: Two-surface vocabulary map with single authoring point.**

The vocabulary map lives in `h-ideation` § "User-Facing Vocabulary" as the authoritative source. This covers both phase agents (discoverer, mediator) since both load `h-ideation`.

However, panelists load `h-ideation-panel`, not `h-ideation`. D7 explicitly includes "light panel cleanup" because protocol codes in panel headers leak when mediation reads stances. Therefore: `h-ideation-panel` gets a minimal "Panel Output Phrasing" section — not a full vocabulary map, but guidance for how panelists should label their own sections when writing stance files that will be surfaced to users via the Disclosure Ladder's verbatim-evidence path.

Agent persona sections get ONE critical-rule line: "Apply the user-facing vocabulary from h-ideation when communicating with the user. Internal names remain visible but always appear with their explanatory context." No duplication of mappings.

**Why not alternatives:**
- Inline in each skill file: DRY violation across 3+ files, maintenance drift guaranteed.
- Only in agent persona: wrong enforcement surface — personas define character, while agent `critical_rules` already govern communication requirements (discoverer L40, mediator L38-44). The vocabulary directive belongs in critical_rules, not persona.
- Only in h-ideation: misses the panel surface entirely. Panelist stance files are a live jargon leak path.

### Q2 — Header Design

**Position: Headers unchanged. Narration guidance uses templates for conditional steps, fixed phrases for unconditional steps.**

Step headers remain as-is: `## Step 1.5 — M3.5: Conditional Proposal Round (Design It Twice)`. They serve agent step-tracking and cross-reference grep. They are never shown directly to the user.

Below headers, add narration guidance in two forms:

- **Fixed narration** (for unconditional steps): A `**Narrate as:**` annotation with the label visible per D4.
  ```
  ## Step 1 — M3: Landscape

  **Narrate as:** "We're at the Landscape step (M3) — I'll present what exists and what's possible, then we'll figure out the way forward."
  ```

- **Narration principle** (for conditional steps where the message depends on runtime state): A `**Narration rule:**` annotation that encodes the pattern without fixing the exact words.
  ```
  ## Step 2 — Late Domain Panel Orchestration (Stance Path)

  **Narration rule:** Name each expertise area being consulted with its internal label and a parenthetical explanation. State why each lens matters for THIS specific problem. Example: "I'm consulting the architecture review (structural soundness) and data review (schema quality) because this problem has both structural boundaries and data-flow concerns."
  ```

Per D4, the label (M3, M3.5, O15) must remain visible to the user with explanatory context — never dropped silently. The annotation enforces this.

### Q3 — Narration Directive Replacements

All replacements apply D6 (keep internal names with context for attribution):

1. **"Tell the user you are switching to a proposal comparison path"** →
   "Explain that multiple viable approaches exist with no clear winner, so you're running a proposal comparison (M3.5 — the Design It Twice path) to gather distinct designs shaped by different priorities. The user will see the trade-offs side by side before choosing."

2. **"Tell the user which late-domain panelists you are invoking and why"** →
   "Name each specialist review being consulted — architecture review (structural soundness), data review (schema and validation quality), end-user review (usability and clarity), security review (trust boundaries) — and state why each is relevant to THIS problem's signal. Omit reviews that weren't selected, with a brief note explaining why."

3. **"End Phase 1 by naming @ideation-mediator"** →
   "End Phase 1 by summarizing what was discovered (1-3 sentences), then explain that a fresh synthesis session (@ideation-mediator — structured decision-support) will continue from the established findings. Provide the start command."

### Q4 — Compliance Signal Redesign

**Position: Add "Narration Principles" to h-ideation that makes the boundary explicit.**

New section content:

```markdown
## Narration Principles

- Internal verification is silent. Checklists, O15 classification steps, and tier gates
  are quality mechanisms — narrate only the RESULT ("the Critic raised a valid concern
  about X") not the mechanism ("I am now applying O15 classification").
- Labels stay visible with context (D4). When referencing an internal process, include
  the label and a parenthetical: "the Critic validation (an adversarial stress-test)."
- Attribution is by name with explanation (D6). "The architecture review (a structural
  soundness check) identified coupling between..."
- Purpose before process. For every narration, ask: "Does the user need to know WHY
  this is happening to make their decision?" If yes, explain purpose. If no, stay silent.
- The Disclosure Ladder (Default → Concrete → Verbatim) still governs how much panel
  material reaches the user. Vocabulary cleanup does not change disclosure level choices.
```

Verification checklists remain unchanged — they're the AGENT's internal quality gate. The new rule only prevents narrating them to the user.

### Q5 — Change Isolation

**Position: Three-tier change model, not binary DO/SAY.**

| Tier | What it governs | Change risk | Regression check |
|------|----------------|-------------|------------------|
| 1 — Logical flow | Step order, conditional gates, subagent dispatch, artifact writes | High | Requires full test pass |
| 2 — Communication structure | Turn types, structured headers, anchor-recall, attribution rules, disclosure level | Medium | Spot-check against h-ideation contract |
| 3 — Vocabulary/phrasing | Word choice, label explanation format, narration tone | Low | Confirm D4/D6 compliance only |

This project's changes are overwhelmingly Tier 3 (vocabulary) with THREE Tier 2 changes (the three narration directive replacements). No Tier 1 changes.

**Isolation rules:**
- Every diff must be tagged with its tier in the commit message.
- Tier 3 changes CANNOT modify numbered list items in workflow steps.
- Tier 2 changes (the three directive replacements) get before/after comparison showing the behavioral intent is preserved (same information reaches user, different words).
- The D5 before/after examples serve double duty: they're both user documentation AND regression reference for reviewers.

**Drift detection:** The `h-ideation` vocabulary map is the source of truth. Any phrasing in workflow skills or agent files that CONTRADICTS the vocabulary map is a bug. This is checkable by grep: if an internal term appears in a `**Narrate as:**` line without its D4-required context parenthetical, that's a violation.

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Two-surface vocabulary (h-ideation + h-ideation-panel) | Covers both leak paths, single authoring intent | Two files to update, not one |
| Narration templates vs. fixed phrases | Handles conditional steps without staleness | More complex guidance, agents may misapply |
| Three-tier isolation over binary DO/SAY | Honest about communication-structure being behavioral | Reviewers need to understand the tier model |
| Labels always visible (D4 strict) | User builds mental model of the process | Slightly more verbose narration |

## Warnings

1. **The Disclosure Ladder is a re-entry vector.** Even with clean phase-agent narration, verbatim panel quotes (Disclosure Ladder level 3) can reintroduce raw jargon. The `h-ideation-panel` companion vocabulary mitigates this at the source, but it's a weaker enforcement surface because panelists have less user-facing pressure.

2. **Agent critical_rules are the real enforcement surface.** Adding vocabulary guidance only to the skill file (h-ideation) without touching the agent's critical_rules section risks the agent ignoring it under pressure. The one-line critical_rule addition is load-bearing.

3. **Narration principle annotations require agent judgment.** Fixed-phrase annotations are deterministic; principle annotations depend on the agent correctly applying D4/D6 at runtime. The D5 before/after examples partially mitigate this by demonstrating the pattern concretely.

4. **Panel-side cleanup must not change panel logical behavior.** Panelist stance files have a fixed section structure (per h-ideation-panel). The "Panel Output Phrasing" guidance must only affect section LABELS and explanatory text, never the analysis content or the Critic loop protocol.

## Confidence

0.74

Revised upward from initial 0.55 after incorporating Critic challenges on scope coverage, D6 compliance, and the three-tier isolation model. Remaining uncertainty: whether "narration principle" annotations are sufficiently deterministic for real agent behavior, and whether the two-surface approach creates enough maintenance overhead to warrant a cross-reference lint.
