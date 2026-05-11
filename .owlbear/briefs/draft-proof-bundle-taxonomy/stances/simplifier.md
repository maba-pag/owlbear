# Simplifier Stance — Proof Bundle Taxonomy

## Key Tensions

1. **The td:0 overload is already patched, not broken.** The `Existing proof required: {scope}` escape hatch in `w-arch-review` Step 2.1 already distinguishes "no proof" from "existing proof required." The fix is ugly free-text, but the actual failure mode it addresses—reviewer treating td:0 as "skip all proof"—is explicitly handled in `w-code-review` (line 88). The problem is documentation clarity, not missing routing.

2. **"Five downstream decisions" overstates coupling.** The framing claims td:N controls five things independently. In reality it controls two decisions with three threshold levels:
   - **Create tests?** (test-writer: td:0 → skip, td:1+ → write)
   - **How deep is review?** (reviewer: td:0 → lint+named-proof, td:1 → scoped tests, td:2 → tests+coverage+code-reader)
   
   Challenger dispatch and code-reader dispatch aren't separate axes — they're thresholds on the same ordinal. Challenger fires at td:1+. Code-reader fires at td:2. That's ordinal behavior working correctly.

3. **The multi-axis model (Option A) replaces one read site per consumer with N read sites per consumer.** Currently `w-code-review` does one lookup: "what's the max td:N?" Under axes, reviewer must read proof-axis, review-axis, challenge-axis independently. Each consumer gains parse complexity. This is a net negative for pipeline speed.

## Simplification Opportunities

### Cut 1: Formalize the existing td:0 split — nothing more

The minimum viable outcome is achievable by promoting `Existing proof required: {scope}` from free-text to a first-class marker:

- `(td:0)` — no tests, no proof, lint only
- `(td:0 proof:{scope})` — no new tests, but named existing proof required

This is a one-line grammar extension to the architect skill, a clause update in reviewer, and zero schema changes. All other td:N behavior stays.

**Files touched: 2** (`w-arch-review/SKILL.md`, `w-code-review/SKILL.md`).

### Cut 2: Defer all axis decomposition to a follow-up

Option A's modular axes and Option D's named bundles both solve a problem that hasn't been demonstrated: "the ordinal makes wrong routing decisions for td:1 and td:2." No evidence is presented that td:1 tasks get over-reviewed or td:2 tasks get under-challenged. The current ordinal is tight and correct for those levels.

If axis decomposition is needed later, it can be added without breaking Cut 1's grammar.

### Cut 3: Kill the named-bundles UX layer entirely

Named bundles ("inspect", "smoke", "matrix") add a lookup indirection for something that's currently a single integer. Architects already know what 0/1/2 mean. Adding names doesn't speed up dispatch — it adds a mapping table that every consumer must import. This is negative value.

## Risks of Over-Engineering

- **Migration cost is non-trivial.** Every archived task in the kanban has `(td:N)` annotations. A taxonomy change either requires migrating them (waste) or maintaining backwards compatibility (the thing the proposal says it won't do).
- **Axis independence is a fiction.** In practice, test-creation depth and proof-execution depth are correlated >95% of the time. Giving architects four knobs to turn means four degrees of freedom to misconfigure, with almost no cases where the axes actually diverge.
- **Pipeline speed goal is undermined.** The stated driver is reducing subagent overhead. Adding more parse logic, more routing tables, and a bundle-to-axes resolution layer moves in the opposite direction.

## Simplest Viable Path

**Do Cut 1 only.** Formalize `(td:0 proof:{scope})` as a structured marker. Update two skill files. Done.

If pipeline throughput is the real goal, the higher-leverage change is making challenger and code-reader dispatch faster or conditional on task risk signals (e.g., files-changed count, security-tagged), not restructuring the proof taxonomy.

## Confidence

**0.85** — High confidence that Cut 1 alone resolves the stated minimum viable outcome. Moderate confidence that the full taxonomy (Options A/D) is premature without evidence of td:1/td:2 misrouting.
