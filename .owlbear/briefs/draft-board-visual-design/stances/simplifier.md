# Simplifier Stance — Board Visual Design

## Three cuts, one reframe

### 1. Drop the alias layer

Three-tier token indirection (PDS → alias → component) is YAGNI at 6 components. Use PDS tokens directly in component CSS. Introduce aliases later via find-and-replace if the component count justifies it. The existing `tokens.css` with 17 custom properties already IS the alias layer — just add a `[data-theme="dark"]` block that reassigns them.

### 2. Split dark theme

Generate the dark token file now (mechanical, trivial). But defer toggle mechanism + dark-mode verification to a follow-up. Verifying dark rendering across 6 components doubles QA surface. The toggle mechanism is its own small feature: state management, localStorage persistence, `prefers-color-scheme` media query detection.

**Ship light theme first. Dark is additive.**

### 3. Reframe "no JSX changes" → "no structural JSX changes"

The code currently uses inline `style={{}}` objects. You *must* touch JSX to:
- Add `className` props
- Remove inline style objects
- Possibly add data attributes for state-driven styling

The real constraint: no new components, no changed callbacks, no altered component hierarchy. Adding class names is hygienic, not structural.

### 4. Per-component CSS is fine

One CSS file per component (Column.css, Card.css, etc.) maps naturally to the existing code structure. A single `board.css` would become a 400-line file with unclear ownership. Per-component is simpler.

### DnD: agree with minimal styling

Questionable UX, but removing is out of scope. Style the existing data attributes passably and move on.
