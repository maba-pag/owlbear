---
name: h-frontend-design
description: "Handbook: Frontend UI/UX design guidance — typography, color, layout, motion, interaction"
user-invocable: true
---

# Frontend Design Reference

Design reference for project-authored UI. Adapted from Impeccable (Paul Bakaus) and Anthropic's frontend-design skill; source tracking lives in `.owlbear/sources/overview.md`.

For frontend component structure, accessibility patterns, and testing conventions, see `h-frontend-conventions`.

## Project Context

Before producing design guidance, establish from project documentation, dependencies, routes, and
existing UI patterns:

1. **Product and audience** — Operational tool, consumer workflow, content surface, marketing site,
   or another product type; novice, expert, internal, or public users.
2. **Primary jobs** — The user goals and workflows the interface must make efficient or compelling.
3. **Visual intent** — Brand personality, information density, hierarchy, and interaction tone.
4. **System constraints** — Existing design system, component library, tokens, input modes, and
   supported viewports.

State unresolved assumptions. Ask the user only when materially different interpretations would
change the design direction or audit result.

Do not infer Cockpit, Porsche Design System, React, or any other product or stack without repository
evidence. When those dependencies and product surfaces are present, their local conventions remain
authoritative.

## Design Domain Index

Detailed reference material lives in the sections below. Load the relevant section when addressing a specific design concern — do not scan every domain by default.

| Section | When to use |
| --- | --- |
| Typography | Font choices, scale, vertical rhythm, readability |
| Color and Contrast | Color palettes, contrast ratios, dark mode, OKLCH |
| Spatial Design | Spacing systems, layout grid, density, touch targets |
| Motion Design | Animation duration, easing, reduced-motion support |
| Interaction Design | States, focus, keyboard, dialogs, undo/confirm |
| Responsive Design | Supported viewports, layout transitions, container queries, real devices |
| UX Writing | Button labels, error messages, empty states, tone |
| Anti-Pattern Classification | Objective blockers vs. contextual heuristics |

## Quality Classification

### Objective Blockers

Treat these as blockers when they affect an in-scope user workflow:

- No visible focus replacement when native outline is removed
- Placeholder text used as a form label
- Critical actions accessible only on hover
- Ambiguous primary action labels ("OK", "Submit", "Yes" with no context)
- Generic error messages ("An error occurred") with no user-actionable guidance
- Controls or content that overlap, clip, or become unreachable in a supported viewport
- Missing loading, error, or recovery behavior that prevents completion of the primary job

Apply legal, accessibility, target-size, contrast, reduced-motion, keyboard, and viewport thresholds
from the consuming project's requirements. In their absence, use WCAG and platform guidance as a
recommended baseline, but distinguish a measured violation from a theoretical risk.

### Contextual Heuristics

Tie heuristic findings to the discovered product intent. Palette, typography, density, decorative
treatment, card usage, animation style, and mobile behavior are not defects merely because they
differ from a generic preference.

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

Supported viewports, container queries, layout transitions, and real-browser testing. Do not assume
mobile-first behavior or a mobile support floor unless project requirements or user workflows imply
it. Check that content and actions remain coherent at each supported layout state.

### UX Writing

Button labels, error messages, empty states, and tone. Check microcopy patterns, error message templates, and empty-state content strategies when UX writing is in scope.

## Anti-Pattern Classification

Anti-patterns fall into two categories:

1. **Objective blockers** — observed failures against a user goal, supported environment, or stated
   project requirement.
2. **Contextual heuristics** — design concerns whose relevance depends on product intent and local
   conventions.

Common generated-design signatures such as interchangeable card grids, ornamental gradients,
generic system typography, or unexplained purple/cyan palettes are heuristics, not automatic
findings. Report them only when they weaken the intended hierarchy, brand, workflow, or usability.

## Product-Type Starting Points

Use these only when project evidence supports the profile:

| Product type | Starting priorities |
| --- | --- |
| Operational or expert tool | Scanability, stable layout, efficient repeated actions, state clarity, restrained decoration |
| Consumer workflow | Clear next action, progressive disclosure, recovery, trust, comfortable touch interaction |
| Content or editorial surface | Reading rhythm, navigation, hierarchy, media treatment, content focus |
| Marketing or brand surface | Distinct identity, offer clarity, narrative pacing, credible product evidence, conversion path |

An established local design system overrides these starting points. For Cockpit, repository evidence
identifies the operational-tool profile and Porsche Design System conventions.

## State and Evidence Discipline

For a scoped workflow, inspect the states it actually supports: normal, loading, empty, error,
success, destructive or confirmation, and permission-limited states where applicable. Missing states
matter when they block or confuse a real user path, not merely because a checklist names them.

Match claims to evidence:

- Source and static tests can establish tokens, component contracts, declared breakpoints, and
  state branches.
- Runtime component tests can establish rendered state and interaction behavior within their
  environment.
- Browser execution and screenshots establish geometry, overlap, clipping, viewport reachability,
  visual hierarchy, and animation behavior.

Do not present static-code inference as observed visual harm. State the evidence level and confidence
when stronger proof is unavailable.

## Known Gotchas

- **Objective blockers outrank contextual heuristics.** Confirm user impact and evidence before
  subjective design feedback.
- **Design sections must be loaded selectively.** Read only the domain section relevant to the current question.
- **State material assumptions about audience and tone.** Design guidance without project context is
  generic and unhelpful.
