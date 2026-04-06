---
name: h-frontend-design
description: "Handbook: Frontend UI/UX design guidance — typography, color, layout, motion, interaction"
user-invocable: true
---

# Frontend Design Reference

Design reference for OwlBear-authored UI. Adapted from Impeccable (Paul Bakaus) and Anthropic's frontend-design skill. See `NOTICE.md` for attribution.

For frontend component structure, accessibility patterns, and testing conventions, see `h-frontend-conventions`.

## Design Context

Before producing design guidance, establish (or infer) three things:

1. **Target audience** — Developer tooling, consumer app, internal tool?
2. **Primary use cases / jobs** — Key user journeys?
3. **Brand personality or tone** — Minimal and technical? Warm and approachable? Playful or serious?

If unknown, state assumptions explicitly and invite correction before proceeding.

## Reference Pack

Detailed reference material lives in `references/`. Load the relevant file when addressing a specific design concern — do not load all references by default.

| Reference | When to use |
|-----------|-------------|
| `references/typography.md` | Font choices, scale, vertical rhythm, readability |
| `references/color-and-contrast.md` | Color palettes, contrast ratios, dark mode, OKLCH |
| `references/spatial-design.md` | Spacing systems, layout grid, density, touch targets |
| `references/motion-design.md` | Animation duration, easing, reduced-motion support |
| `references/interaction-design.md` | States, focus, keyboard, dialogs, undo/confirm |
| `references/responsive-design.md` | Mobile-first, breakpoints, container queries, real devices |
| `references/ux-writing.md` | Button labels, error messages, empty states, tone |
| `references/anti-patterns.md` | Anti-pattern classification: universal blockers vs. taste heuristics |

These are co-located in the `skills/h-frontend-design/references/` directory.

## Universal Blockers

Hard quality gates — never ship with any of these present:

- No visible focus replacement when native outline is removed
- Placeholder text used as a form label
- Critical actions accessible only on hover
- Text contrast below WCAG AA (4.5:1 body, 3:1 large text)
- Touch targets below 44x44 px
- Critical actions hidden on mobile viewports
- No `prefers-reduced-motion` fallback for animations
- Ambiguous primary action labels ("OK", "Submit", "Yes" with no context)
- Generic error messages ("An error occurred") with no user-actionable guidance

## Design Domains

### Typography

Font choices, type scale, vertical rhythm, and readability. See `references/typography.md` for the full reference including scale ratios, line-height calculations, and font-stack recommendations.

### Color and Contrast

Color palettes, contrast ratios, dark mode support, and OKLCH color space usage. See `references/color-and-contrast.md` for palette construction, AA/AAA thresholds, and systematic dark-mode inversion.

### Spatial Design

Spacing systems, layout grids, density levels, and touch targets. See `references/spatial-design.md` for 4px/8px base grids, density presets (compact/normal/comfortable), and minimum target sizes.

### Motion Design

Animation duration, easing curves, reduced-motion support, and transition patterns. See `references/motion-design.md` for duration ranges, cubic-bezier references, and `prefers-reduced-motion` implementation.

### Interaction Design

State management, focus patterns, keyboard navigation, dialogs, and undo/confirm flows. See `references/interaction-design.md` for focus-visible strategies, dialog patterns, and destructive-action confirmation.

### Responsive Design

Mobile-first approach, breakpoints, container queries, and real-device testing. See `references/responsive-design.md` for breakpoint tokens, container query patterns, and viewport-specific layout strategies.

### UX Writing

Button labels, error messages, empty states, and tone. See `references/ux-writing.md` for microcopy patterns, error message templates, and empty-state content strategies.

## Anti-Pattern Classification

Anti-patterns fall into two categories:

1. **Universal blockers** (listed above) — hard gates, always reject.
2. **Taste heuristics** — AI-slop signatures like default system-font stacks, purple/cyan color schemes, glassmorphism overuse. These are suggestions, not laws. Label them as such when flagging.

See `references/anti-patterns.md` for the full classification.

## Known Gotchas

- **Universal blockers override taste heuristics.** Always scan for hard gates before subjective design feedback.
- **Reference files must be loaded explicitly.** They are co-located but not auto-loaded. Load only the one relevant to the current question.
- **State assumptions about audience and tone.** Design guidance without context assumptions is generic and unhelpful. Be explicit about what you're assuming.
