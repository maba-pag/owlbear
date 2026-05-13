# First-Principles Stance — Board Visual Design

## Challenges (ranked by impact)

### 1. "No JSX changes" is self-defeating (confidence: 0.88)

`Card.tsx` has 16 lines of inline styles with conditional logic. You cannot move them to CSS without selector hooks. Targeting `data-testid` couples styling to test infrastructure. `className` additions are not structural changes — they're hygienic prerequisites for CSS to work at all.

**Reframe:** "No structural JSX changes" (no new components, no callback changes, no hierarchy changes). Adding `className` and removing inline styles is the work, not a boundary violation.

### 2. "Automatic inheritance" conflates two claims (confidence: 0.85)

- Theme switching via tokens IS automatic (change the attribute, colors swap). ✓
- Future component styling is NOT automatic and never will be. Each new component still needs its own CSS. ✗

The word "automatically" over-promises. Honest version: "future features get a proven token palette and established CSS conventions to follow."

### 3. The alias layer is the existing token file (confidence: 0.82)

`tokens.css` already defines 17 overridable CSS custom properties on `:root`. Adding `[data-theme="dark"] { ... }` that reassigns those same properties IS the alias layer. The brief's framing smuggles in a second semantic tier (board-level aliases like `--board-surface`) that isn't earned at this scale.

**Simpler:** Extend `tokens.css` with dark overrides. Use the existing custom properties directly.

### 4. "Finished product" vs "usable and coherent" (confidence: 0.76)

These are different quality bars with a 3-5× effort gap:
- **Usable and coherent:** Surfaces, spacing, typography, basic states. Board is clearly structured and readable.
- **Finished product:** Pixel-perfect hover transitions, empty-state illustrations, badge polish, responsive breakpoint tuning, accessibility audit...

The brief straddles both without committing. The minimum viable win should be "usable and coherent" and the stretch goal is "finished product."

### 5. Both themes together bundles a feature with the fix (confidence: 0.72)

The irreducible problem: the board is invisible in light theme. That's the pain.
Dark theme is an additive feature. Shipping both in one brief:
- Doubles QA surface
- Delays pain relief
- Introduces a toggle mechanism (UI + state + persistence)

Counter-argument: if the token architecture is correct, dark is near-free. The QA cost is what's not free.

### 6. PDS suitability: already settled

The codebase already uses PDS components (`PButton`, `PSelect`, `PMultiSelect`) and PDS tokens. This is not a design-system choice — it's already made. Not worth re-evaluating.
