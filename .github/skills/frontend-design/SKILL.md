---
name: frontend-design
description: "Frontend UI/UX design guidance — typography, color, spatial layout, motion, interaction, responsive design, and UX writing. Use when the user asks for design direction, component styling, accessibility improvements, or frontend quality improvements."
---

# Frontend Design Skill

OwlBear-authored design reference adapted from Impeccable (Paul Bakaus) and
Anthropic's frontend-design skill. See `NOTICE.md` for attribution.

## Design Context

Before producing design guidance, ask for (or infer) these three things:

1. **Target audience** — Who is the primary user? Developer tooling, consumer app, internal tool?
2. **Primary use cases / jobs** — What does the user need to accomplish? Key user journeys?
3. **Brand personality or tone** — Minimal and technical? Warm and approachable? Playful or serious?

If the answer is unknown, state your assumptions explicitly and invite correction before proceeding.

---

## Reference Pack

Detailed reference material is in `references/`. Use the relevant file(s) when
addressing a specific design concern. Do not load all references by default —
load the one(s) relevant to the current task.

| Reference | When to use |
|-----------|-------------|
| [references/typography.md](references/typography.md) | Font choices, scale, vertical rhythm, readability |
| [references/color-and-contrast.md](references/color-and-contrast.md) | Color palettes, contrast ratios, dark mode, OKLCH |
| [references/spatial-design.md](references/spatial-design.md) | Spacing systems, layout grid, density, touch targets |
| [references/motion-design.md](references/motion-design.md) | Animation duration, easing, reduced-motion support |
| [references/interaction-design.md](references/interaction-design.md) | States, focus, keyboard, dialogs, undo/confirm |
| [references/responsive-design.md](references/responsive-design.md) | Mobile-first, breakpoints, container queries, real devices |
| [references/ux-writing.md](references/ux-writing.md) | Button labels, error messages, empty states, tone |
| [references/anti-patterns.md](references/anti-patterns.md) | Anti-pattern classification: universal blockers vs. taste heuristics |

---

## Universal Blockers

These are hard quality gates — never ship with any of these present:

- No visible focus replacement when native outline is removed
- Placeholder text used as a form label
- Critical actions accessible only on hover
- Text contrast below WCAG AA (4.5:1 body, 3:1 large text)
- Touch targets below 44×44 px
- Critical actions hidden on mobile viewports
- No `prefers-reduced-motion` fallback for animations
- Ambiguous primary action labels ("OK", "Submit", "Yes" with no context)
- Generic error messages ("An error occurred") with no user-actionable guidance

---

## Workflow

1. **Gather context.** Ask (or infer) audience, use cases, and tone. Document assumptions.
2. **Load the relevant reference(s).** Pick from the reference pack above.
3. **Apply universal blockers check.** Scan for hard gates first.
4. **Produce design direction or review.** Be specific — reference file sections, concrete values, and code examples where helpful.
5. **Flag taste heuristics separately.** Anti-pattern heuristics (AI-slop signatures like default system-font stacks, purple/cyan color schemes, glassmorphism overuse) are suggestions, not laws. Label them as such.
