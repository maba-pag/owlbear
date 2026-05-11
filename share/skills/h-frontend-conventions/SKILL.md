---
name: h-frontend-conventions
description: "Handbook: Frontend development conventions — design systems, accessibility, component structure"
user-invocable: false
---

# Frontend Conventions

Primary scope in this workspace is the Cockpit frontend at `serve/cockpit/web/`: React 19, TypeScript, Vite, React Compiler, React Router, Porsche Design System React components, Vitest/jsdom, and Playwright.

## Design System

- **Cockpit / Porsche projects:** Use the [Porsche Design System](https://designsystem.porsche.com/) as component library and design language. Follow PDS component APIs, spacing tokens, color tokens, and typography scales. Do not duplicate PDS functionality with custom components.
- **Non-Porsche projects:** Document the chosen design system in the project definition before starting frontend work. If unspecified, use a minimal, accessible component approach.

When using PDS:

- In Cockpit React code, import from `@porsche-design-system/components-react`.
- Use PDS design tokens for spacing, colors, typography — never hardcode pixel values or hex colors with token equivalents
- Prefer PDS components for controls, modals, selects, inputs, buttons, tabs, and status indicators when jsdom/E2E support is adequate.
- Component composition follows PDS conventions (slots, named slots, event naming, host-element properties).
- For PDS custom elements in tests, drive the real element contract: query `p-select`, `p-input-text`, or `p-multi-select` hosts and dispatch the CustomEvent shape the component emits.

### Cockpit PDS Testing Patterns

- `PSelect` and `PInputText` are custom-element hosts in jsdom; do not assume native roles such as `combobox` or `textbox` unless a local test proves them.
- `PInputText` exposes its value as a JavaScript property on the host element.
- `PMultiSelect` state changes through `CustomEvent('update', { detail: { value: [...] } })`; do not use native `change` or `input` events for it.
- `PSelect` tests usually drive `CustomEvent('change', { detail: { value } })` on the `p-select` host.
- If a PDS component lacks reliable jsdom support for a required behavior, use a real-browser Playwright proof or document a native fallback in builder notes.

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
- Separate concerns: API clients in `src/api/`, reusable state logic in `src/hooks/`, presentation in components, and layout styling in CSS files or shared utility modules.
- Props/inputs are typed (TypeScript interfaces or framework-specific typing)
- State management is explicit — document where state lives and how it flows
- Avoid embedding reusable business logic in components. Small view-state coordination is acceptable; shared behavior belongs in hooks, API modules, or pure helpers.
- React Compiler can add generated memo/cache branches. Do not create artificial implementation tests just to satisfy compiled coverage unless the task explicitly targets coverage; behavior-binding assertions are the proof.

## Responsive Design

- Mobile-first: base styles for mobile, progressive enhancement via breakpoints
- Use design system breakpoint tokens or locally consistent media-query ranges.
- Test at minimum: 320px, 768px, 1024px, 1440px viewport widths
- No horizontal scrolling at any supported viewport
- Runtime geometry claims require Playwright or browser evidence. Vitest/jsdom can check static CSS/source contracts, but it cannot prove bounding boxes, overlap, or viewport reachability.

## Testing

- Component tests: framework's testing library (Testing Library, Vitest)
- Test user behavior, not implementation details — interact via roles, labels, text
- a11y tests: use `axe-core` or equivalent automated checker
- Visual regression tests recommended for design-system-critical components
- Cockpit E2E tests live under `serve/cockpit/web/e2e/` and run with Playwright Chromium via `npm run test:e2e`.
- Build proof matters for E2E: Playwright starts through `npm run build && npm run preview`, so TypeScript/build failures block E2E before assertions execute.
- For CSS and HTML quality, use the package scripts `npm run lint:css` and `npm run lint:html` when AC or touched files require them.
- DOM presence alone is weak proof for visibility, reachability, or exact option contracts. Prefer exact values, full option lists, discriminating negative cases, and real viewport assertions for layout AC.

### PDS Test Environment Setup (Vitest + jsdom)

- `skipPorscheDesignSystemCDNRequestsDuringTests()` is exported from the **main package** (`@porsche-design-system/components-react`), NOT from the `/testing` subpath. The research doc placed it in `/testing` — this is incorrect.
- Cockpit setup imports `@porsche-design-system/components-react/jsdom-polyfill`, `@testing-library/jest-dom/vitest`, and `skipPorscheDesignSystemCDNRequestsDuringTests()` from `vitest.setup.ts`.
- jsdom does not implement `attachInternals`. It lives on `HTMLElement`, not `Element` — mock it on `HTMLElement.prototype`, not `Element.prototype`:

  ```ts
  if (
    typeof HTMLElement !== "undefined" &&
    !HTMLElement.prototype.attachInternals
  ) {
    (HTMLElement.prototype as unknown as Record<string, unknown>)[
      "attachInternals"
    ] = vi.fn();
  }
  ```
