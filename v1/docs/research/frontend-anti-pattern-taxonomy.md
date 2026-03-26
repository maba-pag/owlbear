# Frontend Anti-Pattern Taxonomy Research

> **Owning task:** #938 â€” Add OwlBear frontend anti-pattern taxonomy
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #938 asks for a reusable anti-pattern reference under
`.github/skills/frontend-design/` that separates universal blockers (hard
gates) from taste-specific heuristics (AI-slop signatures). The parent
research (#929, `docs/research/impeccable-design-skills.md`) identified the
split but deferred the detailed taxonomy to this task. The key question:
what structure, content, and integration approach best serves OwlBear's
skill system without turning taste into hard law?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | pbakaus/impeccable `SKILL.md` | .95 | DO/DON'T catalog across 7 categories plus "AI Slop Test" section [S1] |
| S2 | WCAG 2.1 SC 2.4.7 / 2.2 SC 2.4.13 (Focus Visible/Appearance) | .90 | Formal criteria for focus indicator size, contrast, and visibility [S2] |
| S3 | WCAG 2.1 SC 1.4.3 / 1.4.11 (Contrast Minimum / Non-text Contrast) | .90 | 4.5:1 body text, 3:1 large text and UI components [S3] |
| S4 | WCAG 2.1 SC 2.5.5 (Target Size) | .85 | 44Ã—44px minimum interactive target [S4] |
| S5 | NNGroup "Placeholders in Form Fields Are Harmful" (Sherwin, 2014/2018) | .90 | 7 usability harms of placeholder-as-label, a11y failures [S5] |
| S6 | WCAG 2.1 SC 3.3.2 (Labels or Instructions) | .85 | Programmatic label requirement for form inputs [S6] |
| S7 | OwlBear `docs/research/impeccable-design-skills.md` Â§5 | .95 | Prior blocker/taste split with initial item lists [S7] |
| S8 | Anthropic `skills/frontend-design/SKILL.md` | .80 | Broad anti-pattern warnings and design-thinking framing [S8] |
| S9 | OwlBear `.github/skills/frontend-design/SKILL.md` | .95 | Current 9-item Universal Blockers list and workflow step 5 [S9] |

## 3. Structure Analysis

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| A. Expand SKILL.md inline | No new file | Bloats always-loaded context; mixes quick-check with deep examples | Reject |
| B. Add `references/anti-patterns.md` | Progressive loading; matches existing 7-file pattern; testable | One more file to maintain; needs SKILL.md table update | **Adopt (.90)** |
| C. Separate `docs/` document only | Out of skill, no auto-load | Not discoverable from the skill workflow | Reject |

Option B integrates cleanly: the reference table in SKILL.md gets one new
row, `_EXPECTED_REFERENCE_FILES` in tests gets one new entry, and the
existing 9-item quick-check in SKILL.md stays compact [S1, S9].

## 4. Content Design

### Universal Blockers (hard gates)

These map directly to WCAG SC or documented usability research. Each item
has a formal backing:

| Blocker | WCAG/Source | Why it's a hard gate |
|---------|-------------|---------------------|
| No visible focus replacement | SC 2.4.7, 2.4.13 [S2] | Keyboard users cannot navigate |
| Placeholder as label | SC 3.3.2 [S6], NNGroup [S5] | Disappears on input; fails a11y |
| Hover-only critical actions | SC 2.1.1 [S2], SC 2.5.5 [S4] | Touch/keyboard users excluded |
| Contrast below AA | SC 1.4.3, 1.4.11 [S3] | Low-vision users cannot read |
| Touch targets < 44Ã—44px | SC 2.5.5 [S4] | Motor-impaired users misfire |
| Critical actions hidden on mobile | SC 1.3.4 [S3] | Orientation/viewport exclusion |
| No reduced-motion fallback | SC 2.3.3 [S2] | Vestibular disorder harm |
| Ambiguous primary labels | NNGroup UX writing [S5], Impeccable [S1] | Cognitive load, error risk |
| Generic error messages | SC 3.3.1, 3.3.3 [S6], NNGroup [S5] | No user-actionable path |

These 9 items are already in OwlBear's SKILL.md [S9]. The reference file
expands each with a one-line rationale and WCAG citation.

### Taste Heuristics (AI-slop signatures)

Impeccable [S1] catalogs ~20 DON'T items we classify as taste-specific.
These should be illustrative warnings, not bans:

| Category | Examples (not exhaustive) | Source |
|----------|--------------------------|--------|
| Typography | Defaulting to Inter/system-ui; monospace as "tech" shorthand | S1, S7 |
| Color | Purple/cyan AI palette; gradient text for impact; pure #000/#fff | S1, S7 |
| Layout | Cards-in-cards; identical card grids; hero-metric template; center-everything | S1, S7 |
| Visual | Glassmorphism; decorative sparklines; generic drop shadows; rounded-rect-with-border | S1, S7 |
| Motion | Bounce/elastic easing as default | S1, S7 |

The reference file frames these as "signals that an AI generated this" with
the instruction to flag them as suggestions, not laws [S1, S7, S9].

## 5. Integration Approach

1. **New file:** `references/anti-patterns.md` with two sections (Blockers,
   Taste Heuristics), attribution header linking to NOTICE.md.
2. **SKILL.md update:** Add row to reference table; keep existing 9-item
   blocker checklist intact; update workflow step 3 to reference the file.
3. **Test update:** Add `"anti-patterns.md"` to `_EXPECTED_REFERENCE_FILES`
   in `tests/test_frontend_design_skill.py`.

## 6. Recommendation (.90 confidence)

Create `references/anti-patterns.md` as a two-tier reference: universal
blockers (with WCAG citations) above taste heuristics (illustrative, not
absolute). Update SKILL.md to reference it and update tests to expect it.
This matches the existing reference-pack pattern, keeps SKILL.md lean, and
satisfies all five AC items [S1, S2, S3, S4, S5, S6, S7, S8, S9].

Risk: file adds ~100â€“120 lines to the skill package. Mitigation: it's
progressive-loaded only when anti-pattern checking is relevant, so it does
not inflate baseline context.

## 7. Follow-up Tasks

1. **Add RED tests for anti-pattern taxonomy reference** â€” Create failing
   tests that assert `references/anti-patterns.md` exists, is referenced in
   SKILL.md, contains both tiers, and cites prior art.
2. **Create anti-pattern taxonomy reference file** â€” Implement
   `references/anti-patterns.md` with universal blockers (WCAG-backed) and
   taste heuristics (illustrative). Update SKILL.md reference table and
   tests.
