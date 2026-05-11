---
name: h-frontend-design
description: "Handbook: Frontend UI/UX design guidance — typography, color, layout, motion, interaction"
user-invocable: true
---

# Frontend Design Reference

Design reference for project-authored UI. Adapted from Impeccable (Paul Bakaus) and Anthropic's frontend-design skill; source tracking lives in `.owlbear/sources/overview.md`.

For frontend component structure, accessibility patterns, and testing conventions, see `h-frontend-conventions`.

## Design Context

Before producing design guidance, establish (or infer) three things:

1. **Target audience** — Developer tooling, consumer app, internal tool?
2. **Primary use cases / jobs** — Key user journeys?
3. **Brand personality or tone** — Minimal and technical? Warm and approachable? Playful or serious?

If unknown, state assumptions explicitly and invite correction before proceeding.

For Cockpit, default to an internal developer-operations tool unless a task states otherwise: dense but calm information layout, fast scanning, predictable controls, and minimal decorative treatment.

## Design Domain Index

Detailed reference material lives in the sections below. Load the relevant section when addressing a specific design concern — do not scan every domain by default.

| Section | When to use |
|-----------|-------------|
| Typography | Font choices, scale, vertical rhythm, readability |
| Color and Contrast | Color palettes, contrast ratios, dark mode, OKLCH |
| Spatial Design | Spacing systems, layout grid, density, touch targets |
| Motion Design | Animation duration, easing, reduced-motion support |
| Interaction Design | States, focus, keyboard, dialogs, undo/confirm |
| Responsive Design | Mobile-first, breakpoints, container queries, real devices |
| UX Writing | Button labels, error messages, empty states, tone |
| Anti-Pattern Classification | Universal blockers vs. taste heuristics |

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

Font choices, type scale, vertical rhythm, and readability. Check scale ratios, line-height calculations, and font-stack choices when typography is in scope.

### Color and Contrast

Color palettes, contrast ratios, dark mode support, and OKLCH color space usage. Check palette construction, AA/AAA thresholds, and systematic dark-mode inversion when color is in scope.

### Spatial Design

Spacing systems, layout grids, density levels, and touch targets. Check 4px/8px base grids, density presets, and minimum target sizes when spatial design is in scope.

### Motion Design

Animation duration, easing curves, reduced-motion support, and transition patterns. Check duration ranges, easing choices, and `prefers-reduced-motion` implementation when motion is in scope.

### Interaction Design

State management, focus patterns, keyboard navigation, dialogs, and undo/confirm flows. Check focus-visible strategies, dialog patterns, and destructive-action confirmation when interaction design is in scope.

### Responsive Design

Mobile-first approach, breakpoints, container queries, and real-device testing. Check breakpoint tokens, container query patterns, and viewport-specific layout strategies when responsive design is in scope.

### UX Writing

Button labels, error messages, empty states, and tone. Check microcopy patterns, error message templates, and empty-state content strategies when UX writing is in scope.

## Anti-Pattern Classification

Anti-patterns fall into two categories:

1. **Universal blockers** (listed above) — hard gates, always reject.
2. **Taste heuristics** — AI-slop signatures like default system-font stacks, purple/cyan color schemes, glassmorphism overuse. These are suggestions, not laws. Label them as such when flagging.

Use this classification directly when producing frontend-audit findings.

## Cockpit Defaults

- Treat Cockpit as a work surface, not a marketing page: prioritize density, hierarchy, keyboard reachability, state clarity, and predictable navigation.
- Avoid hero/landing-page composition, decorative card stacks, ornamental gradients, and copy that explains the interface instead of improving it.
- Prefer Porsche Design System components and tokens when they match the interaction. When PDS/web-component behavior conflicts with jsdom, record whether proof belongs in Vitest or Playwright.

## Known Gotchas

- **Universal blockers override taste heuristics.** Always scan for hard gates before subjective design feedback.
- **Design sections must be loaded selectively.** Read only the domain section relevant to the current question.
- **State assumptions about audience and tone.** Design guidance without context assumptions is generic and unhelpful. Be explicit about what you're assuming.
