---
applyTo: "src/**/ui/**,src/**/frontend/**,**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss"
description: "Frontend development conventions — design systems, accessibility, component structure"
---

# Frontend Development Standards

These conventions apply to all frontend/UI code in OwlBear projects. They are enforced by the architect (during review) and the reviewer (during verification) for tasks tagged `frontend` or `ui`.

## Design guidance

For deeper design guidance, use the `frontend-design` skill.

## Design system

- **Porsche projects:** Use the [Porsche Design System](https://designsystem.porsche.com/) as the component library and design language. Follow PDS component APIs, spacing tokens, color tokens, and typography scales. Do not create custom components that duplicate PDS functionality.
- **Non-Porsche projects:** Document the chosen design system in the project definition before starting frontend work. If no design system is specified, use a minimal, accessible component approach without a third-party library.

When using the Porsche Design System:

- Import components from `@porsche-design-system/components-{framework}` (framework = react, angular, vue, etc.)
- Use PDS design tokens for spacing, colors, and typography — never hardcode pixel values or hex colors that have a token equivalent
- Follow PDS layout patterns (grid, flex utilities) over custom CSS layout
- Component composition follows PDS conventions (slots, named slots, event naming)

## Accessibility (a11y)

Minimum standard: **WCAG 2.1 Level AA**.

- All interactive elements must be keyboard-navigable
- All images must have meaningful `alt` text (or `alt=""` for decorative)
- Color contrast ratios: ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- Form inputs must have associated `<label>` elements
- ARIA attributes only when semantic HTML is insufficient — prefer native elements
- Page must be navigable with screen reader (logical heading hierarchy, landmark roles)

The reviewer checks a11y as part of the security/quality review for frontend-tagged tasks.

## Component structure

- One component per file — match the component name to the filename
- Separate concerns: logic (hooks/composables), presentation (component), styling (CSS module or scoped)
- Props/inputs are typed (TypeScript interfaces or framework-specific typing)
- State management is explicit — document where state lives and how it flows
- No business logic in components — extract to services/hooks/composables

## Responsive design

- Mobile-first approach: base styles for mobile, progressive enhancement via breakpoints
- Use the design system's breakpoint tokens (if available) over custom media queries
- Test at minimum: 320px, 768px, 1024px, 1440px viewport widths
- No horizontal scrolling at any supported viewport

## Testing

- Component tests use the framework's testing library (e.g., Testing Library, Vitest)
- Test user behavior, not implementation details — interact via roles, labels, and text
- a11y tests: use `axe-core` or equivalent automated checker in the test suite
- Visual regression tests are recommended for design-system-critical components
