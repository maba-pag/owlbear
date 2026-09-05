---
name: h-frontend-conventions
description: "Handbook: Frontend development conventions — design systems, accessibility, component structure"
user-invocable: false
---

# Frontend Conventions

These are the OwlBear baseline conventions for consuming projects. Explicit project configuration,
design-system guidance, and local instructions may replace the baseline.

## Discover Project Policy

Before changing frontend code, inspect the owning package and established implementation for:

- framework, language, compiler, router, and state-management approach;
- component library, design system, tokens, and styling strategy;
- source organization, naming, colocation, and public module boundaries;
- supported browsers, input modes, viewports, and accessibility requirements;
- test, lint, typecheck, build, preview, and browser scripts.

Follow coherent local patterns unless they directly cause the problem being solved. Do not infer
React, Cockpit, Porsche Design System, Vite, Vitest, or Playwright without repository evidence.

## Design System

- Use the project's established design system, components, tokens, typography, and interaction
  patterns when they satisfy the required behavior.
- Do not recreate controls, layout primitives, or semantic tokens already supplied by that system.
- When no design system exists, prefer a minimal set of accessible, locally consistent primitives;
  do not introduce a broad component dependency for one isolated need.
- Verify third-party component behavior against the installed version's types and runtime contract,
  especially for custom elements, events, slots, focus, and form participation.

For deeper visual and interaction guidance, see `h-frontend-design`.

## Optional PDS Knowledge Companion

When a consuming project declares a Porsche Design System package, use its matching package-provided
knowledge skill as an optional companion:

- Discover the PDS wrapper package, framework, installed version, and active Copilot skill roots from
  the project manifest, lockfile, and workspace settings. Do not assume React, a `web/` directory,
  Cockpit, or `.owlbear/skills`.
- Use the installed wrapper's `pds-skill` binary with explicit `--package`, `--location`, and
  `--skill pds-knowledge-{framework}` arguments to link the companion into a configured local skill
  root. Keep the link generated and ignored; do not copy or commit the package-owned skill into
  `share/skills` or another source-controlled skill tree.
- Recreate the link after dependency installation using the consuming project's package-manager
  lifecycle, or document the package-manager-specific command when lifecycle hooks are not owned by
  the project. A missing or dangling link means the optional companion is unavailable; continue with
  this handbook and project-local policy instead of inferring a PDS contract.
- Once loaded, read the companion before PDS-specific frontend work. Verify installed metadata and
  typings first, then read the relevant exact-version references for components, stylesheets, tokens,
  themes, and testing. Use exact-version source or official storefront material only when the
  installed references are insufficient.
- Keep the PDS package, companion skill, lockfile, generated assets, and project integration aligned
  when the project vendors or generates runtime assets. Use the project's build/version checks;
  a symlink alone proves only that the installed tree is being read.
- The companion does not replace project discovery and may not cover setup, migration, changelog,
  patterns/templates, AG Grid, or other PDS topics. For uncovered material, consult matching
  exact-version official documentation.

## Accessibility and Input

Use semantic platform elements first and add ARIA only when native semantics cannot express the
interaction. At minimum:

- Associate labels, instructions, and errors with form controls.
- Preserve meaningful keyboard and pointer operation for supported workflows.
- Provide meaningful text alternatives for non-text content; decorative images use empty alt text.
- Maintain logical headings and landmarks.
- Do not use color alone to communicate required state.
- Preserve visible focus when native focus indicators are replaced.

Apply the consuming project's accessibility target and supported input modes. If none is defined,
use WCAG 2.1 AA and platform conventions as the baseline, then validate the paths users actually
need rather than treating a generic checklist as proof of usability.

## Component and Module Structure

- Organize code around responsibilities and change locality. Colocate a component's private styles,
  tests, and helpers when that makes the behavior easier to understand and change together.
- Follow established project directories for API access, state, routes, components, and utilities;
  do not impose `src/api/`, `src/hooks/`, or another framework layout on a different architecture.
- Separate reusable domain or business behavior from rendering when it has independent callers,
  tests, or change reasons. Small view-state coordination may remain in the component.
- Split a file when it owns multiple independently changing responsibilities, not merely because it
  contains more than one small local component.
- Type public props, events, API payloads, and state boundaries using the project's language and
  conventions.
- Keep state ownership explicit: identify where canonical state lives, how updates flow, and which
  layer handles loading, errors, retries, and optimistic reconciliation.

## Responsive and Visual Behavior

- Derive supported layout states from project requirements, existing breakpoints, analytics, or the
  target workflow. Do not assume a fixed viewport matrix or mobile-first policy.
- Use design-system breakpoint tokens or locally consistent media/container queries.
- Keep primary content and actions coherent and reachable at each supported layout state.
- Use stable responsive constraints for grids, boards, toolbars, media, and other fixed-format UI so
  dynamic content does not cause incoherent shifting or overlap.
- Static CSS can establish declared rules; only real-browser geometry can prove clipping, overlap,
  viewport reachability, and rendered layout.

## Testing and Proof

Load `h-vitest-and-linting` when the project uses its covered toolchain. Match proof to the claim:

- Unit/component tests protect observable behavior, public component contracts, and meaningful state
  transitions supported by their runtime environment.
- Typecheck, build, and linters prove compilation and static contracts.
- Real-browser tests prove browser APIs, assembled workflows, focus behavior, geometry, viewport
  behavior, and screenshots.

Do not add durable tests for internal DOM shape, source strings, removed files/components, generated
compiler branches, or configuration presence unless those artifacts are maintained public contracts.
A durable test must name a plausible user-visible, state, or API regression that would make it fail.
Use task-local search, diff, lint, typecheck, build, or inspection for one-time structural proof.

Automated accessibility checks can identify classes of violations but do not prove workflow usability.
Use exact values and discriminating cases for bounded option or event contracts; DOM presence alone
does not prove visibility or reachability.

## Cockpit/PDS/React Profile

Apply this profile only when the target package uses Cockpit's React and Porsche Design System stack:

- Import components from `@porsche-design-system/components-react` and use PDS spacing, color,
  typography, component, slot, property, and event contracts rather than duplicating them.
- PDS custom elements are hosts in jsdom. Do not assume native roles or events unless verified for
  the installed version. `PInputText` exposes value on its host; `PSelect` commonly emits `change`
  with `detail.value`; `PMultiSelect` emits `update` with `detail.value`.
- When jsdom cannot represent layout, focus trapping, or another browser behavior, use Cockpit's
  Playwright proof rather than replacing the component contract with a native-element assumption.
- React Compiler may generate memo/cache branches. Do not add implementation tests merely to cover
  generated branches; behavior-binding assertions are the proof.
- Cockpit's setup imports the PDS jsdom polyfill, Testing Library DOM matchers, and
  `skipPorscheDesignSystemCDNRequestsDuringTests()` from the main PDS React package.
- jsdom does not implement `attachInternals`. It belongs on `HTMLElement`, not `Element`:

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

- Discover Cockpit E2E, build, CSS, and HTML scripts from its package manifest. Build or web-server
  startup failure can prevent Playwright assertions from running; classify that failure separately.
