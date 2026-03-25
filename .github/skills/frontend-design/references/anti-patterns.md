# Anti-Patterns Reference

> OwlBear adaptation - see `../NOTICE.md` for full attribution.
> Structure and examples adapted from Impeccable and Anthropic.

## Universal Blockers

These are hard blockers. If any item below is present, treat the design as not
ready to ship.

- **No visible focus replacement when native outline is removed** - Citation:
  WCAG 2.1 SC 2.4.7 (Focus Visible) and WCAG 2.2 SC 2.4.13 (Focus Appearance).
  Rationale: keyboard users lose track of where focus is.
- **Placeholder text used as a form label** - Citation: WCAG 2.1 SC 3.3.2
  (Labels or Instructions), NNGroup research on placeholder usability.
  Rationale: the label disappears while typing and breaks comprehension.
- **Critical actions accessible only on hover** - Citation: WCAG 2.1 SC 2.1.1
  (Keyboard). Rationale: hover-only UI excludes keyboard and touch users.
- **Text or UI contrast below AA thresholds** - Citation: WCAG 2.1 SC 1.4.3
  (Contrast Minimum) and SC 1.4.11 (Non-text Contrast).
  Rationale: low-vision users cannot reliably read or identify controls.
- **Touch targets below 44x44 pixels** - Citation: WCAG 2.1 SC 2.5.5
  (Target Size). Rationale: small targets increase tap error rates.
- **Critical actions hidden on mobile viewports** - Citation: WCAG 2.1
  SC 1.3.4 (Orientation) and SC 1.4.10 (Reflow).
  Rationale: users lose core actions on small screens.
- **No reduced-motion fallback for animations** - Citation: WCAG 2.1
  SC 2.3.3 (Animation from Interactions). Rationale: motion can trigger
  vestibular discomfort.
- **Ambiguous primary action labels** - Citation: NNGroup usability guidance
  on explicit labels, plus Impeccable content conventions.
  Rationale: vague label text raises decision friction and user error.
- **Generic error messages with no next step** - Citation: WCAG 2.1
  SC 3.3.1 (Error Identification) and SC 3.3.3 (Error Suggestion).
  Rationale: users cannot recover without specific guidance.

## Taste Heuristics

These are warning signals, not bans. Use them to flag likely AI-slop output,
then decide with product context, audience, and brand tone.

### Typography

- Defaulting to generic font stacks with no typographic hierarchy.
- Using one-size text everywhere so headings and body copy collapse together.

### Color

- Repeating high-saturation color gradients as decoration with no semantic role.
- Relying on pure black/white extremes for most surfaces and text.

### Layout

- Card-in-card UI with identical card shapes and no content hierarchy.
- Grid layouts that prioritize symmetry over task flow and scanning order.

### Visual

- Glassmorphism or heavy shadow effects used as default styling.
- Decorative visuals that add noise but no informational value.

### Motion

- Bounce-heavy animation or exaggerated easing for routine state changes.
- Motion used by default where instant feedback would be clearer.

Treat these patterns as prompts for review, not automatic rejection criteria.
