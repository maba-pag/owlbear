---
name: h-frontend-conventions
description: "Handbook: Frontend development conventions — design systems, accessibility, component structure"
user-invocable: false
---

# Frontend Conventions

## Design System

- **Porsche projects:** Use the [Porsche Design System](https://designsystem.porsche.com/) as component library and design language. Follow PDS component APIs, spacing tokens, color tokens, and typography scales. Do not duplicate PDS functionality with custom components.
- **Non-Porsche projects:** Document the chosen design system in the project definition before starting frontend work. If unspecified, use a minimal, accessible component approach.

When using PDS:
- Import from `@porsche-design-system/components-{framework}`
- Use PDS design tokens for spacing, colors, typography — never hardcode pixel values or hex colors with token equivalents
- Follow PDS layout patterns (grid, flex utilities) over custom CSS
- Component composition follows PDS conventions (slots, named slots, event naming)

For deeper design guidance, see the `h-frontend-design` skill.

## Accessibility (a11y)

Minimum: **WCAG 2.1 Level AA**.

- All interactive elements: keyboard-navigable
- Images: meaningful `alt` text (or `alt=""` for decorative)
- Color contrast: ≥ 4.5:1 normal text, ≥ 3:1 large text
- Form inputs: associated `<label>` elements
- ARIA: only when semantic HTML is insufficient — prefer native elements
- Navigation: logical heading hierarchy, landmark roles for screen readers

## Component Structure

- One component per file — match component name to filename
- Separate concerns: logic (hooks/composables), presentation (component), styling (CSS module or scoped)
- Props/inputs are typed (TypeScript interfaces or framework-specific typing)
- State management is explicit — document where state lives and how it flows
- No business logic in components — extract to services/hooks/composables

## Responsive Design

- Mobile-first: base styles for mobile, progressive enhancement via breakpoints
- Use design system breakpoint tokens over custom media queries
- Test at minimum: 320px, 768px, 1024px, 1440px viewport widths
- No horizontal scrolling at any supported viewport

## Testing

- Component tests: framework's testing library (Testing Library, Vitest)
- Test user behavior, not implementation details — interact via roles, labels, text
- a11y tests: use `axe-core` or equivalent automated checker
- Visual regression tests recommended for design-system-critical components
