# Sources

External repos and resources studied during OwlBear development.

## Cockpit Visual Audit (Task #1534)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 component overview | <https://designsystem.porsche.com/v4/components/overview/> | Available UI components for action, form, overlay, navigation, text, and data display surfaces | `.owlbear/research/cockpit-visual-audit.md` | 2026-05-14 |
| PDS v4 Select docs | <https://designsystem.porsche.com/v4/components/select/> | Select composition uses PDS select-option components, not native option children | `.owlbear/research/cockpit-visual-audit.md` | 2026-05-14 |
| PDS v4 Popover docs | <https://designsystem.porsche.com/v4/components/popover/> | Popover/top-layer behavior for floating disclosure instead of in-flow status-bar panels | `.owlbear/research/cockpit-visual-audit.md` | 2026-05-14 |
| PDS v4 Tabs docs | <https://designsystem.porsche.com/v4/components/tabs/> | Tab component expectations for styled sidecar tab navigation | `.owlbear/research/cockpit-visual-audit.md` | 2026-05-14 |

## Token Migration Provenance (Task #1603)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 color-scheme.css | (local: node_modules/@porsche-design-system/components-js/global-styles/color-scheme.css) | 33 `--p-color-*` tokens with light/dark variants via `.scheme-*` classes | `.owlbear/research/1603-token-migration-provenance.md` | 2026-05-16 |
| PDS v4 variables.css | (local: node_modules/@porsche-design-system/components-js/global-styles/variables.css) | Spacing, radius, shadow, motion, typography tokens | `.owlbear/research/1603-token-migration-provenance.md` | 2026-05-16 |
| PDS v4 design system docs | <https://designsystem.porsche.com/v4/> | Token naming conventions and theming approach | `.owlbear/research/1603-token-migration-provenance.md` | 2026-05-16 |

## Accessibility Sweep Research (Task #1628)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright accessibility testing | <https://playwright.dev/docs/accessibility-testing> | @axe-core/playwright API, withTags WCAG scope, fixture pattern | `.owlbear/research/accessibility-sweep-1628.md` | 2026-05-16 |
| PDS v4 component accessibility | <https://designsystem.porsche.com/v3/components/button/accessibility/> | PDS components tested against axe-core WCAG 2.2 AA | `.owlbear/research/accessibility-sweep-1628.md` | 2026-05-16 |
| axe-core rule documentation | <https://www.deque.com/axe/core-documentation/api-documentation/> | WCAG tag mapping for withTags configuration | `.owlbear/research/accessibility-sweep-1628.md` | 2026-05-16 |

## Motion/Transition Token Migration (Task #1627)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Motion tokens docs | <https://designsystem.porsche.com/v4/tokens/motion/> | Duration (sm/md/lg/xl) and easing (in-out/in/out) token definitions | `.owlbear/research/1627-pds-motion-tokens.md` | 2026-05-16 |
| PDS v4 CSS Variables docs | <https://designsystem.porsche.com/v4/stylesheets/css-variables/introduction/> | `--p-duration-*` and `--p-ease-*` custom property API | `.owlbear/research/1627-pds-motion-tokens.md` | 2026-05-16 |
| PDS v4 Tailwind motion docs | <https://designsystem.porsche.com/v4/tailwindcss/motion/examples/> | Tailwind `.duration-*` and `.ease-*` class mapping | `.owlbear/research/1627-pds-motion-tokens.md` | 2026-05-16 |
| PDS GitHub common-styles.ts | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/styles/common-styles.ts> | `getTransition()` internal override mechanism (`--p-transition-duration`) | `.owlbear/research/1627-pds-motion-tokens.md` | 2026-05-16 |
| PDS v4 global-styles/variables.css | (local: node_modules/@porsche-design-system/components-js/global-styles/variables.css) | Token value verification: sm=0.25s, md=0.4s, ease-in-out=cubic-bezier(0.25,0.1,0.25,1) | `.owlbear/research/1627-pds-motion-tokens.md` | 2026-05-16 |

## Sidecar Structure Research (Task #1607)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Spacing styles | <https://designsystem.porsche.com/v3/styles/spacing/> | Fluid/static spacing token names and values | `.owlbear/research/sidecar-structure-pds.md` | 2026-05-16 |
| PDS v4 Typography styles | <https://designsystem.porsche.com/v3/styles/typography/> | Heading scale, pairing guidance | `.owlbear/research/sidecar-structure-pds.md` | 2026-05-16 |
| PDS PHeading API | <https://designsystem.porsche.com/v3/components/heading/api/> | size prop values (small–xx-large), tag prop | `.owlbear/research/sidecar-structure-pds.md` | 2026-05-16 |
| PDS PDivider API | <https://designsystem.porsche.com/v3/components/divider/api/> | Self-closing divider, orientation prop | `.owlbear/research/sidecar-structure-pds.md` | 2026-05-16 |

## Sidecar Information Architecture (Task #1616)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Accordion API | <https://designsystem.porsche.com/v3/components/accordion/api/> | Props: heading, heading-tag, open, size, compact, update event | `.owlbear/research/sidecar-information-architecture.md` | 2026-05-16 |
| PDS Accordion Usage | <https://designsystem.porsche.com/v3/components/accordion/usage/> | Usage guidelines: when to use/avoid accordions | `.owlbear/research/sidecar-information-architecture.md` | 2026-05-16 |
| Jira Cloud: Configure work item details | <https://support.atlassian.com/jira-software-cloud/docs/configure-the-issue-detail-view/> | Field layout configuration, section ordering patterns | `.owlbear/research/sidecar-information-architecture.md` | 2026-05-16 |

## Filter Panel PDS Controls (Task #1617)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v3 component nav (deprecation markers) | <https://designsystem.porsche.com/v3/components/checkbox-wrapper/examples/> | Confirms CheckboxWrapper 🚫 deprecated, replaced by Checkbox | `.owlbear/research/filter-panel-pds-controls.md` | 2026-05-16 |
| PDS GitHub CheckboxExampleControlled.tsx | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-react/src/examples/CheckboxExampleControlled.tsx> | Canonical React controlled PCheckbox pattern | `.owlbear/research/filter-panel-pds-controls.md` | 2026-05-16 |
| PDS GitHub CheckboxExampleForm.tsx | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-react/src/examples/CheckboxExampleForm.tsx> | Form integration with onChange and CheckboxChangeEventDetail | `.owlbear/research/filter-panel-pds-controls.md` | 2026-05-16 |
| PDS GitHub checkbox.tsx (Stencil source) | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/components/checkbox/checkbox.tsx> | Props (name, label, checked, value, disabled), events (change, blur) | `.owlbear/research/filter-panel-pds-controls.md` | 2026-05-16 |
| PDS v3 migration guide | <https://designsystem.porsche.com/v3/news/migration-guide/porsche-design-system/> | Wrapper → standalone component deprecation rationale | `.owlbear/research/filter-panel-pds-controls.md` | 2026-05-16 |

## Simple Component Swaps (Task #1614)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Button API | <https://designsystem.porsche.com/v4/components/button/api/> | PButton props (variant, type, onClick) | `.owlbear/research/1614-simple-component-swaps.md` | 2026-05-16 |
| PDS v4 Heading API | <https://designsystem.porsche.com/v4/components/heading/api/> | PHeading props (tag, size) | `.owlbear/research/1614-simple-component-swaps.md` | 2026-05-16 |
| PDS GitHub — PTabs React wrapper | <https://github.com/porsche-design-system/porsche-design-system> | PTabs onUpdate vs deprecated tabChange event contract | `.owlbear/research/1614-simple-component-swaps.md` | 2026-05-16 |

## CockpitProvider Extraction Research (Task #1491)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React createContext docs | <https://react.dev/reference/react/createContext> | Context provider pattern, consumer re-render semantics | `.owlbear/research/1491-cockpit-provider-extraction.md` | 2026-05-12 |
| React Compiler intro | <https://react.dev/learn/react-compiler/introduction> | Auto-memoization behavior, useMemo escape hatch | `.owlbear/research/1491-cockpit-provider-extraction.md` | 2026-05-12 |
| wisp.blog Nest/Merge Providers | <https://www.wisp.blog/blog/should-i-nest-or-merge-multiple-context-providers-in-react> | Single vs split provider trade-offs, hybrid pattern | `.owlbear/research/1491-cockpit-provider-extraction.md` | 2026-05-12 |
| LogRocket Context Pitfalls | <https://blog.logrocket.com/pitfalls-of-overusing-react-context/> | Split context recommendation, consumer re-render risks | `.owlbear/research/1491-cockpit-provider-extraction.md` | 2026-05-12 |

## PDS Mutation Error Banner Research (Task #1494)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Banner API (v3) | <https://designsystem.porsche.com/v3/components/banner/api> | Props, events, slots, CSS vars for PBanner component | `.owlbear/research/cockpit-mutation-error-banner.md` | 2026-05-12 |
| PDS Inline Notification API (v3) | <https://designsystem.porsche.com/v3/components/inline-notification/api> | Props, events including actionLabel/actionIcon for retry | `.owlbear/research/cockpit-mutation-error-banner.md` | 2026-05-12 |
| PDS Notification Patterns | <https://designsystem.porsche.com/v3/patterns/notifications/introduction> | Component selection criteria: placement, criticality, states | `.owlbear/research/cockpit-mutation-error-banner.md` | 2026-05-12 |
| PDS Notification Decision Tree | <https://designsystem.porsche.com/v3/patterns/notifications/decision-tree> | Error/warning case → Banner or Inline Notification recommended | `.owlbear/research/cockpit-mutation-error-banner.md` | 2026-05-12 |

## PToast Success Feedback (Task #1624)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Toast Configurator (v3) | <https://designsystem.porsche.com/v3/components/toast/configurator/> | PToast singleton pattern, addMessage API, queue behavior | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |
| PDS Toast API (v3) | <https://designsystem.porsche.com/v3/components/toast/api/> | Props (theme), CSS vars (--p-toast-position-bottom) | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |
| PDS Toast Accessibility | <https://designsystem.porsche.com/v3/components/toast/accessibility/> | role="status" ARIA live, keyboard support, AXE compliance | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |
| PDS GitHub ToastExample.tsx | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-react/src/examples/ToastExample.tsx> | Canonical React PToast + useToastManager pattern | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |
| PDS GitHub toast-manager.ts | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/components/toast/toast/toast-manager.ts> | Internal ToastManager: 6s timeout, message queue, singleton guard | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |
| PDS GitHub toast.e2e.ts | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-js/tests/e2e/specs/toast.e2e.ts> | E2E test patterns: --p-temporary-toast-timeout CSS var override | `.owlbear/research/ptoast-success-feedback.md` | 2026-05-16 |

## Dark Mode Border Audit (Task #1625)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Color Tokens | <https://designsystem.porsche.com/v4/tokens/color/> | Color token names, descriptions, `light-dark()` values for all contrast/notification/canvas/surface tokens | `.owlbear/research/dark-mode-border-audit.md` | 2026-05-16 |
| PDS v4 CSS Variables stylesheet | <https://designsystem.porsche.com/v4/stylesheets/css-variables/introduction/> | Full `:root` variable definitions with `light-dark()`, spacing, radius, motion tokens | `.owlbear/research/dark-mode-border-audit.md` | 2026-05-16 |

## Focus-Visible PDS Styling (Task #1626)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Tailwind Focus examples | <https://designsystem.porsche.com/v4/tailwindcss/focus/examples/> | Canonical Tailwind classes for focus-visible: `focus-visible:outline outline-focus outline-offset-2` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS GitHub TailwindFocusVisible.tsx | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/styles/src/app/tailwindcss/TailwindFocusVisible.tsx> | Reference React component showing focus-visible Tailwind pattern | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS GitHub getFocusVisibleStyle.ts | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/styles/projects/emotion/src/focus/getFocusVisibleStyle.ts> | JS/Emotion implementation: `outline: 2px solid colorFocus, outlineOffset: offset` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS GitHub common-styles.ts | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/components/src/styles/common-styles.ts> | Internal component focus: `getFocusBaseStyles()` → `outline: 2px solid var(--p-color-focus)` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS Storefront AGENTS.md (focus section) | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/storefront/AGENTS.md> | Canonical CSS pattern: `button:focus-visible { outline: 2px solid var(--p-color-focus); outline-offset: 2px; }` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS Tailwind @theme (local) | (local: node_modules/@porsche-design-system/components-react/tailwindcss/index.css) | `--color-focus: light-dark(#1a44ea, #1a44ea)` and `--default-outline-width: 2px` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS SCSS _focus.scss | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/styles/projects/scss/src/_focus.scss> | SCSS mixin `focus-visible($offset)` generating `:focus-visible { outline: 2px solid $color-focus }` | `.owlbear/research/focus-visible-pds-styling.md` | 2026-05-16 |
| PDS v4 Color Scheme docs | <https://designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/> | `.scheme-dark`/`.scheme-light` classes, polyfill fallback, Lightning CSS bug workaround | `.owlbear/research/dark-mode-border-audit.md` | 2026-05-16 |
| PDS v4 Border Tokens | <https://designsystem.porsche.com/v4/tokens/border/> | Border tokens cover only `border-radius` — no border-color tokens exist | `.owlbear/research/dark-mode-border-audit.md` | 2026-05-16 |
| PDS Admin Panel template | <https://github.com/porsche-design-system/examples/tree/v4/templates/src/admin-panel/1> | Tailwind `border-contrast-low` pattern, `p-canvas` for layout, `bg-surface`/`bg-canvas` differentiation | `.owlbear/research/dark-mode-border-audit.md` | 2026-05-16 |

## Shell Layout Research (Task #1606)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 component introduction | <https://designsystem.porsche.com/v4/components/introduction/> | p-canvas (🧪 experimental) sidebar/shell component, full component catalog | `.owlbear/research/1606-shell-layout-sticky-header-responsive-sidebar.md` | 2026-05-16 |
| PDS v4 Tailwind Grid docs | <https://designsystem.porsche.com/v4/tailwindcss/grid/examples/> | Porsche Grid utilities (grid-template, col-*), confirmed as content-page grid not app shell | `.owlbear/research/1606-shell-layout-sticky-header-responsive-sidebar.md` | 2026-05-16 |
| Tailwind CSS v4 position docs | <https://tailwindcss.com/docs/position> | sticky/fixed/relative utilities and responsive variants | `.owlbear/research/1606-shell-layout-sticky-header-responsive-sidebar.md` | 2026-05-16 |
| Tailwind CSS v4 grid-template-columns | <https://tailwindcss.com/docs/grid-template-columns> | grid-cols-[arbitrary] syntax for custom column definitions | `.owlbear/research/1606-shell-layout-sticky-header-responsive-sidebar.md` | 2026-05-16 |

## PDS Dark-Mode Compatibility Research (Task #1553)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Migration Guide | <https://designsystem.porsche.com/v4/news/migration-guide/porsche-design-system/> | color-scheme mechanism, theme prop removal, .scheme-* classes | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |
| PDS v4 Theme docs | <https://designsystem.porsche.com/v4/must-know/theme/> | color-scheme foundation, light-dark() CSS function | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |
| PDS v4 Color Scheme stylesheet | <https://designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/> | .scheme-* utility classes, polyfill setup | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |
| PDS GitHub color-scheme build | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/styles/projects/global-styles/scripts/buildColorSchemeCss.ts> | .scheme-* → color-scheme mapping, light-dark() polyfill | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |
| PDS GitHub Issue #1185 | <https://github.com/porsche-design-system/porsche-design-system/issues/1185> | Provider-level theme prop history (closed, shipped in v3) | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |
| PDS CHANGELOG v4.0.0-beta.0 | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/components/CHANGELOG.md#L765> | Theme prop removal confirmation | `.owlbear/research/1553-pds-dark-mode-compat.md` | 2026-05-14 |

## Card Visual Treatment Research (Task #1615)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 PTag source (tag-utils.ts, tag.tsx) | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/components/src/components/tag/> | TagVariant type: 10 variants; props: variant, icon, iconSource, compact | `.owlbear/research/1615-card-visual-treatment-pds.md` | 2026-05-16 |
| PDS v4 PTag examples | <https://designsystem.porsche.com/v4/components/tag/examples/> | Confirmed v4.1.0 API, button/link slot patterns, icon integration | `.owlbear/research/1615-card-visual-treatment-pds.md` | 2026-05-16 |
| PDS v4 PIcon source (icon.tsx, icon-utils.ts) | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/components/src/components/icon/> | IconColor type (11 values), IconSize type, icon names from manifest | `.owlbear/research/1615-card-visual-treatment-pds.md` | 2026-05-16 |
| PDS v4 tag-styles.ts color maps | <https://github.com/porsche-design-system/porsche-design-system/tree/main/packages/components/src/components/tag/tag-styles.ts> | VARIANT_TO_COLOR_MAP, colorTextMap, colorBackgroundMap per variant | `.owlbear/research/1615-card-visual-treatment-pds.md` | 2026-05-16 |

## PBanner Shell Wiring Research (Task #1498)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Banner examples (v3) | <https://designsystem.porsche.com/v3/components/banner/examples/> | Usage patterns, slot-based heading/description, CSS custom properties | `.owlbear/research/cockpit-wire-pbanner-shell.md` | 2026-05-12 |

## Token Architecture Test Research (Task #1535)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Migration Guide | <https://designsystem.porsche.com/v4/news/migration-guide/porsche-design-system/> | PDS v4 theme system: light-dark() CSS function, color-scheme property, scheme-* classes | `.owlbear/research/1535-token-architecture-test-approach.md` | 2026-05-13 |
| PDS v4 CSS Variables | <https://designsystem.porsche.com/v4/stylesheets/css-variables/introduction/> | Full CSS variable reference: --p-color-*, --p-shadow-*, --p-radius-*, --p-spacing-* | `.owlbear/research/1535-token-architecture-test-approach.md` | 2026-05-13 |
| PDS v4 Shadow Tokens | <https://designsystem.porsche.com/v4/tokens/shadow/> | Shadow token values: sm, md, lg | `.owlbear/research/1535-token-architecture-test-approach.md` | 2026-05-13 |
| PDS v4 Border Tokens | <https://designsystem.porsche.com/v4/tokens/border/> | Radius token values: xs through 4xl + full | `.owlbear/research/1535-token-architecture-test-approach.md` | 2026-05-13 |
| PDS v4 Spacing Tokens | <https://designsystem.porsche.com/v4/tokens/spacing/> | Spacing token values: fluid and static families | `.owlbear/research/1535-token-architecture-test-approach.md` | 2026-05-13 |

## Token Architecture Impl Research (Task #1543)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MDN prefers-color-scheme | <https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme> | CSS spec: media query for OS dark mode detection | `.owlbear/research/1543-token-architecture-impl.md` | 2026-05-14 |
| PDS v4 themeDark export | `@porsche-design-system/components-react/styles` (npm) | Authoritative dark HSL values for all color tokens | `.owlbear/research/1543-token-architecture-impl.md` | 2026-05-14 |
| PDS v4 shadow/radius/spacing exports | `@porsche-design-system/components-react/styles` (npm) | Non-color token reference values | `.owlbear/research/1543-token-architecture-impl.md` | 2026-05-14 |
| PDS v4 colorSchemeStyles | `@porsche-design-system/components-react/styles` (npm) | PDS native theme switching CSS structure, confirms dark values | `.owlbear/research/1543-token-architecture-impl.md` | 2026-05-14 |

## Column CSS Test Research (Task #1539)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| SO: vitest CSS styling test | <https://stackoverflow.com/questions/76571158/vitest-cannot-test-for-presence-of-specific-styling> | jsdom CSS cascade not implemented; use class presence or E2E | `.owlbear/research/1539-column-css-test-approach.md` | 2026-05-13 |
| jsdom CSS cascade PR | <https://github.com/jsdom/jsdom/pull/2690> | CSS cascade implementation status in jsdom | `.owlbear/research/1539-column-css-test-approach.md` | 2026-05-13 |

## Sidecar Collapse Toggle Test Research (Task #1541)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| WAI-ARIA aria-expanded guide | <https://www.webability.io/glossary/aria-expanded> | Disclosure widget pattern: aria-expanded + CSS state synchronization | `.owlbear/research/1541-sidecar-collapse-toggle-test-approach.md` | 2026-05-13 |

## Card Component CSS Test Research (Task #1538)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Vitest issue #1689 (getComputedStyle) | <https://github.com/vitest-dev/vitest/issues/1689> | Confirms JSDOM doesn't apply imported CSS to getComputedStyle | `.owlbear/research/1538-card-css-test-approach.md` | 2026-05-13 |
| SO: vitest cannot test for specific styling | <https://stackoverflow.com/questions/76571158/vitest-cannot-test-for-presence-of-specific-styling> | Community consensus: use E2E for computed styles, not jsdom | `.owlbear/research/1538-card-css-test-approach.md` | 2026-05-13 |

## PInlineNotification Modal Error Research (Task #1499)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Inline Notification examples (v3) | <https://designsystem.porsche.com/v3/components/inline-notification/examples/> | Usage patterns for actionLabel/actionIcon retry affordance and onDismiss binding | `.owlbear/research/cockpit-inline-notification-modal.md` | 2026-05-12 |

## Board Horizontal Scroll Fix Research (Task #1596)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| CSS-Tricks: auto-fill vs auto-fit | <https://css-tricks.com/auto-sizing-columns-css-grid-auto-fill-vs-auto-fit/> | auto-fit collapses empty tracks; auto-fill preserves them — neither overflows | `.owlbear/research/1596-board-horizontal-scroll-fix.md` | 2026-05-16 |
| MDN: repeat() CSS function | <https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/repeat> | `repeat(<integer>, ...)` creates exactly N tracks — forces overflow when total > container | `.owlbear/research/1596-board-horizontal-scroll-fix.md` | 2026-05-16 |
| SO: CSS grid no-wrap with auto-fill | <https://stackoverflow.com/questions/65844797/css-grid-only-columns-no-wrap-and-with-auto-fill-covering-end-gap> | Confirms auto-fill/auto-fit never overflow; integer count is the solution | `.owlbear/research/1596-board-horizontal-scroll-fix.md` | 2026-05-16 |

## PDS v4 Local Hosting Research (Task #1495)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 CDN docs | <https://designsystem.porsche.com/v4/must-know/performance/cdn/> | CDN architecture, China CDN config — confirms only `auto`/`cn` options | `.owlbear/research/1495-pds-v4-local-hosting.md` | 2026-05-12 |
| PDS v4 migration guide | <https://designsystem.porsche.com/v4/news/migration-guide/porsche-design-system/> | Breaking changes in v4: removed `getInitialStyles()`, mandatory global styles | `.owlbear/research/1495-pds-v4-local-hosting.md` | 2026-05-12 |

## Shell + Secondary CSS Test Research (Task #1542)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Vitest issue #1689 (getComputedStyle) | <https://github.com/vitest-dev/vitest/issues/1689> | Confirms jsdom doesn't apply imported CSS; file-based testing required | `.owlbear/research/1542-shell-secondary-css-test-approach.md` | 2026-05-13 |
| PDS GitHub `load()` source | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-js/projects/components-manager-cli/library-entry/with-prefix.ts> | Load function internals: hardcoded CDN URLs, cdn.url assignment | `.owlbear/research/1495-pds-v4-local-hosting.md` | 2026-05-12 |
| PDS GitHub issue #2701 | <https://github.com/porsche-design-system/porsche-design-system/issues/2701> | "Make Components-JS Prod Build configurable" — open since 2023, confirming no self-hosting support | `.owlbear/research/1495-pds-v4-local-hosting.md` | 2026-05-12 |
| PDS `getCDNBaseURL` utility | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/utils/getCDNBaseURL.ts> | Compile-time replaced with `document.porscheDesignSystem.cdn.url` in production builds | `.owlbear/research/1495-pds-v4-local-hosting.md` | 2026-05-12 |

## Theme Toggle Button Research (Task #1548)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| web.dev — Building a theme switch component | <https://web.dev/articles/building/a-theme-switch-component> | Canonical button + SVG + aria-label pattern, accessibility (aria-live), sun/moon animation | `.owlbear/research/1548-theme-toggle-button.md` | 2026-05-14 |
| next-themes (pacocoursey) | <https://github.com/pacocoursey/next-themes> | aria-label set to current theme value, 3-state toggle patterns | `.owlbear/research/1548-theme-toggle-button.md` | 2026-05-14 |

## PDS Global-Styles Import Research (Task #1594)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 React Getting Started | <https://designsystem.porsche.com/v4/developing/react/getting-started/> | Recommended `@import` path, Vite config, lightningcss exclusion | `.owlbear/research/1594-pds-global-styles-import.md` | 2026-05-16 |

## Empty State Illustration Prompts Research (Task #1551)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| UX Planet — Empty State Design Guide | <https://uxplanet.org/empty-state-design-a-practical-guide-94ad0adbda45> | Empty state patterns, structure, and design best practices | `.owlbear/research/1551-empty-state-illustration-prompts.md` | 2026-05-13 |
| Mockplus — 25 Best Empty State Examples | <https://www.mockplus.com/blog/post/empty-state-ui-design> | Inspiring empty state UI examples and templates | `.owlbear/research/1551-empty-state-illustration-prompts.md` | 2026-05-13 |

## Card CSS Implementation Research (Task #1546)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MDN: Kanban board with drag and drop | <https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/Kanban_board> | Drag opacity pattern: `opacity: 0.2` on original element during drag | `.owlbear/research/card-css-impl-1546.md` | 2026-05-14 |
| Penpot: Design tokens and CSS variables guide | <https://penpot.app/blog/the-developers-guide-to-design-tokens-and-css-variables/> | `:root` token architecture pattern, custom property inheritance | `.owlbear/research/card-css-impl-1546.md` | 2026-05-14 |

## Cockpit API Client Centralization Research (Task #1493)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Kent C. Dodds — Replace axios with a simple custom fetch wrapper | <https://kentcdodds.com/blog/replace-axios-with-a-simple-custom-fetch-wrapper> | Validates plain async function wrappers for same-origin SPAs | `.owlbear/research/cockpit-api-client-centralization.md` | 2026-05-12 |
| dev.to — Building a Type-Safe API Client in TypeScript | <https://dev.to/limacodes/building-a-type-safe-api-client-in-typescript-beyond-axios-vs-fetch-4a3i> | Typed wrapper functions eliminate fetch duplication | `.owlbear/research/cockpit-api-client-centralization.md` | 2026-05-12 |

## PDS Asset Sync Research (Task #1510)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS CDN core chunk (v4.1.0) | `https://cdn.ui.porsche.com/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` | Webpack chunk mapping (58 component → filename entries), Stencil lazy-load architecture | `.owlbear/research/1510-pds-asset-sync.md` | 2026-05-12 |
| PDS icon component chunk (v4.1.0) | `https://cdn.ui.porsche.com/porsche-design-system/components/porsche-design-system.icon.a77dc30fd842f982a230.js` | Icon name → filename mapping (290 entries) | `.owlbear/research/1510-pds-asset-sync.md` | 2026-05-12 |
| PDS vue-offline sample repo | <https://github.com/porsche-design-system/sample-integration-vue-offline> | Official offline hosting pattern (v3): patched npm package + `public/assets/` + postinstall; v4 offline support not yet available | `.owlbear/research/1510-pds-asset-sync.md` | 2026-05-12 |

## Playwright Mutation Error Banner E2E Research (Task #1509)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS `banner.tsx` source | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/components/banner/banner.tsx> | Shadow DOM structure, dismiss event, open prop | `.owlbear/research/1509-playwright-mutation-error-banner.md` | 2026-05-12 |
| PDS `banner.e2e.ts` | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components-js/tests/e2e/specs/banner.e2e.ts> | Playwright selectors for dismiss button, event testing patterns | `.owlbear/research/1509-playwright-mutation-error-banner.md` | 2026-05-12 |
| PDS Banner configurator (v3) | <https://designsystem.porsche.com/v3/components/banner/configurator/> | open/dismiss controlled pattern, dismiss event listener | `.owlbear/research/1509-playwright-mutation-error-banner.md` | 2026-05-12 |

## PDS Property Trap Validation (Task #1496)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS GitHub issue #2701 | <https://github.com/porsche-design-system/porsche-design-system/issues/2701> | Still "to be refined" — no native self-hosting config coming | `.owlbear/research/1496-pds-property-trap.md` | 2026-05-12 |
| MDN Object.defineProperty | <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/defineProperty> | Getter/setter descriptor spec, configurable flag behavior | `.owlbear/research/1496-pds-property-trap.md` | 2026-05-12 |
| MDN Reflect.set | <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Reflect/set> | Reflect.set respects target's defineProperty setters | `.owlbear/research/1496-pds-property-trap.md` | 2026-05-12 |

## CI/SAST Baseline Research (Task #1413)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Ruff S-rules / flake8-bandit | <https://pydevtools.com/handbook/how-to/how-to-enable-ruff-security-rules/> | S-rule coverage list; confirmed Ruff S-rules equivalent to Bandit | `.owlbear/research/1413-ci-sast-baseline.md` | 2026-05-08 |

## PDS Asset Version Check Research (Task #1512)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Vite Plugin API docs | <https://vite.dev/guide/api-plugin.html> | buildStart hook fires on both dev server start and build; inline plugin pattern | `.owlbear/research/1512-pds-version-check.md` | 2026-05-12 |
| Vite buildStart behavior (issue) | <https://github.com/vitejs/vite/issues/19607> | Confirms buildStart called for client env during dev; backward-compat behavior | `.owlbear/research/1512-pds-version-check.md` | 2026-05-12 |
| npm scripts docs | <https://docs.npmjs.com/cli/v11/using-npm/scripts/> | Pre/post hooks, script chaining options for standalone check approach | `.owlbear/research/1512-pds-version-check.md` | 2026-05-12 |
| Best SAST Tools for Python 2026 | <https://appsecsanta.com/sast-tools/sast-tools-for-python> | Tool comparison matrix; evaluated Semgrep, Bandit, CodeQL against existing stack | `.owlbear/research/1413-ci-sast-baseline.md` | 2026-05-08 |
| Semgrep vs Bandit comparison | <https://dev.to/rahulxsingh/semgrep-vs-bandit-python-security-scanning-compared-2026-5e5j> | Taint-analysis trade-offs; basis for "defer Semgrep" decision | `.owlbear/research/1413-ci-sast-baseline.md` | 2026-05-08 |

## SARIF Upload to GitHub Code Scanning (Task #1417)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MegaLinter SARIF Reporter docs | <https://megalinter.io/latest/reporters/SarifReporter/> | Canonical upload step template, SARIF file path `megalinter-report.sarif` | `.owlbear/research/1417-sarif-upload-code-scanning.md` | 2026-05-08 |
| GitHub docs — Uploading a SARIF file | <https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github> | Permissions (`security-events: write`, `actions: read`), category input, GHAS requirement | `.owlbear/research/1417-sarif-upload-code-scanning.md` | 2026-05-08 |
| github/codeql-action upload-sarif action.yml | <https://github.com/github/codeql-action/blob/main/upload-sarif/action.yml> | Action input parameters: sarif_file, category, wait-for-processing, token | `.owlbear/research/1417-sarif-upload-code-scanning.md` | 2026-05-08 |
| oxsecurity/megalinter SarifReporter.md | <https://github.com/oxsecurity/megalinter/blob/main/docs/reporters/SarifReporter.md> | Confirms file path and recommended workflow step | `.owlbear/research/1417-sarif-upload-code-scanning.md` | 2026-05-08 |

## Unowned Simple Swaps Research (Task #1634)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v3 link-pure examples | <https://designsystem.porsche.com/v3/components/link-pure/examples/> | PLinkPure props and host-href pattern, `icon` prop values, slot usage | `.owlbear/research/1634-unowned-simple-swaps.md` | 2026-05-17 |

## Legacy Audit Prompt (Task #1414)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Vulture — Python dead code finder | <https://github.com/jendrikseipp/vulture> | Detects unused functions, imports, unreachable code; structural inspiration for zero-caller heuristic | `.owlbear/research/1414-legacy-audit-prompt.md` | 2026-05-08 |
| Knip — JS/TS unused code finder | <https://github.com/webpro-nl/knip> | Finds unused files, dependencies, exports; category-based scan structure | `.owlbear/research/1414-legacy-audit-prompt.md` | 2026-05-08 |
| Ruff F401 — unused import rule | <https://github.com/astral-sh/ruff/issues/872> | Discussion of vulture-like dead code detection in ruff; confirms F401 covers imports | `.owlbear/research/1414-legacy-audit-prompt.md` | 2026-05-08 |

## Theme Toggle UI Test Research (Task #1540)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OneUptime — Unit Test React with Vitest | <https://oneuptime.com/blog/post/2026-01-15-unit-test-react-vitest-testing-library/view> | ThemeToggle test example: vi.mock Context, click toggle, assert text reflects state | `.owlbear/research/1540-theme-toggle-ui-test-approach.md` | 2026-05-13 |
| next-themes issue #21 — testing implementations | <https://github.com/pacocoursey/next-themes/issues/21> | ThemeSpy pattern, data-testid convention, fireEvent on toggle | `.owlbear/research/1540-theme-toggle-ui-test-approach.md` | 2026-05-13 |
| Stack Overflow — test theme toggler with RTL | <https://stackoverflow.com/questions/72561602> | userEvent.click toggle, assert visual state change | `.owlbear/research/1540-theme-toggle-ui-test-approach.md` | 2026-05-13 |

## Theme Bootstrap + useTheme Hook Testing Research (Task #1537)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| next-themes test suite | <https://github.com/pacocoursey/next-themes/blob/main/next-themes/__tests__/index.test.tsx> | localStorage mock, matchMedia mock, data-theme assertions, renderHook patterns | `.owlbear/research/theme-bootstrap-usetheme-testing.md` | 2026-05-13 |
| next-themes inline script | <https://github.com/pacocoursey/next-themes/blob/main/next-themes/src/script.ts> | Canonical bootstrap pattern: localStorage → validate → OS fallback → set attribute | `.owlbear/research/theme-bootstrap-usetheme-testing.md` | 2026-05-13 |
| tanstack-themes FOUC prevention | <https://deepwiki.com/juliusmarminge/tanstack-themes/3.3-theme-detection-and-fouc-prevention> | Synchronous script injection architecture, mode resolution logic | `.owlbear/research/theme-bootstrap-usetheme-testing.md` | 2026-05-13 |
| vitest-matchmedia-mock | <https://www.npmjs.com/package/vitest-matchmedia-mock> | Alternative matchMedia mock library; evaluated but not recommended (adds dependency) | `.owlbear/research/theme-bootstrap-usetheme-testing.md` | 2026-05-13 |

## MegaLinter uv.lock Exclusion & Ruff Src Fix (Task #1418)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MegaLinter — Trivy descriptor | <https://megalinter.io/latest/descriptors/repository_trivy/> | Trivy uses `project` CLI lint mode; FILTER_REGEX_EXCLUDE not applicable | Task #1418 body | 2026-05-08 |
| MegaLinter — Filtering files | <https://megalinter.io/latest/config-filtering/> | FILTER_REGEX_EXCLUDE "not applicable with linters using CLI lint mode project" | Task #1418 body | 2026-05-08 |
| MegaLinter — editorconfig-checker descriptor | <https://megalinter.io/latest/descriptors/editorconfig_editorconfig_checker/> | Uses `list_of_files` mode; IS affected by FILTER_REGEX_EXCLUDE | Task #1418 body | 2026-05-08 |

## Theme Bootstrap Script Implementation Research (Task #1545)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Static Signal — Dark Mode Without the Flash | <https://staticsignal.io/posts/dark-mode-without-the-flash/> | Canonical inline blocking script pattern, 3-piece architecture (vars + script + toggle) | `.owlbear/research/1545-theme-bootstrap-impl.md` | 2026-05-14 |
| dev.to (gaisdav) — Prevent Theme Flash in React | <https://dev.to/gaisdav/how-to-prevent-theme-flash-in-a-react-instant-dark-mode-switching-o20> | Vite/React implementation, localStorage + matchMedia + data-theme inline script | `.owlbear/research/1545-theme-bootstrap-impl.md` | 2026-05-14 |
| next-themes script.ts | <https://github.com/pacocoursey/next-themes/blob/main/next-themes/src/script.ts> | Production bootstrap: localStorage → validate → system fallback → updateDOM | `.owlbear/research/1545-theme-bootstrap-impl.md` | 2026-05-14 |
| next-themes index.tsx (ThemeScript injection) | <https://github.com/pacocoursey/next-themes/blob/main/next-themes/src/index.tsx#L165-L215> | Injection mechanism: dangerouslySetInnerHTML IIFE, nonce support | `.owlbear/research/1545-theme-bootstrap-impl.md` | 2026-05-14 |

## Pre-end_work Scoped Commit Check (Task #1412)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Git documentation — git-status | <https://git-scm.com/docs/git-status> | `--porcelain` output format and pathspec filtering semantics | `.owlbear/research/1412-pre-end-work-scoped-commit-check.md` | 2026-05-08 |

## AC Quality Skill Schema (Task #1404)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| NextGenAnalysts — AC best practices | <https://nextgenanalysts.co.uk/how-to-write-clear-and-concise-acceptance-criteria-with-practical-examples/> | 5 AC quality components: specific/measurable, testable, independent, user-focused, clear DoD; banned vague terms | `.owlbear/research/1404-ac-quality-skill-schema.md` | 2026-05-08 |
| Atlassian — Acceptance Criteria | <https://www.atlassian.com/work-management/project-management/acceptance-criteria> | AC as "testable statements focused on positive customer results" | `.owlbear/research/1404-ac-quality-skill-schema.md` | 2026-05-08 |
| AltexSoft — AC Purposes, Formats, Best Practices | <https://www.altexsoft.com/blog/acceptance-criteria-purposes-formats-and-best-practices/> | "Each AC must be independently testable with clear pass/fail scenarios" | `.owlbear/research/1404-ac-quality-skill-schema.md` | 2026-05-08 |

## Qdrant Persistence + Source Identity (Task #1320)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Qdrant local mode docs | <https://qdrant.tech/documentation/guides/installation/#local-mode> | `QdrantClient(path=...)` filesystem persistence without server | `.owlbear/research/1320-qdrant-persistence-source-identity-impl.md` | 2026-05-04 |

## Filter Accessibility Tests (Task #1254)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| WAI-ARIA APG Disclosure (Show/Hide) Pattern | <https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/> | `aria-expanded` + `aria-controls` on toggle button, panel `id`/`role="region"`/`aria-label` semantics, focus management on expand/collapse | `.owlbear/research/filter-accessibility-tests-1254.md` | 2026-05-03 |

## Real-Time Cockpit Updates (Task #1233)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| germano.dev — SSE vs WebSockets (2022, 263 HN comments) | <https://germano.dev/sse-websockets> | Technical deep-dive + live demo comparing SSE and WebSocket; confirmed SSE fits server→client-only push | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |
| digitalbiztalk.com — SSE vs WebSockets 2026 | `https://www.digitalbiztalk.com/` (exact article path unverified — domain unresolvable at 2026-05-01 validation) | Comparison article cited in original research; URL could not be independently confirmed | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |
| Medium — FastAPI SSE implementation (2025) | <https://mahdijafaridev.medium.com/implementing-server-sent-events-sse-with-fastapi-real-time-updates-made-simple-6492f8bfc154> | FastAPI-specific SSE howto; StreamingResponse + async generator pattern | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |
| sysid/sse-starlette (GitHub) | <https://github.com/sysid/sse-starlette> | Battle-tested SSE library for Starlette/FastAPI; EventSourceResponse, reconnect handling | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |
| samuelcolvin/watchfiles (GitHub) | <https://github.com/samuelcolvin/watchfiles> | Rust-backed async file watcher (Pydantic author); OS-native FSEvents/inotify, async-friendly API | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |
| uvicorn.org — Settings (concurrency limits) | <https://www.uvicorn.org/settings/> | Worker count, connection limits, async model reference for SSE deployment impact assessment | `.owlbear/research/1233-realtime-cockpit-updates.md` | 2026-04-30 |

## EventSource Client Implementation (Task #1235)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| WHATWG HTML Spec §9.2 — Server-sent events | <https://html.spec.whatwg.org/multipage/server-sent-events.html> | Normative EventSource API: readyState semantics (CONNECTING/OPEN/CLOSED), auto-reconnect behavior, connection failure rules, event parsing | `.owlbear/research/1235-eventsource-client-implementation.md` | 2026-05-01 |
| reactuse.com — useEventSource hook | <https://reactuse.com/browser/useeventsource/> | React hook pattern for EventSource: status tracking, open/close control, data extraction | `.owlbear/research/1235-eventsource-client-implementation.md` | 2026-05-01 |
| suqingdong/useEventSource (GitHub) | <https://github.com/suqingdong/useEventSource> | React SSE hook library: reconnect, terminate, data state management pattern | `.owlbear/research/1235-eventsource-client-implementation.md` | 2026-05-01 |

## useEventSource Hook (Task #1260)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| ReactUse — useEventSource | <https://reactuse.com/browser/useeventsource/> | React hook API pattern: status types (CONNECTING/CONNECTED/DISCONNECTED), autoReconnect options, open/close methods | `.owlbear/research/1260-useeventsource-hook.md` | 2026-05-01 |
| NepeinAV/react-sse-hooks (GitHub) | <https://github.com/NepeinAV/react-sse-hooks> | Provider-based SSE hook library: EventSourceProvider, useEventSource, useEventSourceListener patterns | `.owlbear/research/1260-useeventsource-hook.md` | 2026-05-01 |

## EventSourceProvider Context and useSSEEvent Hook (Task #1276)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| samouss/react-hooks-sse (GitHub) | <https://github.com/samouss/react-hooks-sse> | Prior art for React SSE context provider pattern (SSEProvider + useSSE); validated fixed-type-list + single-connection architecture | `.owlbear/research/1276-eventsource-provider-hook.md` | 2026-05-02 |

## Paused Polling Option (Task #1259)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Dan Abramov — Making setInterval Declarative with React Hooks | <https://overreacted.io/making-setinterval-declarative-with-react-hooks/> | Canonical `delay: null` pause pattern for React interval hooks; ref-based callback approach | `.owlbear/research/1259-paused-option-usepollingfetch.md` | 2026-05-01 |
| TanStack Query — `enabled` option | <https://tanstack.com/query/latest/docs/framework/react/guides/disabling-queries> | Industry-standard boolean pause pattern for React data-fetching hooks | `.owlbear/research/1259-paused-option-usepollingfetch.md` | 2026-05-01 |

## SSE Endpoint Implementation (Task #1234)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| sse-starlette v3.4.1 (PyPI) | <https://pypi.org/project/sse-starlette/> | EventSourceResponse API, configuration options, shutdown handling, test patterns | `.owlbear/research/1234-sse-endpoint-implementation.md` | 2026-05-01 |
| watchfiles v1.1.1 — awatch API docs | <https://watchfiles.helpmanual.io/api/watch/> | Async file watcher API: awatch signature, stop_event, debounce, filter, recursive params | `.owlbear/research/1234-sse-endpoint-implementation.md` | 2026-05-01 |

## Extend SSE to Decisions and Activity (Task #1236)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| watchfiles — awatch multi-path + recursive docs | <https://watchfiles.helpmanual.io/api/watch/> | Confirmed awatch(*paths) supports multiple dirs/files; recursive=True catches new subdirs | `.owlbear/research/1236-extend-sse-decisions-activity.md` | 2026-05-01 |
| sysid/sse-starlette — typed events (README v3.4.1) | <https://github.com/sysid/sse-starlette> | yield dict with "event" key for typed SSE events; EventSourceResponse configuration | `.owlbear/research/1236-extend-sse-decisions-activity.md` | 2026-05-01 |

## Version Field Semantics (Task #1170)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Docker Compose Spec — Version top-level element (obsolete) | <https://docs.docker.com/reference/compose-file/version-and-name/> | Precedent for deprecating config version field in favor of structure-based detection | `.owlbear/research/1170-version-field-semantics.md` | 2026-04-29 |

## Arch-Audit Prompt (Task #1150)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| mattpocock/skills improve-codebase-architecture | <https://github.com/mattpocock/skills/blob/main/improve-codebase-architecture/SKILL.md> | Module quality vocabulary and codebase-wide audit approach — inspiration for Depth, Leverage, Locality, Seam, and Deletion Test prompt structure | `share/prompts/arch-audit.prompt.md` | 2026-04-27 |

## M3.5 Proposal Round (Task #1148)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Ousterhout "Design It Twice" (A Philosophy of Software Design, Ch.11) | <https://thedeployguy.com/2019-06-16-a-philosophy-of-software-design-summary-part-2-cp10-end/> | Generate ≥2 radically different approaches, comparison reveals priorities | `.owlbear/research/1148-m3-5-proposal-round.md` | 2026-04-27 |
| mattpocock/skills design-an-interface | <https://github.com/mattpocock/skills/blob/main/design-an-interface/SKILL.md> | Parallel sub-agent design generation with constraint directives | `.owlbear/research/1148-m3-5-proposal-round.md` | 2026-04-27 |

## Kanban Board GREEN Phase (Task #933)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| @dnd-kit/react (npm) | <https://www.npmjs.com/package/@dnd-kit/react> | v0.4.0 pre-release, React 19 native, useDraggable/useDroppable/useSortable hooks | `.owlbear/research/933-kanban-board-green.md` | 2026-04-18 |
| @dnd-kit/core (npm) | <https://www.npmjs.com/package/@dnd-kit/core> | v6.3.1 stable, 13M/week, React 19 issues reported (#1654, #1747) | `.owlbear/research/933-kanban-board-green.md` | 2026-04-18 |
| @atlaskit/pragmatic-drag-and-drop (npm) | <https://www.npmjs.com/package/@atlaskit/pragmatic-drag-and-drop> | v1.8.0, framework-agnostic, Apache-2.0, 970K/week | `.owlbear/research/933-kanban-board-green.md` | 2026-04-18 |
| dnd-kit React 19 issues | <https://github.com/clauderic/dnd-kit/issues?q=react+19> | Open issues: #1654 use-client, #1747 removeChild, #1940 sortable lists | `.owlbear/research/933-kanban-board-green.md` | 2026-04-18 |

## CI Sync SPA Bundle (Task #938)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| actions/setup-node docs | <https://github.com/actions/setup-node> | node-version-file, cache options, v4 API | `.owlbear/research/938-ci-sync-spa-bundle.md` | 2026-04-19 |

## Kanban Board RED Tests (Task #931)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| RTL Example + MSW recommendation | <https://testing-library.com/docs/react-testing-library/example-intro> | MSW for API mocking, fetch-level mock pattern, async test patterns | `.owlbear/research/931-kanban-board-tests.md` | 2026-04-18 |
| RTL user-event setup | <https://testing-library.com/docs/user-event/setup> | userEvent.setup() session pattern, DnD limitations in jsdom | `.owlbear/research/931-kanban-board-tests.md` | 2026-04-18 |

## App Shell RED Phase — Test Strategy (Task #927)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Router v7 API docs | <https://api.reactrouter.com/v7> | MemoryRouter test wrapper pattern, initialEntries, unified `react-router` package structure in v7 | `.owlbear/research/927-app-shell-tests.md` | 2026-04-18 |
| React Router v7 install + routing guide | <https://reactrouter.com> | `npm install react-router` install step, Routes/Route/Outlet layout pattern | `.owlbear/research/927-app-shell-tests.md` | 2026-04-18 |

## Cockpit Launch Command (Task #937)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastAPI StaticFiles docs | <https://fastapi.tiangolo.com/tutorial/static-files/> | StaticFiles mount pattern, constructor args | `.owlbear/research/937-cockpit-launch-command.md` | 2026-04-19 |
| Starlette StaticFiles source | <https://github.com/encode/starlette/blob/master/starlette/staticfiles.py> | html=True behavior — does NOT fallback to root index.html for deep routes | `.owlbear/research/937-cockpit-launch-command.md` | 2026-04-19 |
| Starlette StaticFiles docs | <https://starlette.dev/staticfiles/> | html parameter, check_dir parameter | `.owlbear/research/937-cockpit-launch-command.md` | 2026-04-19 |
| FastAPI Lifespan Events | <https://fastapi.tiangolo.com/advanced/events/> | asynccontextmanager lifespan pattern | `.owlbear/research/937-cockpit-launch-command.md` | 2026-04-19 |

## Planner askQuestions Approval (Task #998)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | Handoffs, tool lists, user-invocable/disable-model-invocation flags, agent file structure | `.owlbear/research/998-planner-askquestions-approval.md` | 2026-04-18 |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | Subagent isolation model, coordinator patterns, custom agent as subagent, tool inheritance | `.owlbear/research/998-planner-askquestions-approval.md` | 2026-04-18 |

## Shell Traffic-Light State Wiring (Task #966)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React docs: Passing Data Deeply with Context | <https://react.dev/learn/passing-data-deeply-with-context> | createContext/useContext pattern, when to use context vs props | `.owlbear/research/966-shell-traffic-light-wiring.md` | 2026-04-18 |

## E2E Kanban Board Tests: DnD, Density, Scroll (Task #957)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright Mouse API | <https://playwright.dev/docs/api/class-mouse> | `mouse.down()`, `mouse.move()`, `mouse.up()`, `mouse.wheel()` for DnD and scroll testing | `.owlbear/research/957-e2e-kanban-dnd-density-scroll.md` | 2026-04-18 |

## React Compiler Enablement (Tasks #970, #971, #1015)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler introduction | <https://react.dev/learn/react-compiler/introduction> | Stability, scope, and opt-out strategy | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler installation | <https://react.dev/learn/react-compiler/installation> | Vite config: `react({ babel: { plugins: ['babel-plugin-react-compiler'] } })` | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler debugging | <https://react.dev/learn/react-compiler/debugging> | Breaking patterns, `"use no memo"` escape hatch | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler directives | <https://react.dev/reference/react-compiler/directives> | `"use memo"`/`"use no memo"` per-component opt-out | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler incremental adoption | <https://react.dev/learn/react-compiler/incremental-adoption> | `compilationMode`, per-file overrides | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler configuration | <https://react.dev/reference/react-compiler/configuration> | `panicThreshold: 'none'`, silent skip behavior | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| Playwright Locator.boundingBox() | <https://playwright.dev/docs/api/class-locator#locator-bounding-box> | Returns `{x, y, width, height}` for card density measurement | `.owlbear/research/957-e2e-kanban-dnd-density-scroll.md` | 2026-04-18 |
| Playwright DnD + Scrolling guide | <https://playwright.dev/docs/input#drag-and-drop> | Manual drag pattern, double mouse-move requirement for dragover, `mouse.wheel()` scroll pattern | `.owlbear/research/957-e2e-kanban-dnd-density-scroll.md` | 2026-04-18 |

## Cockpit Read API GREEN Phase (Task #930)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastAPI Dependency Injection | <https://fastapi.tiangolo.com/tutorial/dependencies/> | `Depends()` pattern for `get_engine` DI callable, `dependency_overrides` in tests | `.owlbear/research/930-cockpit-read-api-green.md` | 2026-04-18 |
| PDS v3.34 Tabs examples + API | <https://designsystem.porsche.com/v3> | PTabs/PTabsItem custom element tags, `activeTabIndex` prop, `label` prop, jsdom tab-switch event behaviour | `.owlbear/research/927-app-shell-tests.md` | 2026-04-18 |

## KanbanBoard Memoization (Task #963)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React.memo API reference | <https://react.dev/reference/react/memo> | Shallow prop comparison, React Compiler note, custom comparator API | `.owlbear/research/963-memoize-kanbanboard.md` | 2026-04-18 |
| useMemo API reference | <https://react.dev/reference/react/useMemo> | Caching calculations, dependency semantics, memo+useMemo synergy pattern | `.owlbear/research/963-memoize-kanbanboard.md` | 2026-04-18 |
| useCallback API reference | <https://react.dev/reference/react/useCallback> | Function caching, equivalent to useMemo returning function, hook ordering rules | `.owlbear/research/963-memoize-kanbanboard.md` | 2026-04-18 |

## React Compiler Trigger Reassessment (Task #971)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler installation docs | <https://react.dev/learn/react-compiler/installation> | Install steps (`babel-plugin-react-compiler`), vite.config.ts plugin wiring, `"use no memo"` opt-out directive | `.owlbear/research/971-react-compiler-trigger-reassessment.md` | 2026-04-19 |

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler installation docs | <https://react.dev/learn/react-compiler/installation> | babel-plugin-react-compiler, Vite config, React 19 support, ESLint integration | `.owlbear/research/971-react-compiler-trigger-reassessment.md` | 2026-04-19 |

## Sidecar GREEN Gaps (Task #936)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| react-markdown npm (v10.1.0) | <https://www.npmjs.com/package/react-markdown> | Safe by default, no dSIH, HTML escaped; rehypeSanitize is no-op without rehypeRaw | `.owlbear/research/936-sidecar-green-gaps.md` | 2026-04-18 |
| remark-gfm npm (v4.0.1) | <https://www.npmjs.com/package/remark-gfm> | GFM plugin for remark — tables, strikethrough, task lists; required for task body rendering | `.owlbear/research/936-sidecar-green-gaps.md` | 2026-04-18 |
| rehype-sanitize npm (v6.0.0) | <https://www.npmjs.com/package/rehype-sanitize> | Sanitizes HTML in hast tree; defaultSchema follows GitHub-style sanitation | `.owlbear/research/936-sidecar-green-gaps.md` | 2026-04-18 |

## React Compiler Evaluation (Task #969)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler introduction | <https://react.dev/learn/react-compiler/introduction> | Stability statement, 1.0.0 stable, supported React versions | `.owlbear/research/969-react-compiler-evaluation.md` | 2026-04-18 |
| React Compiler installation | <https://react.dev/learn/react-compiler/installation> | Vite config (3 LOC), babel plugin setup, devDep | `.owlbear/research/969-react-compiler-evaluation.md` | 2026-04-18 |
| babel-plugin-react-compiler (npm) | <https://www.npmjs.com/package/babel-plugin-react-compiler> | v1.0.0, 7.6M weekly downloads, integration LOC | `.owlbear/research/969-react-compiler-evaluation.md` | 2026-04-18 |
| react-compiler-runtime (npm) | <https://www.npmjs.com/package/react-compiler-runtime> | v1.0.0, 0 dependencies, runtime companion | `.owlbear/research/969-react-compiler-evaluation.md` | 2026-04-18 |

## React Compiler + PDS Interop (Task #970)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler introduction | <https://react.dev/learn/react-compiler/introduction> | Stability, scope, what the compiler does | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler installation | <https://react.dev/learn/react-compiler/installation> | Vite config, babel plugin setup | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler debugging | <https://react.dev/learn/react-compiler/debugging> | Breaking patterns, "use no memo" directive | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler directives | <https://react.dev/reference/react-compiler/directives> | "use memo"/"use no memo" opt-in/out | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler incremental adoption | <https://react.dev/learn/react-compiler/incremental-adoption> | Annotation mode, overrides for gradual rollout | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler configuration | <https://react.dev/reference/react-compiler/configuration> | compilationMode, panicThreshold settings | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| Rules of React | <https://react.dev/reference/rules> | Purity, side effects, immutability — compiler contract | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| Vitest coverage drop — reactwg/react-compiler#78 | <https://github.com/reactwg/react-compiler/discussions/78> | Compiler-generated branches inflate coverage branch count | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |

## useBoard Polling GREEN Implementation (Task #967)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React docs: useEffect | <https://react.dev/reference/react/useEffect> | Cleanup, setInterval pattern, fetch-in-effect, StrictMode double-mount | `.owlbear/research/967-useboard-polling-green.md` | 2026-04-18 |
| MDN: AbortController | <https://developer.mozilla.org/en-US/docs/Web/API/AbortController> | Signal/abort API, fetch cancellation, browser compat | `.owlbear/research/967-useboard-polling-green.md` | 2026-04-18 |

## TanStack Query vs Plain Polling Research (Task #960)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| TanStack Query v5 docs — overview | <https://tanstack.com/query/latest/docs/framework/react/overview> | Architecture, QueryClient, structural sharing, stale-while-revalidate semantics | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — polling guide | <https://tanstack.com/query/latest/docs/framework/react/guides/polling> | `refetchInterval`, `refetchIntervalInBackground`, polling lifecycle | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — testing guide | <https://tanstack.com/query/latest/docs/framework/react/guides/testing> | QueryClientProvider wrapper pattern, test isolation with createQueryClient | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — important defaults | <https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults> | 3-retry default, staleTime=0, gcTime semantics | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| @tanstack/react-query (npm) | <https://www.npmjs.com/package/@tanstack/react-query> | v5.x bundle size (~15-20 KB gzip), peer deps, changelog | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |

## Sidecar + Polling RED Tests (Task #935)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| react-markdown npm docs | <https://www.npmjs.com/package/react-markdown> | v10.1.0, safe by default (no dangerouslySetInnerHTML), skipHtml option, rehype-sanitize for strict mode | `.owlbear/research/935-sidecar-detail-activity-polling-tests.md` | 2026-04-18 |
| Vitest mocking guide | <https://vitest.dev/guide/mocking.html> | vi.useFakeTimers, vi.stubGlobal, vi.mock factory patterns for polling and module mocking | `.owlbear/research/935-sidecar-detail-activity-polling-tests.md` | 2026-04-18 |
| RTL introduction | <https://testing-library.com/docs/react-testing-library/intro> | renderHook API in v16, data-testid pattern, user-behavior-first testing philosophy | `.owlbear/research/935-sidecar-detail-activity-polling-tests.md` | 2026-04-18 |

## Frontend Scaffold Feasibility (Task #925)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS React wrapper (npm) | <https://www.npmjs.com/package/@porsche-design-system/components-react> | Peer deps (React >=19), exports map, single JS dependency | `.owlbear/research/925-frontend-scaffold.md` | 2026-04-18 |
| PDS React getting-started | <https://designsystem.porsche.com/v3/developing/react/getting-started> | Vite integration steps, PorscheDesignSystemProvider, partials plugin, Tailwind theme | `.owlbear/research/925-frontend-scaffold.md` | 2026-04-18 |
| PDS React testing | <https://designsystem.porsche.com/v3/developing/react/testing> | jsdom polyfill, componentsReady, shadow DOM query utilities, CDN request suppression | `.owlbear/research/925-frontend-scaffold.md` | 2026-04-18 |
| PDS License | <https://github.com/porsche-design-system/porsche-design-system/blob/main/LICENSE.md> | Dual license: Apache 2.0 source code + custom restrictive design assets license | `.owlbear/research/925-frontend-scaffold.md` | 2026-04-18 |
| PDS Theme styles | <https://designsystem.porsche.com/v3/styles/theme> | Design token exports: JS, SCSS, vanilla-extract, Tailwind CSS theme | `.owlbear/research/925-frontend-scaffold.md` | 2026-04-18 |

## Context Menu Dismiss + A11y RED Tests (Task #962)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| WAI-ARIA APG Menu Pattern | <https://www.w3.org/WAI/ARIA/apg/patterns/menu/> | `role="menu"` + `role="menuitem"` requirements, Escape closes menu, keyboard interaction spec | `.owlbear/research/962-context-menu-dismiss-a11y.md` | 2026-04-18 |
| RTL fireEvent API | <https://testing-library.com/docs/dom-testing-library/api-events> | `fireEvent.keyDown(node, {key:'Escape'})`, `fireEvent.mouseDown(node)` patterns for dismiss testing | `.owlbear/research/962-context-menu-dismiss-a11y.md` | 2026-04-18 |

## Frontend Perf Benchmark + Virtualization (Task #959)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| react-virtuoso (npm) | <https://www.npmjs.com/package/react-virtuoso> | v4.18.5, 57KB min / 18.4KB gzip, 0 deps, 2.5M/wk, built-in DnD scroll support | `.owlbear/research/959-frontend-perf-virtualization.md` | 2026-04-18 |
| react-window (npm) | <https://www.npmjs.com/package/react-window> | v2.2.7, 12.5KB min / 6.5KB gzip, 0 deps, 5.4M/wk, fixed-height List/Grid | `.owlbear/research/959-frontend-perf-virtualization.md` | 2026-04-18 |
| Bundlephobia: react-virtuoso | <https://bundlephobia.com/package/react-virtuoso@4.18.5> | Bundle composition: 100% self, tree-shakeable, side-effect free | `.owlbear/research/959-frontend-perf-virtualization.md` | 2026-04-18 |
| Bundlephobia: react-window | <https://bundlephobia.com/package/react-window@2.2.7> | Bundle composition: 100% self, tree-shakeable | `.owlbear/research/959-frontend-perf-virtualization.md` | 2026-04-18 |
| Vitest bench API | <https://vitest.dev/api/#bench> | Experimental Tinybench-based benchmarking, `bench()` function, statistical output | `.owlbear/research/959-frontend-perf-virtualization.md` | 2026-04-18 |

> **TODO:** stale — duplicate section heading for Task #970 (MD024); merge with first occurrence above [#1495]

## React Compiler + PDS Interop (Task #970)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler introduction | <https://react.dev/learn/react-compiler/introduction> | Stability statement, scope, useMemo/useCallback guidance | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler installation | <https://react.dev/learn/react-compiler/installation> | Vite Babel plugin config, DevTools verification, "use no memo" | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler debugging | <https://react.dev/learn/react-compiler/debugging> | Breaking patterns, runtime vs build errors, "use no memo" workflow | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler directives | <https://react.dev/reference/react-compiler/directives> | "use memo"/"use no memo", compilationMode interaction, best practices | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler incremental adoption | <https://react.dev/learn/react-compiler/incremental-adoption> | Babel overrides, annotation mode, runtime gating | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| React Compiler configuration | <https://react.dev/reference/react-compiler/configuration> | compilationMode, panicThreshold, logger, gating options | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| Vitest coverage drop with React Compiler | <https://github.com/reactwg/react-compiler/discussions/78> | Known issue: compiler-generated branches inflate branch count, no source-map fix | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |
| Rules of React | <https://react.dev/reference/rules> | Purity, side effects outside render, immutability rules compiler relies on | `.owlbear/research/970-react-compiler-pds-interop.md` | 2026-04-18 |

## TanStack Query vs Plain Polling (Task #960)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| TanStack Query v5 — overview | <https://tanstack.com/query/latest/docs/framework/react/overview> | Core concepts: server state caching, dedup, structural sharing, stale-while-revalidate | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — polling guide | <https://tanstack.com/query/latest/docs/framework/react/guides/polling> | `refetchInterval` API, conditional polling via function, background polling, dedup semantics | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — testing guide | <https://tanstack.com/query/latest/docs/framework/react/guides/testing> | QueryClientProvider wrapper, retry:false, gcTime:Infinity for test isolation | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| TanStack Query — important defaults | <https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults> | staleTime, structuralSharing, refetchOnWindowFocus, retry defaults | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |
| @tanstack/react-query (npm) | <https://www.npmjs.com/package/@tanstack/react-query> | v5.99.0, 1 dep, 47M/wk, MIT, ~15-20KB gzipped total | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 2026-04-18 |

## Mtime Cache for list_tasks() (Task #941)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Python os.scandir/DirEntry docs | <https://docs.python.org/3/library/os.html#os.scandir> | DirEntry.stat() behavior on Unix (requires syscall), st_mtime_ns type (int, nanoseconds) | `.owlbear/research/mtime-cache-941.md` | 2026-04-17 |

## Cockpit Layout Validation (Task #922)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Porsche DS Grid styles | <https://designsystem.porsche.com/v3/styles/grid> | Grid primitives, spacing tokens, fluid column system | `.owlbear/research/922-cockpit-layout-mockup.md` | 2026-04-17 |
| Pragmatic Drag-and-Drop | <https://github.com/atlassian/pragmatic-drag-and-drop> | Atlassian kanban board drag patterns (Trello/Jira reference) | `.owlbear/research/922-cockpit-layout-mockup.md` | 2026-04-17 |

## PreToolUse Guard Hooks Test Approach (Task #891)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Hooks docs — PreToolUse I/O | <https://code.visualstudio.com/docs/copilot/customization/hooks> | PreToolUse hook I/O contract: stdin JSON schema, stdout allow/deny format, exit code semantics, fail-open spec | `.owlbear/research/891-pretooluse-hooks-test-approach.md` | 2026-04-17 |

## E2E Kanban Board Tests (Task #955)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright intro + installation | <https://playwright.dev/docs/intro> | Setup, webServer config, headless/headed modes, CI story | `.owlbear/research/955-e2e-kanban-board-tests.md` | 2026-04-18 |
| Playwright DnD + scrolling | <https://playwright.dev/docs/input#drag-and-drop> | `locator.dragTo()`, manual drag via `mouse.down()/move()/up()`, `mouse.wheel()`, `scrollIntoViewIfNeeded()` | `.owlbear/research/955-e2e-kanban-board-tests.md` | 2026-04-18 |
| Playwright Locator API — boundingBox | <https://playwright.dev/docs/api/class-locator#locator-bounding-box> | `boundingBox()` returns `{x,y,width,height}` for layout measurement | `.owlbear/research/955-e2e-kanban-board-tests.md` | 2026-04-18 |
| Vitest Browser Mode | <https://vitest.dev/guide/browser/> | Browser mode setup, Playwright provider, projects config, limitations | `.owlbear/research/955-e2e-kanban-board-tests.md` | 2026-04-18 |
| Vitest Component Testing | <https://vitest.dev/guide/browser/component-testing> | Component testing patterns, `vitest-browser-react`, Testing Library integration | `.owlbear/research/955-e2e-kanban-board-tests.md` | 2026-04-18 |

## SSRF Surface in BrowserContentFetcher (Task #949)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright page.goto() docs | <https://playwright.dev/python/docs/api/class-page#page-goto> | No IP+Host header support; follows redirects by default; URL string only | `.owlbear/research/949-ssrf-browser-fetcher.md` | 2026-04-18 |
| Playwright browser_context.route() docs | <https://playwright.dev/python/docs/api/class-browsercontext#browser-context-route> | Route interception pattern for blocking requests by URL/predicate | `.owlbear/research/949-ssrf-browser-fetcher.md` | 2026-04-18 |
| Playwright Network docs | <https://playwright.dev/python/docs/network> | Request interception, modification, and abort patterns | `.owlbear/research/949-ssrf-browser-fetcher.md` | 2026-04-18 |

## SSRF Pre-Flight Check for navigate() (Task #950)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright page.goto() docs | <https://playwright.dev/python/docs/api/class-page#page-goto> | No IP+Host header support; Playwright constraint on TOCTOU mitigation | `.owlbear/research/950-ssrf-browser-navigate.md` | 2026-04-18 |
| OwlBear #946 `_is_blocked_ip` implementation | Internal: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L156-175 | Proven SSRF IP blocklist pattern for duplication | `.owlbear/research/950-ssrf-browser-navigate.md` | 2026-04-18 |

## App Shell GREEN Phase (Task #929)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Router v7 library routing docs | <https://reactrouter.com/start/library/routing> | BrowserRouter, layout routes, Outlet pattern, nested route config | `.owlbear/research/929-app-shell-green.md` | 2026-04-18 |
| React Router v7 installation guide | <https://reactrouter.com/start/library/installation> | BrowserRouter wrapper pattern for Vite/React apps | `.owlbear/research/929-app-shell-green.md` | 2026-04-18 |

## Copilot SDK vs OpenAI-Compat Endpoint Research (Task #887)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| github-copilot-sdk PyPI | <https://pypi.org/project/github-copilot-sdk/> | MIT | SDK API surface (v0.2.2): session-based event-driven chat, no `response_format` support, BYOK, auth methods, tool definitions | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` | 2026-04-15 |
| GitHub Copilot SDK repo | <https://github.com/github/copilot-sdk> | MIT | Architecture (JSON-RPC ↔ Copilot CLI), models, FAQ (auth, billing, BYOK), getting-started guide | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` | 2026-04-15 |
| copilot-api (ericc-ch) | <https://github.com/ericc-ch/copilot-api> | MIT | Reverse-engineered OpenAI-compat proxy for Copilot: endpoints (`/v1/chat/completions`, `/v1/models`), auth flow, rate-limit controls, GitHub ToS/abuse-detection warnings | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` | 2026-04-15 |
| GitHub Copilot Requests docs | <https://docs.github.com/en/copilot/concepts/billing/copilot-requests> | N/A | Premium request model, model multipliers (GPT-4.1 = 0×, GPT-5 mini = 0× on paid plans), rate limits, quota behavior | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` | 2026-04-15 |

## Copilot SDK Monitoring Check (Task #889)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Copilot SDK CHANGELOG.md | <https://github.com/github/copilot-sdk/blob/main/CHANGELOG.md> | v0.2.0–v0.2.2 changelog: confirmed no `response_format` or completions API added | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` (monitoring update) | 2026-04-15 |
| Copilot SDK Issue #857 | <https://github.com/github/copilot-sdk/issues/857> | "Force structured output" — open feature request, no milestone | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` (monitoring update) | 2026-04-15 |
| PyPI github-copilot-sdk v0.2.2 | <https://pypi.org/project/github-copilot-sdk/> | SDK API surface: session-based, no `response_format`, BYOK `wire_api` field (custom providers only) | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` (monitoring update) | 2026-04-15 |

## Session-Context Python Port (Task #896)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Hooks docs — SessionStart I/O | <https://code.visualstudio.com/docs/copilot/customization/hooks> | SessionStart hook stdin/stdout JSON contract, fail-open spec | `.owlbear/research/896-session-context-py-port.md` | 2026-04-17 |

## Copilot Auth Port Feasibility (Task #888)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| github-copilot-sdk PyPI (v0.2.2 recheck) | <https://pypi.org/project/github-copilot-sdk/> | Confirmed: still no `response_format`, BYOK routes through CLI subprocess, session/event API only | `.owlbear/research/888-copilot-auth-port-feasibility.md` | 2026-04-15 |
| copilot-api proxy (ericc-ch, recheck) | <https://github.com/ericc-ch/copilot-api> | 3.7k stars, explicit abuse-detection warnings added, confirms risk is actively enforced | `.owlbear/research/888-copilot-auth-port-feasibility.md` | 2026-04-15 |
| Graphicator | `C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator` | (own project) \ Device-flow OAuth implementation ported to `copilot_auth.py`: `request_device_code`, `poll_for_access_token`, `exchange_for_copilot_token`, token cache, editor headers | `serve/knowledge/src/owlbear_knowledge/copilot_auth.py` | 2026-04-15 |

## Entity Name Canonicalization (Task #865)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| ScrapingAnt: Deduplication & Canonicalization in Scraped KGs | <https://scrapingant.com/blog/data-deduplication-and-canonicalization-in-scraped> | Blocking/candidate generation pipeline; canonical_name as blocking key; rule-based vs ML vs hybrid approaches | .owlbear/research/865-entity-name-canonicalization.md | 2026-04-14 |
| SpotIntelligence: Entity Resolution Techniques | <https://spotintelligence.com/2024/01/22/entity-resolution/> | Rule-based matching, string similarity measures, clustering approaches for entity deduplication | .owlbear/research/865-entity-name-canonicalization.md | 2026-04-14 |

## StructuredExtractor Replacement Research (Task #874)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OpenAI Python SDK — Structured Outputs | <https://developers.openai.com/api/docs/guides/structured-outputs> | Native `response_format` with Pydantic JSON schema, `AsyncOpenAI` async client | .owlbear/research/874-structuredextractor-replacement.md | 2026-04-14 |
| LiteLLM — Structured Outputs (JSON Mode) | <https://docs.litellm.ai/docs/completion/json_mode> | `response_format` with Pydantic models, multi-provider support, dep count analysis | .owlbear/research/874-structuredextractor-replacement.md | 2026-04-14 |
| Instructor — Structured LLM Outputs | <https://python.useinstructor.com/> | `response_model` abstraction, retry/validation, Pydantic integration | .owlbear/research/874-structuredextractor-replacement.md | 2026-04-14 |
| Kuboid — LiteLLM Supply Chain Attack March 2026 | <https://www.kuboid.in/blog/litellm-supply-chain-attack-march-2026-explained> | TeamPCP/LAPSUS$ credential stealer in v1.82.7-8, releases paused | .owlbear/research/874-structuredextractor-replacement.md | 2026-04-14 |

## LLMExtractor Implementation Research (Task #875)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OpenAI Structured Outputs guide | <https://developers.openai.com/api/docs/guides/structured-outputs> | Strict JSON schema, `response_format`, Pydantic support, refusal handling | .owlbear/research/875-llmextractor-openai-implementation.md | 2026-04-14 |
| openai-python SDK helpers.md | <https://github.com/openai/openai-python/blob/main/helpers.md> | `chat.completions.parse()` API, auto-schema from Pydantic, `ParsedChatCompletion` | .owlbear/research/875-llmextractor-openai-implementation.md | 2026-04-14 |

## SharePoint REST API Parallel Path Research (Task #773)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Microsoft Graph SharePoint API overview | <https://learn.microsoft.com/en-us/graph/api/resources/sharepoint?view=graph-rest-1.0> | Site/list/drive API surface, URL addressing patterns | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 2026-04-14 |
| Graph API sitePage + canvasLayout | <https://learn.microsoft.com/en-us/graph/api/sitepage-get?view=graph-rest-1.0> | Page content extraction via $expand=canvasLayout, web part innerHtml, permissions (Sites.Read.All) | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 2026-04-14 |
| Sites.Selected delegated auth announcement | <https://devblogs.microsoft.com/microsoft365dev/sharepoint-now-supports-delegated-sites-selected-authentication/> | Granular per-site delegated permission scope (Feb 2024) | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 2026-04-14 |
| Office365-REST-Python-Client (vgrem) | <https://pypi.org/project/Office365-REST-Python-Client/> | Python library for SharePoint REST + Graph API, MSAL integration, dep analysis | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 2026-04-14 |
| MSAL Python docs | <https://msal-python.readthedocs.io/en/latest/> | Auth library for Azure AD token acquisition (device-code, interactive, client-credentials) | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 2026-04-14 |

## GraphContentFetcher Implementation Research (Task #879)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| canvasLayout v1.0 API reference | <https://learn.microsoft.com/en-us/graph/api/resources/canvaslayout?view=graph-rest-1.0> | canvasLayout resource structure, horizontalSections/verticalSection relationships | .owlbear/research/879-graphcontentfetcher-implementation.md | 2026-04-14 |
| SE: retrieve modern SP page content | <https://sharepoint.stackexchange.com/questions/307632> | Community confirmation that $expand=canvasLayout works in v1.0 for modern pages | .owlbear/research/879-graphcontentfetcher-implementation.md | 2026-04-14 |
| msgraph-sdk-python (v1.55.0) | <https://github.com/microsoftgraph/msgraph-sdk-python> | SDK dep analysis: kiota-*, azure-core, 15+ transitive deps — confirms Option A preferred | .owlbear/research/879-graphcontentfetcher-implementation.md | 2026-04-14 |
| azure-identity vs msal comparison | <https://www.datalineo.com/post/power-bi-rest-api-with-python-part-iii-azure-identity> | azure-identity wraps msal, adds azure-core layer; raw msal is lighter | .owlbear/research/879-graphcontentfetcher-implementation.md | 2026-04-14 |

## Edge CDP Validation Spike (Task #752)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | CDP connection API: endpoint_url, is_local param, default context access | .owlbear/research/cdp-spike-752.md | 2026-04-10 |
| Chrome 136 remote-debugging-port restriction | <https://developer.chrome.com/blog/remote-debugging-port> | Critical: `--remote-debugging-port` requires `--user-data-dir` to non-default dir from Chrome 136+ | .owlbear/research/cdp-spike-752.md | 2026-04-10 |

## Migrate task_io.py from PyYAML to ruamel.yaml (Task #827)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| ruamel.yaml Basic Usage | <https://yaml.dev/doc/ruamel.yaml/basicuse/> | safe/rt modes, StringIO dump pattern, YAML instance API | .owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md | 2026-04-12 |
| ruamel.yaml Differences with PyYAML | <https://yaml.dev/doc/ruamel.yaml/pyyaml/> | YAML 1.1→1.2 behavioral changes: booleans, octals, sexagesimals | .owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md | 2026-04-12 |
| Playwright `launch_persistent_context` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context> | Alternative approach: Playwright-managed Edge lifecycle with channel="msedge" | .owlbear/research/cdp-spike-752.md | 2026-04-10 |
| Playwright Chrome Extensions docs | <https://playwright.dev/python/docs/chrome-extensions> | Confirms Edge removed `--load-extension` flags; `--remote-debugging-port` still usable | .owlbear/research/cdp-spike-752.md | 2026-04-10 |

## Actor Field in Activity Log Tests (Task #811)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PocketPaw Audit Log docs | <https://pocketpaw.xyz/security/audit-log/> | JSONL audit log with `session_id`+`channel` fields for consumer identity; append-only semantics | .owlbear/research/811-actor-field-activity-log-tests.md | 2026-04-12 |
| tundere-ledger (PyPI) | <https://pypi.org/project/tundere-ledger/> | Python JSONL audit log decorator with `actor_name` parameter for attribution | .owlbear/research/811-actor-field-activity-log-tests.md | 2026-04-12 |

## Fix Timestamp Sort (Task #816)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Python datetime docs — fromisoformat | <https://docs.python.org/3/library/datetime.html> | fromisoformat() handles arbitrary fractional digits (truncated to 6); aware comparison normalizes to UTC | .owlbear/research/fix-timestamp-sort-816.md | 2026-04-12 |
| DEV Community — Sorting ISO 8601 timestamps | <https://dev.to/adnauseum/sorting-iso-8601-timestamps-5am2> | Confirms ISO 8601 string sort fails across different timezone offsets | .owlbear/research/fix-timestamp-sort-816.md | 2026-04-12 |

## Source-Aware Candidate Filtering (Task #863)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Kumar et al. (2025) — Enterprise KG multi-source integration | <https://arxiv.org/abs/2503.07993> | Cross-source entity matching via embedding + LLM mapper; context for sort-first prioritization approach | .owlbear/research/863-source-aware-candidate-filtering.md | 2026-04-14 |
| Saeedi et al. (2020) — Incremental multi-source entity resolution | ESWC 2020 proceedings (no URL in research doc) | Multi-source entity resolution for KG completion; context for cross-source bucket strategy | .owlbear/research/863-source-aware-candidate-filtering.md | 2026-04-14 |
| Kumar et al. (2025) — LLM-Powered KGs for Enterprise Intelligence | <https://arxiv.org/html/2503.07993v1> | Enterprise KG integrating multiple data sources via LLM entity extraction and embedding-based matching | .owlbear/research/863-source-aware-candidate-filtering.md | 2026-04-14 |
| Saeedi et al. (2020) — Incremental Multi-source Entity Resolution | <https://dbs.uni-leipzig.de/index.php/research/publications/incremental-multi-source-entity-resolution-for-knowledge-graph-completion> | Multi-source entity clustering for KG completion; source-order-independent resolution | .owlbear/research/863-source-aware-candidate-filtering.md | 2026-04-14 |

## MCP Browser Session Management (Task #837)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright Page API | <https://playwright.dev/python/docs/api/class-page> | `page.goto()`, `page.locator().click/fill/select_option()`, `page.content()`, `page.locator("body").aria_snapshot()` — page interaction patterns for navigate/click/type/select/read_text/snapshot tools | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 2026-04-12 |

## MCP Browser Server Research (Task #771)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP Tools Documentation | <https://gofastmcp.com/servers/tools> | ToolAnnotations API, Context access, error handling patterns, tool decorator args | .owlbear/research/771-mcp-browser-server.md | 2026-04-11 |

## MCP Browser ctx Refactor (Task #836)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP Dependency Injection Documentation | <https://gofastmcp.com/servers/dependency-injection> | `ctx: Context` auto-injection pattern, `request_context.lifespan_context` access for tools | .owlbear/research/836-mcp-browser-ctx-refactor.md | 2026-04-12 |

## Playwright Dep Bump for aria_snapshot (Task #855)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright Python Release Notes | <https://playwright.dev/python/docs/release-notes> | `page.aria_snapshot()` introduced in v1.59; `locator.aria_snapshot()` in v1.49 | .owlbear/research/855-playwright-dep-bump.md | 2026-04-13 |
| PyPI playwright Release History | <https://pypi.org/project/playwright/#history> | Latest Python release is 1.58.0 (2026-01-30); v1.59 not yet published | .owlbear/research/855-playwright-dep-bump.md | 2026-04-13 |

## Excalidraw Skill Expansion (Task #743)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| coleam00/excalidraw-diagram-skill SKILL.md | <https://github.com/coleam00/excalidraw-diagram-skill> | Visual Pattern Library (9 patterns), Shape Meaning table, Large Diagram Strategy, Container vs Text rules, ID conventions | .owlbear/research/excalidraw-skill-expansion.md | 2026-04-10 |
| Wikipedia: Entity-relationship model | <https://en.wikipedia.org/wiki/Entity-relationship_model> | Chen notation conventions: rectangles=entities, diamonds=relationships, ellipses=attributes | .owlbear/research/excalidraw-skill-expansion.md | 2026-04-10 |

## Authenticated Content Pipeline (Task #751)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright connect_over_cdp docs | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | CDP connection API, is_local flag, Edge support confirmation | .owlbear/research/751-authenticated-content-pipeline.md | 2026-04-10 |
| trafilatura (PyPI) | <https://pypi.org/project/trafilatura/> | HTML content extraction library — Apache 2.0, benchmark-proven, markdown output | .owlbear/research/751-authenticated-content-pipeline.md | 2026-04-10 |
| markdownify (PyPI) | <https://pypi.org/project/markdownify/> | HTML→markdown conversion — MIT license, BeautifulSoup-based, customizable | .owlbear/research/751-authenticated-content-pipeline.md | 2026-04-10 |
| browser-use project | <https://github.com/browser-use/browser-use> | CDP automation prior art — 80K stars, DomService pattern, AX tree usage | .owlbear/research/751-authenticated-content-pipeline.md | 2026-04-10 |

## Edge Launcher + CDP Implementation (Task #758)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | CDP connection API: endpoint_url, is_local (v1.58+), 30s default timeout | .owlbear/research/edge-launcher-cdp-impl-758.md | 2026-04-10 |
| Chrome 136 remote-debugging-port restriction | <https://developer.chrome.com/blog/remote-debugging-port> | `--remote-debugging-port` + `--user-data-dir` mandatory from Chrome/Edge 136+ | .owlbear/research/edge-launcher-cdp-impl-758.md | 2026-04-10 |

## CDP Spike Implementation Validation (Task #776)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | API verification: is_local (v1.58+), 30s timeout, default context pattern | .owlbear/research/cdp-spike-impl-776.md | 2026-04-10 |
| Chrome 136 remote-debugging-port restriction | <https://developer.chrome.com/blog/remote-debugging-port> | Verification: `--user-data-dir` to non-default dir mandatory from Chrome 136+ | .owlbear/research/cdp-spike-impl-776.md | 2026-04-10 |
| Brief security voice | .owlbear/briefs/draft-browser-knowledge-extraction/opinions/security.md | HR#4: CDP binds 127.0.0.1 only, no wildcard origins — identified gap in #752 design | .owlbear/research/cdp-spike-impl-776.md | 2026-04-10 |

## Phase 0 CDP Spike Research (Task #774)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Chrome 136 remote-debugging-port blog | <https://developer.chrome.com/blog/remote-debugging-port> | `--user-data-dir` mandatory for `--remote-debugging-port` from Chrome/Edge 136+ | .owlbear/research/774-edge-cdp-spike.md | 2026-04-10 |
| trafilatura evaluation benchmarks | <https://trafilatura.readthedocs.io/en/latest/evaluation.html> | F1 0.909 (standard), 0.902 (precision) — benchmark on news/blog, NOT corporate intranet | .owlbear/research/774-edge-cdp-spike.md | 2026-04-10 |
| trafilatura Python API docs (v2.0.0) | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | extract() params: output_format, favor_precision, prune_xpath, include_links | .owlbear/research/774-edge-cdp-spike.md | 2026-04-10 |

## Phase 1 Browser Package + Pipeline Quality + Schema (Task #775)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| trafilatura (PyPI) | <https://pypi.org/project/trafilatura/> | HTML content extraction library (Apache 2.0) — evaluated as dependency for owlbear_browser content extractor | .owlbear/research/775-phase1-browser-pipeline-schema.md | 2026-04-10 |
| Playwright CDP API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | CDP connection API patterns — is_local (v1.58+), 30s default timeout, default context access | .owlbear/research/775-phase1-browser-pipeline-schema.md | 2026-04-10 |

## HTML→Markdown Cleaner (Task #759)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| trafilatura Python API docs (v2.0.0) | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | extract() params: output_format, favor_precision, prune_xpath, include_links — evaluated as primary implementation approach (superseded by lxml custom) | .owlbear/research/759-html-markdown-cleaner.md | 2026-04-11 |
| trafilatura evaluation benchmarks | <https://trafilatura.readthedocs.io/en/latest/evaluation.html> | F1 0.909 (standard), 0.902 (precision) on news/blog; corporate intranet quality predicted .65 — informed decision to use lxml custom converter instead | .owlbear/research/759-html-markdown-cleaner.md | 2026-04-11 |
| markdownify 1.2.2 (PyPI) | <https://pypi.org/project/markdownify/> | HTML→markdown converter (MIT, BeautifulSoup-based) — evaluated as alternative; rejected: 3-4x more LOC vs trafilatura, no general boilerplate removal | .owlbear/research/759-html-markdown-cleaner.md | 2026-04-11 |

## Hash Stability Validation Protocol (Task #778)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| trafilatura Python API docs (v2.0.0) | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | `extract()` params: `output_format`, `prune_xpath`, `include_links`, `include_tables`, `url` — hash stability loop calls `extract()` with these params for cleaned-content hashing | .owlbear/research/778-hash-stability-protocol.md | 2026-04-11 |

## board_config() Implementation (Task #806)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Pydantic v2 docs — Models | <https://docs.pydantic.dev/latest/concepts/models/> | `model_copy()` returns "a copy (by default, shallow copy)" — confirms deep=True needed for isolation | .owlbear/research/board-config-impl-806.md | 2026-04-11 |

## Edge Launcher + CDP Tests (Task #755)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | CDP connection API: endpoint_url, is_local, timeout, default context access | .owlbear/research/edge-launcher-cdp-tests-755.md | 2026-04-10 |
| Chrome 136 remote-debugging-port restriction | <https://developer.chrome.com/blog/remote-debugging-port> | `--remote-debugging-port` requires `--user-data-dir` to non-default dir from Chrome 136+ | .owlbear/research/edge-launcher-cdp-tests-755.md | 2026-04-10 |

## Excalidraw Reference Files (Task #742)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| coleam00 element-templates.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/element-templates.md> | JSON templates for 6 element types (rectangle, text×2, arrow, line, dot) — validated for adaptation | .owlbear/research/excalidraw-reference-files.md | 2026-04-10 |
| coleam00 json-schema.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/json-schema.md> | Element types table, common/text/arrow properties, binding format | .owlbear/research/excalidraw-reference-files.md | 2026-04-10 |
| coleam00 color-palette.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/color-palette.md> | Semantic fill/stroke pairs, text hierarchy, evidence artifact colors | .owlbear/research/excalidraw-reference-files.md | 2026-04-10 |
| Excalidraw API updateScene docs | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/props/excalidraw-api#elements> | Element structure confirmation (type, version, versionNonce, seed fields) | .owlbear/research/excalidraw-reference-files.md | 2026-04-10 |

## Excalidraw Skill Reliability (Task #736)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| coleam00/excalidraw-diagram-skill SKILL.md | <https://github.com/coleam00/excalidraw-diagram-skill> | 450-line skill with design process, 9 visual patterns, mandatory render loop — compared vs OwlBear's 106-line adaptation | .owlbear/research/excalidraw-skill-reliability.md | 2026-04-10 |
| coleam00 element-templates.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/element-templates.md> | JSON templates for rectangle, text, arrow (with bindings), line, dot — all required fields shown | .owlbear/research/excalidraw-skill-reliability.md | 2026-04-10 |
| coleam00 json-schema.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/json-schema.md> | Element types, common properties, text-specific, arrow-specific, binding format | .owlbear/research/excalidraw-skill-reliability.md | 2026-04-10 |
| coleam00 color-palette.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/color-palette.md> | Semantic fill/stroke pairs, text hierarchy, evidence artifact colors | .owlbear/research/excalidraw-skill-reliability.md | 2026-04-10 |

## Wire PydanticAI Evaluate Callable (Task #701)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PydanticAI docs — Agents (output_type, system_prompt, run) | <https://ai.pydantic.dev/agents/> | `Agent(model, output_type=EvaluationResult, system_prompt=...)`, `await agent.run(prompt)` → `result.output` — confirmed API for factory pattern | .owlbear/research/wire-pydanticai-evaluate-callable.md | 2026-04-09 |

## Async StructuredExtractor Protocol (Task #687)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PEP 544 — Protocols: Structural subtyping | <https://peps.python.org/pep-0544/> | `@runtime_checkable` checks attribute existence only, not sync/async | .owlbear/research/async-structuredextractor-protocol.md | 2026-04-09 |
| Python docs — `typing.Protocol` | <https://docs.python.org/3/library/typing.html#typing.Protocol> | Protocols support `async def` methods since Python 3.8 | .owlbear/research/async-structuredextractor-protocol.md | 2026-04-09 |
| Python docs — `unittest.mock.AsyncMock` | <https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock> | Auto-promotes async spec methods; MagicMock does not | .owlbear/research/async-structuredextractor-protocol.md | 2026-04-09 |

## ddgs MCP Integration (Task #686)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| ddgs v9.13 README | <https://github.com/deedy5/ddgs> | MCP server command (`ddgs mcp`), 6 available tools, stdio client config JSON example | .owlbear/research/ddgs-mcp-integration.md | 2026-04-09 |
| ddgs PyPI v9.13 | <https://pypi.org/project/ddgs/> | Install command `pip install ddgs[mcp]`, release date Apr 6 2026, `[mcp]` extra definition | .owlbear/research/ddgs-mcp-integration.md | 2026-04-09 |

## ddgs[mcp] Dependency Compatibility (Task #706)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PyPI JSON API — ddgs 9.13.0 | <https://pypi.org/pypi/ddgs/json> | `requires_dist` for `[mcp]` extra: `mcp>=1.26.0` — confirmed compatibility with workspace `mcp[cli]>=1.26` | .owlbear/research/ddgs-mcp-dependency-compat.md | 2026-04-09 |
| PyPI JSON API — primp 1.2.2 | <https://pypi.org/pypi/primp/json> | Rust-based HTTP client, zero Python runtime deps — validated transitive dependency footprint | .owlbear/research/ddgs-mcp-dependency-compat.md | 2026-04-09 |

## Native Kanban Engine (Task #712)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PyPI — ruamel.yaml 0.19.1 | <https://pypi.org/project/ruamel.yaml/> | Round-trip YAML parser, comment/order preservation, 0.5M daily downloads — confirmed as only viable option for lossless YAML round-trip | .owlbear/research/native-kanban-engine.md | 2026-04-09 |
| GitHub — kanban-md v0.33.0 | <https://github.com/antopolskiy/kanban-md> | Current Go binary dependency — file format, CLI surface, behavioral contracts used as baseline | .owlbear/research/native-kanban-engine.md | 2026-04-09 |

## Diagram Rendering Tool for v2 Agents (Task #683)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code built-in tools list | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features#_chat-tools> | N/A (docs) | Complete list of VS Code Copilot built-in tools — confirmed `renderMermaidDiagram` does NOT exist | `.owlbear/research/diagram-rendering-tool-v2.md` | 2026-04-08 |
| VS Code Mermaid in chat | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | N/A (docs) | `mermaid-chat.enabled` setting renders Mermaid diagrams inline in chat responses | `.owlbear/research/diagram-rendering-tool-v2.md` | 2026-04-08 |

## MCP Tool Error Signaling Research (Task #680)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Spec §6 Error Handling (2025-11-25) | <https://modelcontextprotocol.io/specification/2025-11-25/server/tools> | Open Spec | Tool execution errors vs protocol errors; `isError: true` for input validation, business logic, API failures | `.owlbear/research/mcp-tool-error-signaling-680.md` | 2026-04-08 |
| MCP Spec §6 Error Handling (2025-06-18) | <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | Open Spec | Earlier spec version; same two error mechanisms documented | `.owlbear/research/mcp-tool-error-signaling-680.md` | 2026-04-08 |
| bierner/markdown-mermaid | <https://github.com/mjbvz/vscode-markdown-mermaid> | MIT | Mermaid rendering in Markdown Preview panel, 906 stars, extension already installed in OwlBear profile | `.owlbear/research/diagram-rendering-tool-v2.md` | 2026-04-08 |

## StructuredExtractor Knowledge Graph Wiring (Task #676)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PydanticAI docs — run_sync behavior | <https://ai.pydantic.dev/api/agent/#pydantic_ai.Agent.run_sync> | `run_sync()` uses `loop.run_until_complete()` — incompatible with running event loop | .owlbear/research/wire-structuredextractor-knowledge-graph.md | 2026-04-08 |

## LLMExtractor PydanticAI Implementation (Task #689)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PydanticAI docs — Agents (output_type, system_prompt, run) | <https://pydantic.dev/docs/ai/core-concepts/agent/> | Agent constructor API: `output_type=`, `system_prompt=`, `await agent.run()` → `result.output` | .owlbear/research/llmextractor-pydanticai-implementation.md | 2026-04-09 |
| PydanticAI docs — Structured Output | <https://pydantic.dev/docs/ai/core-concepts/output/> | `output_type=BaseModel` forces tool-based structured output with Pydantic validation | .owlbear/research/llmextractor-pydanticai-implementation.md | 2026-04-09 |
| PydanticAI docs — Testing (TestModel, FunctionModel, override) | <https://pydantic.dev/docs/ai/guides/testing/> | `TestModel`, `agent.override(model=TestModel())`, `ALLOW_MODEL_REQUESTS = False` | .owlbear/research/llmextractor-pydanticai-implementation.md | 2026-04-09 |

## Playwright Browser Integration for v2 (Task #684)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright PyPI | <https://pypi.org/project/playwright/> | v1.58.0 — install footprint, transitive deps (greenlet, pyee), browser binary size (~300-500 MB) | .owlbear/research/playwright-browser-integration-v2.md | 2026-04-08 |
| Prior research #264 | `.owlbear/research/browser-automation.md` | Keep-custom decision (.90 confidence), OSS alternative evaluation, Edge CDP constraint analysis | .owlbear/research/playwright-browser-integration-v2.md | 2026-04-08 |

## Analysis Detector Wiring (Task #682)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| v1 improvement_proposals.py | `v1/src/owlbear/core/improvement_proposals.py` | Prior art: descriptive-only proposals from EventStore metrics, never consumed automatically | .owlbear/research/analysis-detector-wiring.md | 2026-04-08 |
| #31 research: self-improvement analysis pipeline | `.owlbear/research/self-improvement-analysis-pipeline.md` | Original design: 4 detectors, AnalysisProposal schema, CLI entrypoint | .owlbear/research/analysis-detector-wiring.md | 2026-04-08 |

## Ideation Panel Handbook (Task #652)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Six Thinking Hats (de Bono 1985) | <https://en.wikipedia.org/wiki/Six_Thinking_Hats> | Deliberate perspective-shifting with distinct roles — theoretical basis for multi-ideation panel | .owlbear/research/ideation-panel-handbook.md | 2026-04-07 |
| Blackboard design pattern (Lalanda 1997) | <https://en.wikipedia.org/wiki/Blackboard_(design_pattern)> | Shared workspace + specialized knowledge sources — architectural precedent for Working Directory comms | .owlbear/research/ideation-panel-handbook.md | 2026-04-07 |

## Briefs Directory Structure (Task #642)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Blackboard design pattern | <https://en.wikipedia.org/wiki/Blackboard_(design_pattern)> | Blackboard pattern: structured global memory + knowledge sources + control component (Lalanda 1997) | .owlbear/research/briefs-directory-structure.md | 2026-04-06 |

## editFiles Schema Verification (Task #638)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Agent Hooks docs — PreToolUse input (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | `editFiles` tool_input schema: `{ "files": ["path"] }` — array of strings | .owlbear/research/editfiles-schema-verification-638.md | 2026-04-06 |
| VS Code Cheat Sheet — built-in tools | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | `#edit/editFiles` — "Apply edits to files in the workspace" confirms tool exists as built-in | .owlbear/research/editfiles-schema-verification-638.md | 2026-04-06 |

## Web Search MCP Options (Task #681)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| ddgs (deedy5/ddgs) v9.13 | <https://github.com/deedy5/ddgs> | Metasearch library with built-in MCP server, 9 backends, extract(), MIT license | .owlbear/research/web-search-mcp-options.md | 2026-04-08 |
| Brave Search MCP (official) | <https://github.com/brave/brave-search-mcp-server> | Official Brave MCP server, Node.js/TS, 6 tools, API key required, 880 stars | .owlbear/research/web-search-mcp-options.md | 2026-04-08 |
| Tavily MCP | <https://github.com/tavily-ai/tavily-mcp> | Node.js MCP server, search+extract+map+crawl, API key required, 1.7k stars | .owlbear/research/web-search-mcp-options.md | 2026-04-08 |
| MCP servers registry | <https://github.com/modelcontextprotocol/servers> | Reference and community MCP servers list, Brave Search archived to official repo | .owlbear/research/web-search-mcp-options.md | 2026-04-08 |

## Deny-Code-Writes AC Validation (Task #637)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Agent Hooks docs (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | PreToolUse input schema: `editFiles` tool_name with `files[]` array, `permissionDecision` output | .owlbear/research/deny-code-writes-ac-validation-637.md | 2026-04-06 |

## Pragmatist Voice Agent (Task #646)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Six Thinking Hats — Blue Hat synthesis role | <https://en.wikipedia.org/wiki/Six_Thinking_Hats> | Blue Hat: "The Big Picture & Managing" — facilitator aggregating all thinking directions into cohesive summary (de Bono 1985) | .owlbear/research/ideation-pragmatist-agent.md | 2026-04-06 |

## Blocked-Task Scan for Decision-Request Notifications (Task #348)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Azure DevOps approval checks | <https://learn.microsoft.com/en-us/azure/devops/pipelines/process/approvals> | Pipeline approval gates: stages pause for checks, timeout marks skipped, UI + email notification | docs/research/blocked-task-scan-decision-notifications.md | 2026-04-05 |
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | Required reviewers gate deployments, configurable wait timer, GitHub UI notification | docs/research/blocked-task-scan-decision-notifications.md | 2026-04-05 |

## Fix-Attempt Delegation Flow Testing Strategy (Task #320)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| tests/test_fix_attempt_agent_318.py | (internal) | Contract-level structural test pattern for agent .md files — 27 tests via regex/string assertions | docs/research/fix-attempt-delegation-tests.md | 2026-04-04 |
| tests/test_quality_runner_wiring.py | (internal) | Skill file content validation + agent frontmatter wiring combined pattern | docs/research/fix-attempt-delegation-tests.md | 2026-04-04 |

## Notifier Protocol Duplicate Assessment (Task #344)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MS Teams Incoming Webhooks docs | <https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook> | Teams webhook HTTP POST pattern, Adaptive Card payload format, channel-scoped config | docs/research/notifier-protocol-344-duplicate-assessment.md | 2026-04-04 |
| MS Teams connector deprecation notice | <https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using> | M365 Connectors nearing deprecation; migration to Power Automate Workflows with webhook trigger | docs/research/notifier-protocol-344-duplicate-assessment.md | 2026-04-04 |

## Revisit Blocked-Task DR Scan (Task #631)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| (validation pass — no new external sources) | — | All sources from #348 and #592 research; codebase-only validation | .owlbear/research/revisit-blocked-task-dr-scan-notification.md | 2026-04-05 |

## Import/Export Knowledge Snapshots (Task #618)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Python sqlite3 docs — Connection.backup | <https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup> | Python backup API, read-only URI mode (`?mode=ro`), transaction context manager | .owlbear/research/import-export-knowledge-snapshots.md | 2026-04-05 |
| SQLite ATTACH DATABASE | <https://sqlite.org/lang_attach.html> | Cross-DB queries via qualified table names — evaluated as alternative approach (rejected: less dedup control) | .owlbear/research/import-export-knowledge-snapshots.md | 2026-04-05 |
| SQLite Online Backup API | <https://sqlite.org/backup.html> | Online backup API for live DB snapshots — evaluated, not needed (row-level approach preferred) | .owlbear/research/import-export-knowledge-snapshots.md | 2026-04-05 |

## Power Automate Workflows for Teams Notifications (Task #592)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MS O365 connector retirement blog | <https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/> | O365 Connectors retire Apr 30 2026; Power Automate Workflows is migration path; MessageCard support added Feb 2026 | docs/research/power-automate-workflows-teams-notifications.md | 2026-04-04 |
| Teams webhook connector reference | <https://learn.microsoft.com/en-us/connectors/teams/#microsoft-teams-webhook> | TeamsIncomingWebhookTrigger API: HTTP POST, Adaptive Card schema, auth types, throttling limits | docs/research/power-automate-workflows-teams-notifications.md | 2026-04-04 |
| Create incoming webhooks with Workflows | <https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498> | Step-by-step template/scratch setup, URL copy, auth options, channel selection | docs/research/power-automate-workflows-teams-notifications.md | 2026-04-04 |

## Project-Local Knowledge Source (Task #616)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OwlBear #135 knowledge-scoping research | (internal) docs/research/knowledge-scoping.md | Column-based scope filtering design: scope TEXT column on all tables, vec0 post-filter, scope resolution | docs/research/project-local-knowledge-source.md | 2026-04-05 |
| LightRAG workspace isolation | <https://github.com/HKUDS/LightRAG> | File-based: separate subdirectories per workspace. PG: workspace column isolation. 28.7k stars, MIT. | docs/research/project-local-knowledge-source.md | 2026-04-05 |
| Mem0 multi-level scoping | <https://github.com/mem0ai/mem0> | user_id/session_id metadata keys for query-time scope filtering. Shared backend with logical separation. 48k stars, Apache-2.0. | docs/research/project-local-knowledge-source.md | 2026-04-05 |
| SQLite ATTACH DATABASE | <https://www.sqlite.org/lang_attach.html> | Cross-database queries via qualified table names. Atomic transactions for file-backed DBs. Max 10 attached. | docs/research/project-local-knowledge-source.md | 2026-04-05 |

## Agent-Scoped Hooks Research (Task #37)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Agent Hooks docs (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | Hook lifecycle events, PreToolUse/PostToolUse I/O, `updatedInput`, `env`, `chat.hookFilesLocations`, PostToolUse `decision: "block"`, safety guidance, SessionStart I/O schema | `docs/research/agent-scoped-hooks.md`, `docs/research/sessionstart-context-injection-hook.md` | 2026-04-04 |

## Register owlbear-memory MCP Server (Task #570)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code MCP Configuration Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | Server naming conventions (camelCase recommended, not enforced), stdio server config format | `docs/research/register-owlbear-memory-mcp.md` | 2026-04-03 |

## approve_memory CLI Wrapper (Task #531)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Python SDK README §Writing MCP Clients | github.com/modelcontextprotocol/python-sdk | stdio_client, StdioServerParameters, ClientSession patterns for CLI-to-MCP communication | docs/research/approve-memory-cli-wrapper.md | 2026-04-03 |
| MCP quickstart client tutorial | modelcontextprotocol.io/quickstart/client | MCP client connection management, call_tool pattern | docs/research/approve-memory-cli-wrapper.md | 2026-04-03 |

## deer-flow Broad Survey (Task #429)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| deer-flow repo (v2 main, MIT) | github.com/bytedance/deer-flow | Harness/app boundary test, skill validation patterns, middleware chain, guardrail protocol, summarization config, MCP caching, ACP config, embedded client, sandbox audit, reflection resolvers | docs/research/deer-flow-broad-survey.md | 2026-04-01 |
| deer-flow test_harness_boundary.py | In-repo: backend/tests/test_harness_boundary.py | AST-based import boundary enforcement pattern | docs/research/deer-flow-broad-survey.md S2A | 2026-04-01 |
| deer-flow skills/validation.py | In-repo: packages/harness/deerflow/skills/validation.py | Skill frontmatter validation patterns (naming, allowlist, safety) | docs/research/deer-flow-broad-survey.md S2D | 2026-04-01 |

## MCP Server Error/Return Standardization (Task #496)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Spec 2025-06-18 — Tools § Error Handling | modelcontextprotocol.io/specification/2025-06-18/server/tools | Two error mechanisms: protocol errors (JSON-RPC) and tool execution errors (`isError: true`); `error:` prefix supplements `isError` | docs/research/mcp-server-error-return-standardization.md | 2026-03-31 |
| MCP Python SDK v1.26.0 README | github.com/modelcontextprotocol/python-sdk | FastMCP catches exceptions as ToolError → `isError: true`; normal returns yield `isError: false`; structured output auto-generation from type annotations | docs/research/mcp-server-error-return-standardization.md | 2026-03-31 |

## Register owlbear-memory MCP Server (Task #571)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code custom agents docs | code.visualstudio.com/docs/copilot/customization/custom-agents | Tool pattern format: `<server name>/*` uses mcp.json key as server name | docs/research/register-owlbear-memory-mcp-json.md | 2026-04-03 |
| VS Code MCP server docs | code.visualstudio.com/docs/copilot/chat/mcp-servers | mcp.json configuration format for stdio servers | docs/research/register-owlbear-memory-mcp-json.md | 2026-04-03 |

## KanbanTask Model + outputSchema Validation (Task #495)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Prior outputSchema research (#477) | docs/research/mcp-kanban-outputschema-annotations.md | KanbanTask model design, ToolError pattern, annotation mapping | docs/research/kanbantask-model-outputschema.md | 2026-03-31 |
| FastMCP func_metadata.py (v1.26.0) | Installed: `.venv/.../fastmcp/utilities/func_metadata.py` | BaseModel return type → outputSchema auto-generation, wrap_output logic | docs/research/kanbantask-model-outputschema.md | 2026-03-31 |
| MCP low-level server.py | Installed: `.venv/.../mcp/server/lowlevel/server.py` | ToolError → isError:true, structured output validation and normalization | docs/research/kanbantask-model-outputschema.md | 2026-03-31 |
| kanban-md v0.33.0 JSON output | Local binary: `kanban-md show/list --json` | Verified complete field superset (class, claimed_by, claimed_at corrections) | docs/research/kanbantask-model-outputschema.md | 2026-03-31 |

## Knowledge & Project outputSchema + Annotations (Task #492)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Spec 2025-11-25 — Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | outputSchema, ToolAnnotations spec definitions (readOnlyHint, idempotentHint, destructiveHint, openWorldHint) | docs/research/knowledge-project-outputschema-annotations.md | 2026-03-31 |
| MCP Spec 2025-11-25 — Schema | modelcontextprotocol.io/specification/2025-11-25/schema | ToolAnnotations interface: title, readOnlyHint, destructiveHint, idempotentHint, openWorldHint fields | docs/research/knowledge-project-outputschema-annotations.md | 2026-04-02 |
| FastMCP docs — Output Schemas | gofastmcp.com/servers/tools#output-schemas | Auto-generation from return types, output_schema decorator param, manual schema control | docs/research/knowledge-project-outputschema-annotations.md | 2026-03-31 |
| MCP Python SDK v1.26.0 internals | Installed: `.venv/.../mcp/server/fastmcp/` | Tool.output_schema cached_property, FuncMetadata auto-generation, FastMCP.list_tools() protocol mapping | docs/research/knowledge-project-outputschema-annotations.md | 2026-03-31 |

## Skill Validation Hardening (Task #511)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Agent Skills Specification | agentskills.io/specification | Name field rules (hyphen-case, 1-64 chars, no leading/trailing/consecutive hyphens), description max 1024 chars | docs/research/skill-validation-hardening.md | 2026-04-01 |
| VS Code Agent Skills docs | code.visualstudio.com/docs/copilot/customization/agent-skills | Confirms spec naming constraints and directory-match requirement | docs/research/skill-validation-hardening.md | 2026-04-01 |
| deer-flow validation.py (MIT) | github.com/bytedance/deer-flow → backend/packages/harness/deerflow/skills/validation.py | Regex pattern, angle-bracket rejection, implementation reference | docs/research/skill-validation-hardening.md | 2026-04-01 |

## Memory Migration CLI Design (Task #527)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Mem0 CLI import command | docs.mem0.ai/platform/cli | Bulk import pattern (`mem0 import`), dry-run mode (`--dry-run`), JSON array input format | docs/research/memory-migration-cli-design.md | 2026-04-01 |
| Mem0 migration guide v1.0 | github.com/mem0ai/mem0/blob/main/MIGRATION_GUIDE_v1.0.md | API migration patterns, response format normalization | docs/research/memory-migration-cli-design.md | 2026-04-01 |

## Test-Writer Non-Impl Fallback Heuristic (Task #498)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GitHub Actions paths/paths-ignore | docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore | Content-based routing: skip test jobs for non-code changes | docs/research/test-writer-non-impl-fallback-heuristic.md | 2026-03-31 |
| GitLab CI rules:changes | docs.gitlab.com/ci/yaml/#ruleschanges | File-type heuristic for pipeline routing | docs/research/test-writer-non-impl-fallback-heuristic.md | 2026-03-31 |

## deer-flow Memory + Subagent Deep Dive (Task #428)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| deer-flow repo (v2, Apache-2.0) | github.com/bytedance/deer-flow | Memory system (updater, queue, storage, prompt, middleware) and subagent system (executor, registry, config, task_tool, SubagentLimitMiddleware) — full source analysis | docs/research/deer-flow-memory-subagent-deep-dive.md | 2026-03-31 |

## Upgrade query_service.py — Hybrid Search (Task #160)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Qdrant hybrid queries docs | qdrant.tech/documentation/concepts/hybrid-queries/ | Prefetch + Fusion.RRF server-side ranking pattern | docs/research/upgrade-query-service-hybrid-search.md | 2026-04-01 |
| qdrant-client v1.9+ API (local) | Installed package | Verified `Fusion.RRF`, `FusionQuery`, `Prefetch` classes | docs/research/upgrade-query-service-hybrid-search.md | 2026-04-01 |

## KANBAN_TOOLS_EXCLUDE Config (Task #473)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP v1.26.0 server.py | Installed: `.venv/Lib/site-packages/mcp/server/fastmcp/server.py` | `remove_tool(name) -> None` public API, raises ToolError on unknown | docs/research/kanban-tools-exclude-config.md | 2026-03-31 |
| FastMCP tool_manager.py | Installed: `.venv/Lib/site-packages/mcp/server/fastmcp/tools/tool_manager.py` | `remove_tool` implementation and ToolError exception | docs/research/kanban-tools-exclude-config.md | 2026-03-31 |
| OwlBear mcp-kanban server | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | KANBAN_BIN env read pattern (in lifespan), tool registration via decorators | docs/research/kanban-tools-exclude-config.md | 2026-03-31 |

## E2E Smoke Test Script (Task #157)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OwlBear test_e2e_dispatch.py | tests/test_e2e_dispatch.py | UUID task isolation, subprocess dispatch, try/finally cleanup pattern | docs/research/e2e-smoke-test-script.md | 2026-04-01 |
| Python subprocess docs | docs.python.org/3/library/subprocess.html | timeout parameter, TimeoutExpired handling for dispatch wait | docs/research/e2e-smoke-test-script.md | 2026-04-01 |
| Python atexit docs | docs.python.org/3/library/atexit.html | Exit handler tradeoffs (decided against atexit) | docs/research/e2e-smoke-test-script.md | 2026-04-01 |

## memory-mcp Server Architecture Design (Task #387)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Mem0 open-source (Apache-2.0) | github.com/mem0ai/mem0 | Multi-level memory scoping (user_id, agent_id), memory add/search API, MCP integration (OpenMemory) | docs/research/memory-mcp-server-design.md S7 | 2026-04-01 |
| DR #428 resolved | docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md | Binding constraints: adopt patterns 1,2,4(custom),6 from deer-flow | docs/research/memory-mcp-server-design.md S2 | 2026-04-01 |
| #499 schema definitions | docs/research/deer-flow-memory-patterns-schema-definitions.md | Concrete MemoryEntry schema, MCP tool interface proposal | docs/research/memory-mcp-server-design.md S1 | 2026-04-01 |

## Curator Workflow Design for memory-mcp (Task #528)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Mem0 Memory class | github.com/mem0ai/mem0 | Memory add/get/delete/update/history operations, scoping via user_id/agent_id/run_id, LLM-driven curation (ADD/UPDATE/DELETE events) | docs/research/curator-workflow-memory-mcp.md S6 | 2026-04-01 |
| LangMem conceptual guide | langchain-ai.github.io/langmem/concepts/conceptual_guide | Background memory manager consolidation pattern, collection vs profile memory types, hot-path vs background formation | docs/research/curator-workflow-memory-mcp.md S7 | 2026-04-01 |

## PostToolUse Subagent Output Routing (Task #532)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Hooks docs (4/2/2026) | code.visualstudio.com/docs/copilot/customization/hooks | PostToolUse I/O schema (additionalContext, systemMessage, exit codes), subagent routing behavior — additionalContext confirmed model-facing, exit code 2 NOT model-facing via -Command | docs/research/posttooluse-subagent-output-routing.md | 2026-04-02 |

## Exit Code 2 via -File Invocation Routing (Task #548)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MS PS 5.1 about_PowerShell_exe | learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe | -File vs -Command exit code propagation semantics; -File preserves numeric script exit codes, -Command converts non-0/1 to 1; used to predict BlockingError for exit 2 via -File (prediction disproven empirically) | docs/research/exit-code-2-file-mode-routing.md | 2026-04-02 |

## PostToolUse additionalContext Lint Feedback (Task #547)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| claude-plugins-official #317 | github.com/anthropics/claude-plugins-official/issues/317 | systemMessage alone not model-facing; combined systemMessage + hookSpecificOutput.additionalContext pattern confirmed | docs/research/posttooluse-additionalcontext-lint-feedback.md | 2026-04-02 |
| microsoft/vscode #296189 | github.com/microsoft/vscode/issues/296189 | Correct PostToolUse output format; hookEventName field required in hookSpecificOutput | docs/research/posttooluse-additionalcontext-lint-feedback.md | 2026-04-02 |

## Switch move/pick to JSON, Remove board_context (Task #477)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| kanban-md v0.33.0 CLI help | Local binary (`kanban-md move --help`, `pick --help`) | Confirmed `--json` global flag support for move and pick commands | docs/research/move-pick-json-remove-board-context.md | 2026-03-31 |
| kanban-md JSON schemas | `skills/kanban-md/references/json-schemas.md` | Task object schema returned by `--json` flag | docs/research/move-pick-json-remove-board-context.md | 2026-03-31 |
| MCP Spec 2025-11-25 — Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | outputSchema, structuredContent, ToolAnnotations spec definitions | docs/research/mcp-kanban-outputschema-annotations.md | 2026-03-31 |
| MCP Python SDK v1.26.0 types + func_metadata | Installed package `.venv/Lib/site-packages/mcp/` | ToolAnnotations class, Tool.outputSchema field, FastMCP structured_output auto-detection | docs/research/mcp-kanban-outputschema-annotations.md | 2026-03-31 |

## set_approval_state MCP Tool Design (Task #529)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Spec 2025-11-25 — ToolAnnotations schema | modelcontextprotocol.io/specification/2025-11-25 (schema.json) | readOnlyHint, idempotentHint, destructiveHint, openWorldHint definitions and defaults | docs/research/set-approval-state-mcp-tool.md S5 | 2026-04-03 |

## TOOLS_EXCLUDE for Knowledge and Project MCP Servers (Task #493)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| mcp-kanban _apply_tool_exclusions | packages/mcp-kanban/src/owlbear_mcp_kanban/server.py L72-90 | Reference pattern for lifespan-level tool exclusion | docs/research/tools-exclude-knowledge-project.md | 2026-04-01 |
| #473 TOOLS_EXCLUDE research | docs/research/kanban-tools-exclude-config.md | Design rationale for env var naming and lifespan approach | docs/research/tools-exclude-knowledge-project.md | 2026-04-01 |
| mcp-knowledge server ToolAnnotations usage | `packages/mcp-knowledge/src/.../server.py` | Existing annotation pattern (readOnlyHint=True/False) as implementation precedent | docs/research/mcp-kanban-outputschema-annotations.md | 2026-03-31 |

## create_task Status/Parent/JSON (Task #475)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| kanban-md v0.33.0 `create --help` | Local binary | `--status`, `--parent`, `--json` flag availability and types | docs/research/create-task-status-parent-json.md | 2026-03-31 |
| Modernize list_tasks research (#472) | docs/research/modernize-list-tasks.md | JSON output design precedent, lean JSON approach | docs/research/create-task-status-parent-json.md | 2026-03-31 |
| FastMCP `func_metadata.py` | Installed: `.venv/.../mcp/server/fastmcp/utilities/func_metadata.py` | outputSchema auto-detection from return type annotations | docs/research/create-task-status-parent-json.md | 2026-03-31 |
| MCP Python SDK `mcp.types` | Installed: `.venv/.../mcp/types.py` L1310-1380 | Tool.outputSchema, CallToolResult.structuredContent definitions | docs/research/create-task-status-parent-json.md | 2026-03-31 |
| outputSchema research (#477) | docs/research/mcp-kanban-outputschema-annotations.md | KanbanTask model design, ToolError error handling pattern | docs/research/create-task-status-parent-json.md | 2026-03-31 |

## edit_task dep/parent/title/JSON (Task #476)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| kanban-md CLI v0.33.0 help | (local binary) | `edit --help` flag verification for --add-dep, --remove-dep, --parent, --title, --json | docs/research/edit-task-dep-parent-title-json.md | 2026-03-31 |
| Existing expand-mcp-kanban research (#56) | docs/research/expand-mcp-kanban-tools.md | Prior gap analysis identifying missing edit params | docs/research/edit-task-dep-parent-title-json.md | 2026-03-31 |
| MCP Python SDK v1.26.0 README | <https://github.com/modelcontextprotocol/python-sdk> | Structured output patterns: TypedDict, Pydantic, dict return types; outputSchema auto-detection | docs/research/edit-task-dep-parent-title-json.md | 2026-03-31 |
| MCP Python SDK mcp.types module | (installed package: mcp.types L1310-1380) | Tool.outputSchema and CallToolResult.structuredContent field definitions | docs/research/edit-task-dep-parent-title-json.md | 2026-03-31 |

## mcp-knowledge Structured Returns (Task #507)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP docs — Structured Output | gofastmcp.com/servers/tools#structured-output | Auto structuredContent + content for typed returns; list needs annotation for schema wrapping | docs/research/mcp-knowledge-structured-returns.md | 2026-03-31 |
| FastMCP docs — Output Schemas | gofastmcp.com/servers/tools#output-schemas | Auto-generation from return type; primitives/lists wrapped in {"result": ...} | docs/research/mcp-knowledge-structured-returns.md | 2026-03-31 |

## end_work Compound Tool (Task #471)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP Tools docs | <https://gofastmcp.com/servers/tools> | Literal type support, ToolError, async patterns, structured output | docs/research/end-work-compound-tool.md | 2026-03-31 |
| MCP Spec — Tools | <https://modelcontextprotocol.io/specification/2025-03-26/server/tools> | Tool design patterns, error reporting model | docs/research/end-work-compound-tool.md | 2026-03-31 |

## deer-flow Subagent Patterns for Wave Dispatch (Task #500)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| deer-flow deep dive (#428) sections 3D–3F | docs/research/deer-flow-memory-subagent-deep-dive.md | SubagentLimitMiddleware truncation behavior; SubagentResult status lifecycle | docs/research/deer-flow-subagent-patterns-wave-dispatch.md | 2026-04-01 |
| Python asyncio sync primitives | docs.python.org/3/library/asyncio-sync.html | Semaphore concurrency control — available but unnecessary for pre-computed wave sizes | docs/research/deer-flow-subagent-patterns-wave-dispatch.md | 2026-04-01 |
| AutoGen AgentChat TaskResult pattern | microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html | Typed TaskResult objects for agent dispatch results; different execution model (in-process) | docs/research/deer-flow-subagent-patterns-wave-dispatch.md | 2026-04-01 |

## deer-flow Memory Pattern Schema Definitions (Task #499)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| deer-flow deep dive (owning: #428) | `docs/research/deer-flow-memory-subagent-deep-dive.md` | Fact schema, confidence gating, dedup, pruning, injection, category taxonomy patterns | docs/research/deer-flow-memory-patterns-schema-definitions.md | 2026-03-31 |
| DR #428 (approved) | `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` | Custom adoption decision: patterns 1,2,6 unchanged, 4 customized | docs/research/deer-flow-memory-patterns-schema-definitions.md | 2026-03-31 |
| Mem0 memory system | github.com/mem0ai/mem0 | Scoping via user_id/agent_id, fact deduplication, Memory ABC pattern | docs/research/deer-flow-memory-patterns-schema-definitions.md | 2026-03-31 |

## ToolAnnotations for mcp-kanban (Task #494)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Spec 2025-11-25 — Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | ToolAnnotations spec: readOnlyHint, destructiveHint, idempotentHint defaults | docs/research/mcp-kanban-toolannotations.md | 2026-03-31 |
| MCP Python SDK v1.26.0 mcp.types | Installed: `.venv/Lib/site-packages/mcp/types.py` L1247-1300 | ToolAnnotations class definition and field defaults | docs/research/mcp-kanban-toolannotations.md | 2026-03-31 |

## KB Data Loader Script and Sources Manifest (Task #176)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GraphRAG YAML config | microsoft.github.io/graphrag/config/yaml/ | YAML manifest format with `type`, `config`, `scope` fields for document discovery | packages/knowledge/src/owlbear_knowledge/loader.py | 2026-03-30 |
| strictyaml docs | hitchdev.com/strictyaml/ | Type-safe YAML parsing with typed schema validation (Map, Seq, Enum, Bool, EmptyNone) | packages/knowledge/src/owlbear_knowledge/loader.py | 2026-03-30 |
| mcp-knowledge server ToolAnnotations | `packages/mcp-knowledge/src/.../server.py` | Existing annotation pattern as implementation reference | docs/research/mcp-kanban-toolannotations.md | 2026-03-31 |
| mcp-knowledge annotation tests | `packages/mcp-knowledge/tests/test_ingest_graph_tools.py` L630-680 | `_get_tool_annotations()` test helper pattern | docs/research/mcp-kanban-toolannotations.md | 2026-03-31 |

## Modernize list_tasks (Task #472)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP tool registration docs | <https://gofastmcp.com/servers/fastmcp#tools> | Tool parameter typing conventions for Optional[bool] tri-state | docs/research/modernize-list-tasks.md | 2026-03-31 |
| Python typing.Optional docs | <https://docs.python.org/3/library/typing.html#typing.Optional> | Optional[bool] tri-state pattern reference | docs/research/modernize-list-tasks.md | 2026-03-31 |

## Challenger Researcher Expansion (Task #469)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Challenger subagent design (owning: #465) | docs/research/challenger-subagent-design.md | Expansion path S3h, I/O contract S3d, interaction model S3b | docs/research/challenger-researcher-expansion.md | 2026-03-31 |
| Arch-review Step 3.5 integration (#468) | skills/arch-review/SKILL.md | Implemented challenger integration pattern as template | docs/research/challenger-researcher-expansion.md | 2026-03-31 |
| Du et al. 2023 — Multiagent Debate | <https://arxiv.org/abs/2305.14325> | Single-round debate improves factuality over self-reflection | docs/research/challenger-researcher-expansion.md | 2026-03-31 |
| Liang et al. 2024 — MAD (EMNLP) | <https://arxiv.org/abs/2305.19118> | Degeneration-of-Thought in self-reflection; external challenge needed | docs/research/challenger-researcher-expansion.md | 2026-03-31 |

## start_work Compound Tool (Task #470)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MCP Python SDK (FastMCP) | <https://github.com/modelcontextprotocol/python-sdk> | `@mcp.tool()` decorator patterns, return types, compound tool feasibility | docs/research/start-work-compound-tool.md | 2026-03-31 |
| FastMCP Tools docs | <https://gofastmcp.com/servers/tools> | Tool arguments, structured output, error handling patterns | docs/research/start-work-compound-tool.md | 2026-03-31 |

## Recipe 0 Tier-Aware Auto-Resolution (Task #464)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | Per-environment wait-timers: production has required-reviewers with no auto-bypass, staging has wait-timers — validates tier-differentiated auto-resolve | docs/research/recipe0-tier-aware-auto-resolve.md | 2026-03-31 |
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | UserProxyAgent blocks indefinitely until user responds — validates indefinite T3 blocking in single-user system | docs/research/recipe0-tier-aware-auto-resolve.md | 2026-03-31 |

## KANBAN_TOOLS_EXCLUDE Config (Task #473) — Supplemental

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| FastMCP v1.x server.py | <https://github.com/modelcontextprotocol/python-sdk/blob/v1.x/src/mcp/server/fastmcp/server.py> | `remove_tool(name)` public API for post-registration tool removal | docs/research/kanban-tools-exclude-config.md | 2026-03-31 |
| MCP Python SDK README | <https://github.com/modelcontextprotocol/python-sdk> | `@mcp.tool()` registration pattern, lifespan conventions | docs/research/kanban-tools-exclude-config.md | 2026-03-31 |

## Impact-Tier Decision Requests (Task #459)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | UserProxyAgent blocks indefinitely; HandoffTermination typed pause pattern — validates T3 indefinite blocking | docs/research/impact-tier-decision-requests.md | 2026-03-31 |
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | Per-environment wait-timers with auto-approve; required-reviewer gates — validates tiered timeout model | docs/research/impact-tier-decision-requests.md | 2026-03-31 |

## Extend Decision-Request for Action Requests (Task #221)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | HandoffTermination pattern for async user requests — typed pause point, structured resume input | docs/research/extend-decision-request-for-action-requests.md | 2026-03-30 |
| CrewAI Task docs | <https://docs.crewai.com/concepts/tasks> | `human_input` attribute, callback mechanism for blocking on user review | docs/research/extend-decision-request-for-action-requests.md | 2026-03-30 |
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | Required-reviewer approval gate pattern — structured file-based state with auto-timeout and well-known directory | docs/research/extend-decision-request-for-action-requests.md | 2026-03-30 |

## deer-flow Adoptable Patterns (Task #386)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| deer-flow repo (v2 main) | <https://github.com/bytedance/deer-flow> | Apache-2.0 | Middleware chain (loop detection, tool error handling, summarization), memory system (fact confidence, debounced queue), subagent executor (dual pools, trace IDs, tool filtering), guardrail provider pattern, SOUL personality config, deferred tool registry, MCP cache mtime invalidation | `docs/research/deer-flow-adoptable-patterns.md` | 2026-03-30 |
| LangChain Agent Middleware docs | <https://python.langchain.com/docs/how_to/agent_middleware> | N/A | Middleware chain concept validation, AgentMiddleware interface | `docs/research/deer-flow-adoptable-patterns.md` | 2026-03-30 |

## KB Data Loader and Sources Manifest (Task #176)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GraphRAG YAML config | <https://microsoft.github.io/graphrag/config/yaml/> | Input file pattern and YAML config structure for document ingestion | docs/research/kb-data-loader-manifest.md | 2026-03-30 |
| LightRAG insert API | <https://github.com/HKUDS/LightRAG> | Batch insertion pattern, doc_status_storage delta detection | docs/research/kb-data-loader-manifest.md | 2026-03-30 |
| LlamaIndex SimpleDirectoryReader | <https://developers.llamaindex.ai/python/framework/module_guides/loading/simpledirectoryreader/> | Glob-based file discovery, metadata extraction pattern | docs/research/kb-data-loader-manifest.md | 2026-03-30 |

## Subagent Nesting Architecture (Task #228)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agents Concepts | <https://code.visualstudio.com/docs/copilot/concepts/agents> | CC-BY-4.0 | Parallel subagent execution, context isolation, subagent key characteristics | `docs/research/subagent-nesting-architecture.md` | 2026-03-30 |
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Nesting depth (max 5), coordinator/worker pattern, multi-perspective review, nested subagents setting | `docs/research/subagent-nesting-architecture.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agents field overrides disable-model-invocation, inherit vs assign mode, user-invocable | `docs/research/subagent-nesting-architecture.md` | 2026-03-30 |

## Reviewer Parallel Fan-Out (Task #265)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agents Concepts | <https://code.visualstudio.com/docs/copilot/concepts/agents> | CC-BY-4.0 | Parallel subagent execution confirmation, context isolation benefits | `docs/research/reviewer-parallel-fan-out.md` | 2026-03-30 |
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Multi-perspective review pattern ("Thorough Reviewer"), coordinator/worker orchestration | `docs/research/reviewer-parallel-fan-out.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agents array override for disable-model-invocation, assign vs inherit tool modes | `docs/research/reviewer-parallel-fan-out.md` | 2026-03-30 |

## Dispatch-Cycle Trace ID (Task #434)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| W3C Trace Context | <https://www.w3.org/TR/trace-context/> | trace-id (16-byte UUID) propagation standard, parent-id per span, trace-flags | docs/research/dispatch-cycle-trace-id.md | 2026-03-30 |
| OpenTelemetry Traces | <https://opentelemetry.io/docs/concepts/signals/traces/> | trace_id + span_id context propagation, parent-child correlation model | docs/research/dispatch-cycle-trace-id.md | 2026-03-30 |
| LangSmith Observability | <https://docs.langchain.com/langsmith/observability-concepts> | Trace = collection of runs bound by trace_id, threads linked by session_id | docs/research/dispatch-cycle-trace-id.md | 2026-03-30 |

## Reviewer execute/* Tool Removal (Task #317)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Subagent tool independence from parent agent | `docs/research/reviewer-execute-tool-removal.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Least privilege via assign mode, tool set security | `docs/research/reviewer-execute-tool-removal.md` | 2026-03-30 |

## Reviewer Loop Pattern Detection (Task #436)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| deer-flow LoopDetectionMiddleware | <https://github.com/bytedance/deer-flow> | Apache-2.0 | Hash-based tool call dedup, warn@3/stop@5 thresholds, sliding window tracking | `docs/research/reviewer-loop-pattern-detection.md` | 2026-03-30 |
| AutoGen termination conditions | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html> | MIT | Composable termination (MaxMessage, FunctionCall, Text), stateful+resettable pattern | `docs/research/reviewer-loop-pattern-detection.md` | 2026-03-30 |

## Planner Recipe 0 Action Request Extension (Task #226)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | Wait-timer auto-approve after timeout; structured file-based gate with auto-resolution precedent | docs/research/planner-recipe0-action-request-extension.md | 2026-03-30 |
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | HandoffTermination typed pause-point pattern; confirms structured resume signals | docs/research/planner-recipe0-action-request-extension.md | 2026-03-30 |

## Analysis Module Implementation Readiness (Task #179)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen telemetry + structured logging | <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/telemetry.html> | MIT | Typed event spans (`invoke_agent`), per-agent attribution via OpenTelemetry | `docs/research/analysis-module-implementation-readiness.md` | 2026-03-30 |
| LangSmith evaluation concepts | <https://docs.langchain.com/langsmith/evaluation> | N/A | Code evaluators vs LLM-as-judge; validates pure-stats approach for threshold-based detection | `docs/research/analysis-module-implementation-readiness.md` | 2026-03-30 |

## Stop Hook Multi-Agent Viability (Task #209, 2nd research cycle)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | Stop hook output schema (systemMessage, decision, reason), common output format, SubagentStop semantics | `docs/research/stop-hook-multi-agent-viability.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Agent-scoped hooks treated as SubagentStop, user-invocable vs pipeline-only distinction | `docs/research/stop-hook-multi-agent-viability.md` | 2026-03-30 |

## Stop Commit Guard Defect Remediation (Task #209)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | Hook command properties (`command` vs `windows`), Stop hook I/O format, `hookSpecificOutput` wrapper, `stop_hook_active` loop prevention | `docs/research/stop-commit-guard-defect-remediation.md` | 2026-03-30 |

## Loop Detection Instruction Patterns (Task #432)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| deer-flow LoopDetectionMiddleware | <https://github.com/bytedance/deer-flow> → `backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py` | Apache-2.0 | Hash-based tool call dedup, 3-warn/5-stop thresholds, sliding window, LRU per-thread tracking | `docs/research/loop-detection-instruction-patterns.md` | 2026-03-30 |
| Microsoft AutoGen termination conditions | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html> | MIT | MaxMessageTermination, composable conditions (AND/OR), custom FunctionCallTermination | `docs/research/loop-detection-instruction-patterns.md` | 2026-03-30 |

## Hook AC Command-Execution Model Correction (Task #213)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | PreToolUse `permissionDecision` output, PostToolUse `systemMessage` and `decision` output, tool_name in stdin JSON, correct VS Code tool names (`create_file`, `replace_string_in_file`) | `docs/research/hook-ac-command-execution-model.md` | 2026-03-30 |

## Mock ACP Agent for E2E Testing (Task #155)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP SDK `interfaces.py` — Agent Protocol | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/interfaces.py> | MIT | Agent Protocol interface (15 required methods), method signatures | `docs/research/mock-acp-agent-e2e.md` | 2026-03-30 |
| ACP SDK `examples/agent.py` — ExampleAgent | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/agent.py> | MIT | Reference Agent implementation pattern (~125 LOC), `run_agent()` entry point | `docs/research/mock-acp-agent-e2e.md` | 2026-03-30 |

## Tool-Error Handling Guidance (Task #433)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Anthropic Claude API — Handle Tool Calls | <https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls> | N/A | `is_error` field in tool_result, structured error signaling pattern | `docs/research/tool-error-handling-guidance.md` | 2026-03-30 |
| OpenAI Function Calling Guide | <https://developers.openai.com/api/docs/guides/function-calling> | N/A | Error codes/descriptions as formatted results, model interprets error strings | `docs/research/tool-error-handling-guidance.md` | 2026-03-30 |
| CrewAI Tools — Error Handling | <https://docs.crewai.com/concepts/tools> | N/A | Built-in error handling as key tool characteristic, graceful exception management | `docs/research/tool-error-handling-guidance.md` | 2026-03-30 |

## Fix-Attempt Agent Design Validation (Task #318)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Coordinator/worker pattern, assign mode, nesting depth 5 | `docs/research/fix-attempt-agent-design.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agents array overrides disable-model-invocation | `docs/research/fix-attempt-agent-design.md` | 2026-03-30 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Verbal reinforcement: feedback replaces weight updates for retry | `docs/research/fix-attempt-agent-design.md` | 2026-03-30 |
| SupaConductor Evaluate-Loop | <https://github.com/Ibrahim-3d/orchestrator-supaconductor> | MIT | Execute-Evaluate-Fix cycle (max 3), fixer as separate step | `docs/research/fix-attempt-agent-design.md` | 2026-03-30 |
| ACP SDK `stdio.py` — `spawn_agent_process()` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/stdio.py> | MIT | Subprocess spawn pattern, `ClientSideConnection` wiring, env/cwd forwarding | `docs/research/mock-acp-agent-e2e.md` | 2026-03-30 |
| ACP SDK `test_rpc.py` — spawn roundtrip | <https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py> | MIT | In-memory agent/client test harness, `test_spawn_agent_process_roundtrip` pattern | `docs/research/mock-acp-agent-e2e.md` | 2026-03-30 |

## Extend Decision-Request Process for User Action Requests (Task #221)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | MIT | HandoffTermination pattern for async user handoff, UserProxyAgent for typed pause points | `docs/research/extend-decision-request-for-action-requests.md` | 2026-03-30 |
| CrewAI Task docs | <https://docs.crewai.com/concepts/tasks> | Apache-2.0 | `human_input` task attribute for human review gate, callback mechanism for notifications | `docs/research/extend-decision-request-for-action-requests.md` | 2026-03-30 |
| GitHub Actions environment protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | CC-BY-4.0 | Required-reviewer approval gate, structured file-based state, auto-timeout patterns | `docs/research/extend-decision-request-for-action-requests.md` | 2026-03-30 |
| ACP SDK `conftest.py` — TestAgent/TestClient | <https://github.com/agentclientprotocol/python-sdk/blob/main/tests/conftest.py> | MIT | TestAgent stub pattern, TestClient with permission handling | `docs/research/mock-acp-agent-e2e.md` | 2026-03-30 |

## Canonical Tool Registry Validation (Task #198)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Cheat Sheet (2026-03-25) | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Canonical built-in tool list (7 tool sets + 31 individual tools) | `docs/research/canonical-tool-registry-validation.md` | 2026-03-30 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool sets concept, MCP tool format, tool type taxonomy | `docs/research/canonical-tool-registry-validation.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `tools:` field spec, `<server>/*` MCP format, tool set references | `docs/research/canonical-tool-registry-validation.md` | 2026-03-30 |

## Validate Multi-Project Setup (Task #167)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `chat.agentFilesLocations` resolution, agent picker source tooltips, Configure Custom Agents menu | `docs/research/validate-multi-project-setup.md` | 2026-03-30 |
| VS Code customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Chat Customizations editor (Preview), parent repository discovery, troubleshooting customizations | `docs/research/validate-multi-project-setup.md` | 2026-03-30 |
| VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server config, `MCP: List Servers` command, server naming conventions | `docs/research/validate-multi-project-setup.md` | 2026-03-30 |

## Pipeline Quality Audit (Task #192)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Du et al. 2023 — Multi-agent Debate | <https://arxiv.org/abs/2305.14325> | CC-BY-4.0 | Multi-agent debate improves factuality only when agents reason independently; sequential pipelines inherit upstream errors | `docs/research/pipeline-quality-audit.md` | 2026-03-29 |
| VS Code MCP Server Guide | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> | CC-BY-4.0 | MCP server configuration, Copilot extension built-in server provision, duplicate server behavior | `docs/research/pipeline-quality-audit.md` | 2026-03-29 |

## Gate 4 TW:MISSING Tag Exemptions (Task #215)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Actions `paths-ignore` | <https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore> | CC-BY-4.0 | Established CI pattern for exempting non-code changes from test gates | `docs/research/gate4-tw-missing-tag-exemptions.md` | 2026-03-30 |
| GitLab CI `rules:changes` | <https://docs.gitlab.com/ci/yaml/#ruleschanges> | MIT | Tag/path-based gate exemption pattern in CI pipelines | `docs/research/gate4-tw-missing-tag-exemptions.md` | 2026-03-30 |

## Quality-Runner Subagent Design (Task #263)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Built-in Tools Reference | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Canonical built-in tool identifiers (7 sets, 31+ tools) for assign-mode validation | `docs/research/quality-runner-subagent-design.md` | 2026-03-30 |
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | agents array override for disable-model-invocation, coordinator/worker patterns | `docs/research/quality-runner-subagent-design.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | user-invocable, disable-model-invocation, assign mode frontmatter | `docs/research/quality-runner-subagent-design.md` | 2026-03-30 |

## Arch-Review Premise Challenge (Task #195)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Klein 2007 — Performing a Project Premortem | <https://hbr.org/2007/09/performing-a-project-premortem> | N/A | Pre-mortem technique: assume failure and work backward to identify causes; breaks groupthink and anchoring bias | `docs/research/arch-review-premise-challenge.md` | 2026-03-29 |
| Chesterton 1929 — The Drift from Domesticity | <https://en.wikipedia.org/wiki/G._K._Chesterton#Chesterton's_fence> | N/A | Chesterton's fence: understand why something exists (or doesn't) before changing it; inverse applied to feature additions | `docs/research/arch-review-premise-challenge.md` | 2026-03-29 |

## Gate 3 Atomicity Architect Bypass (Task #214)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| `skills/dispatch-planning/SKILL.md` (internal) | N/A | N/A | Gate 3 definition, Board Scan Recipe 1 marker pattern | `docs/research/gate-3-atomicity-architect-bypass.md` | 2026-03-30 |
| `skills/arch-review/SKILL.md` (internal) | N/A | N/A | Step 3.1 single-responsibility check, `## Architecture Review` output section | `docs/research/gate-3-atomicity-architect-bypass.md` | 2026-03-30 |

## General KB Initial Data Load Research (Task #24)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GraphRAG quickstart | <https://microsoft.github.io/graphrag/get_started/> | MIT | Bulk indexing from `input/` directory, `graphrag index` pipeline | `docs/research/general-kb-initial-data-load.md` | 2026-03-29 |
| LightRAG insert API | <https://github.com/HKUDS/LightRAG> | MIT | `rag.ainsert()` incremental ingestion, workspace isolation pattern | `docs/research/general-kb-initial-data-load.md` | 2026-03-29 |
| Mem0 memory layer | <https://github.com/mem0ai/mem0> | Apache-2.0 | `memory.add()` incremental pattern, multi-level memory scoping | `docs/research/general-kb-initial-data-load.md` | 2026-03-29 |

## E2E Dispatch Integration Test (Task #156)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | CliRunner invocation model, synchronous test pattern, result assertion | `docs/research/e2e-dispatch-integration-test.md` | 2026-03-30 |
| Click testing docs | <https://click.palletsprojects.com/en/stable/testing/> | BSD-3 | CliRunner API, file system isolation, subcommand invocation | `docs/research/e2e-dispatch-integration-test.md` | 2026-03-30 |
| ACP SDK test_rpc.py | <https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py> | MIT | spawn_agent_process roundtrip pattern, TestClient fixture, mock agent testing | `docs/research/e2e-dispatch-integration-test.md` | 2026-03-30 |

## Gate-Blocked Task Remediation (Task #216)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub actions/stale action | <https://github.com/marketplace/actions/close-stale-issues> | MIT | Timer-based stale detection pattern: label after N days, close after M more; escalation before action | `docs/research/gate-blocked-task-remediation.md` | 2026-03-30 |
| GitLab CI blocked pipeline | <https://docs.gitlab.com/ci/jobs/job_control/> | MIT | Pipeline "blocked" status visibility for manual/blocking jobs; retry patterns | `docs/research/gate-blocked-task-remediation.md` | 2026-03-30 |
| Jenkins restart-from-stage | <https://www.jenkins.io/doc/book/pipeline/running-pipelines/> | CC-BY-SA-4.0 | Manual re-entry from any completed stage; user-initiated remediation, not automated | `docs/research/gate-blocked-task-remediation.md` | 2026-03-30 |
| Azure DevOps impediment tracking | <https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-issues-impediments> | CC-BY-4.0 | Blocker visibility via queries, aging-based escalation ("blockers active >7 days") | `docs/research/gate-blocked-task-remediation.md` | 2026-03-30 |

## Wire Audit Log into Dispatch Loop (Task #164)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| CrewAI Event Listeners | <https://docs.crewai.com/concepts/event-listener> | N/A | Event bus architecture with BaseEventListener, Started/Completed/Failed triplets, singleton CrewAIEventsBus pattern — evaluated as over-engineering for single-consumer audit | `docs/research/wire-audit-log-dispatch-loop.md` | 2026-03-30 |
| AutoGen `logging.py` event classes | <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/logging.py> | MIT | Typed event classes with JSON serialization via stdlib logging — evaluated as untyped at handler level | `docs/research/wire-audit-log-dispatch-loop.md` | 2026-03-30 |
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC-BY-SA-4.0 | Monotonic clock recommendation for duration measurement, append-only audit integrity | `docs/research/wire-audit-log-dispatch-loop.md` | 2026-03-30 |

## Orchestrator Audit Log Research (Task #21)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen `logging.py` event classes | <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/logging.py> | MIT | Typed event classes (LLMCallEvent, ToolCallEvent) with JSON `__str__`, stdlib logger pattern | `docs/research/orchestrator-audit-log.md` | 2026-03-29 |
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC-BY-SA-4.0 | When/where/who/what event schema, append-only storage, separate audit logs from app logs | `docs/research/orchestrator-audit-log.md` | 2026-03-29 |
| Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | MIT | TypeAdapter for JSONL serialization pattern | `docs/research/orchestrator-audit-log.md` | 2026-03-29 |

## manage_todo_list Subagent Removal (Task #193)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Cheat Sheet (2026-03-25) | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | `todos` tool description, canonical built-in tool list | `docs/research/manage-todo-list-subagent-removal.md` | 2026-03-30 |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Subagent context isolation, tool inheritance, collapsed execution model | `docs/research/manage-todo-list-subagent-removal.md` | 2026-03-30 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool enabling, tool type taxonomy | `docs/research/manage-todo-list-subagent-removal.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `tools:` frontmatter spec, unavailable tool behavior | `docs/research/manage-todo-list-subagent-removal.md` | 2026-03-30 |

## Extract retrieval.py (Task #159)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MS GraphRAG Local Search | <https://microsoft.github.io/graphrag/query/local_search> | MIT | Entity-based reasoning, neighbor fan-out, context-window budget | `docs/research/extract-retrieval-graphaugmentedretriever.md` | 2026-03-30 |
| LightRAG (HKUDS, EMNLP 2025) | <https://github.com/HKUDS/LightRAG> | MIT | KG + vector "mix" mode, token budget system | `docs/research/extract-retrieval-graphaugmentedretriever.md` | 2026-03-30 |

## E2E Dispatch Test Research (Task #23)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `test_rpc.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py> | Apache-2.0 | `spawn_agent_process` E2E roundtrip test, in-memory agent/client harness, TestClient/TestAgent patterns | `docs/research/e2e-dispatch-test.md` | 2026-03-29 |
| ACP Python SDK `conftest.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/tests/conftest.py> | Apache-2.0 | TestClient/TestAgent mock helpers, asyncio TCP loopback test server pattern | `docs/research/e2e-dispatch-test.md` | 2026-03-29 |
| ACP Python SDK `duet.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/duet.py> | Apache-2.0 | Two-process spawn pattern: client spawns agent subprocess, interactive loop | `docs/research/e2e-dispatch-test.md` | 2026-03-29 |
| ACP Architecture Spec | <https://agentclientprotocol.com/get-started/architecture> | N/A | ACP design philosophy, stdio setup, MCP forwarding architecture | `docs/research/e2e-dispatch-test.md` | 2026-03-29 |

## AcpClient Wrapper Validation (Task #59)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | Apache-2.0 | RequestError factory methods, 7 JSON-RPC error codes | `docs/research/acp-client-wrapper-validation.md` | 2026-03-29 |
| ACP Python SDK `client/connection.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | Apache-2.0 | ClientSideConnection method signatures, required params | `docs/research/acp-client-wrapper-validation.md` | 2026-03-29 |
| ACP Python SDK `utils.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/utils.py> | Apache-2.0 | `@param_model` is a no-op marker, `@compatible_class` wraps methods | `docs/research/acp-client-wrapper-validation.md` | 2026-03-29 |

## Necessity Check Code-Review (Task #196)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Google Eng-Practices: What to Look For in a Code Review | <https://google.github.io/eng-practices/review/reviewer/looking-for.html> | CC-BY-4.0 | Design section asks "Does this change belong in your codebase?"; Complexity warns against over-engineering | `docs/research/necessity-check-code-review.md` | 2026-03-29 |
| Martin Fowler — Yagni | <https://martinfowler.com/bliki/Yagni.html> | N/A | YAGNI principle; Kohavi et al. ⅔ of features don't improve metrics; cost-of-carry analysis | `docs/research/necessity-check-code-review.md` | 2026-03-29 |
| SmartBear — Best Practices for Peer Code Review | <https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/> | N/A | Checklists are the most effective way to eliminate omission-type errors | `docs/research/necessity-check-code-review.md` | 2026-03-29 |

## Environment Audit Research-Workflow (Task #194)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Google Eng-Practices: What to Look For in a Code Review | <https://google.github.io/eng-practices/review/reviewer/looking-for.html> | CC-BY-4.0 | Design section asks "Does this change belong in your codebase?" — prior art for environment necessity checks | `docs/research/environment-audit-research-workflow.md` | 2026-03-29 |
| Du et al. 2023 — Multi-agent Debate | <https://arxiv.org/abs/2305.14325> | CC-BY-4.0 | Sequential pipeline anchoring — agents inherit upstream assumptions without independent verification | `docs/research/environment-audit-research-workflow.md` | 2026-03-29 |

## Self-Improvement Analysis Pipeline (Task #31)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| v1 `improvement_proposals.py` | `v1/src/owlbear/core/improvement_proposals.py` | (internal) | Threshold-based pattern detection from EventStore, ImprovementProposal Pydantic model, generate_proposals() API | `docs/research/self-improvement-analysis-pipeline.md` | 2026-03-29 |
| v1 `observability.py` (EventStore) | `v1/src/owlbear/core/observability.py` | (internal) | EventStore.summary(), tool_stats() aggregation APIs consumed by analysis | `docs/research/self-improvement-analysis-pipeline.md` | 2026-03-29 |
| AutoGen event logging | <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/logging.py> | MIT | Typed event classes (LLMCallEvent, ToolCallEvent), per-agent attribution | `docs/research/self-improvement-analysis-pipeline.md` | 2026-03-29 |
| LangSmith evaluation concepts | <https://docs.langchain.com/langsmith/evaluation-concepts> | N/A | Code vs LLM-as-judge evaluators, offline/online evaluation patterns | `docs/research/self-improvement-analysis-pipeline.md` | 2026-03-29 |

## AcpClient Parameter Forwarding (Task #147)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `meta.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/meta.py> | Apache-2.0 | `PROTOCOL_VERSION = 1` constant, schema version v0.11.2 | `docs/research/acp-client-param-forwarding.md` | 2026-03-29 |
| ACP Python SDK `helpers.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/helpers.py> | Apache-2.0 | `text_block` helper, `ContentBlock` type alias for prompt content | `docs/research/acp-client-param-forwarding.md` | 2026-03-29 |

## Stale Tool Names Audit (Task #193)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Cheat Sheet — Chat Tools | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features#_chat-tools> | N/A | Canonical built-in tool list: `todos` confirmed as current name | `docs/research/stale-tool-names.md` | 2026-03-29 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | N/A | tools field spec, Claude agent format mapping | `docs/research/stale-tool-names.md` | 2026-03-29 |

## Knowledge Engine Extraction Research (Task #15)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG v3 | <https://github.com/microsoft/graphrag> | MIT | Multi-package monorepo layout, foundation-vs-layer separation, package boundary patterns | `docs/research/extract-knowledge-engine-v1.md` | 2026-03-28 |
| PrivateGPT (Zylon) | <https://github.com/zylon-ai/private-gpt> | Apache-2.0 | Component-based DI, abstraction-first storage patterns | `docs/research/extract-knowledge-engine-v1.md` | 2026-03-28 |
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | Frozen models, ConfigDict patterns used in knowledge models | `packages/knowledge/src/owlbear_knowledge/models.py` | 2026-03-28 |

## Multi-Project Setup Test Research (Task #25)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Parent repository discovery, customization settings, resolution mechanisms | `docs/research/multi-project-setup-test.md` | 2026-03-29 |
| VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agentFilesLocations setting, agent file locations, agent override behavior | `docs/research/multi-project-setup-test.md` | 2026-03-29 |
| VS Code agent skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | agentSkillsLocations setting, skill discovery, SKILL.md resolution | `docs/research/multi-project-setup-test.md` | 2026-03-29 |
| VS Code custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | instructionsFilesLocations setting, copilot-instructions.md priority | `docs/research/multi-project-setup-test.md` | 2026-03-29 |
| VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server config, naming conventions, on-demand lifecycle | `docs/research/multi-project-setup-test.md` | 2026-03-29 |

## README v2 Trim Assessment (Tasks #28, #93)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Code README | <https://github.com/anthropics/claude-code> | Proprietary | Concise README structure: one-liner, get started, plugins, links | `docs/research/readme-v2-rewrite.md`, `docs/research/readme-trim-assessment.md` | 2026-03-28 |
| Aider README | <https://github.com/Aider-AI/aider> | Apache-2.0 | Features + getting-started + docs links; secondary setup kept external | `docs/research/readme-trim-assessment.md` | 2026-03-29 |

## v2 ErrorJournal Module Research (Task #184)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | MIT | TypeAdapter dump_json/validate_json for JSONL serialization, create-once-reuse pattern | `docs/research/v2-errorjournal-module.md` | 2026-03-29 |
| jsonlines library docs | <https://jsonlines.readthedocs.io/en/latest/> | BSD-3 | JSONL append/read patterns, line-oriented persistence conventions | `docs/research/v2-errorjournal-module.md` | 2026-03-29 |

## Entity Extraction + Graph Builders Research (Task #33)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| fast-graphrag BaseLLMService | <https://github.com/circlemind-ai/fast-graphrag/blob/main/fast_graphrag/_llm/_base.py> | MIT | Protocol-based LLM abstraction, `send_message(response_model=)` pattern for structured output | `docs/research/extract-entity-extraction-graph-builders.md` | 2026-03-29 |
| nano-graphrag LLM functions | <https://github.com/gusye1234/nano-graphrag/blob/main/nano_graphrag/_llm.py> | MIT | Plain async callable pattern for LLM integration, no class hierarchy | `docs/research/extract-entity-extraction-graph-builders.md` | 2026-03-29 |
| Python Protocol PEP 544 | <https://docs.python.org/3/library/typing.html#typing.Protocol> | PSF | Runtime-checkable Protocol for structural subtyping (used for StructuredExtractor design) | `docs/research/extract-entity-extraction-graph-builders.md` | 2026-03-29 |

## Task #143 TDD RED Scope Validation (Task #143)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| v1 cancellation.py | `v1/src/owlbear/memory/knowledge/cancellation.py` | (internal) | CancelSignal Protocol + LinkedCancelSignal implementation (29 LOC) | `docs/research/task-143-tdd-red-scope-validation.md` | 2026-03-29 |
| v1 paths.py | `v1/src/owlbear/paths.py` | (internal) | sandbox_path() null-byte + traversal guard (36 LOC) | `docs/research/task-143-tdd-red-scope-validation.md` | 2026-03-29 |
| v1 consolidation.py | `v1/src/owlbear/memory/knowledge/consolidation.py` | (internal) | ConsolidationService constructor + PydanticAI Agent usage (114 LOC) | `docs/research/task-143-tdd-red-scope-validation.md` | 2026-03-29 |
| v1 evaluator.py | `v1/src/owlbear/memory/knowledge/evaluator.py` | (internal) | SourceEvaluator + EvaluationResult + PydanticAI Agent usage (167 LOC) | `docs/research/task-143-tdd-red-scope-validation.md` | 2026-03-29 |

## GitHub Remote MCP Server Integration (Task #121)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub MCP Server README | <https://github.com/github/github-mcp-server> | MIT | Canonical `type:http` + URL config for VS Code mcp.json | `scripts/setup.py` — `create_mcp_config()` | 2026-03-29 |
| VS Code MCP Server Guide | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> | CC-BY-4.0 | Remote server config format, `http` type semantics, VS Code mcp.json schema | `scripts/setup.py` — `create_mcp_config()` | 2026-03-29 |

## Orchestrator Dispatch Loop Research (Task #146)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK quickstart | <https://agentclientprotocol.github.io/python-sdk/quickstart/> | Apache-2.0 | `spawn_agent_process` lifecycle, `connect_to_agent`, session API (initialize/new_session/prompt) | `docs/research/orchestrator-dispatch-loop.md` | 2026-03-29 |
| ACP Python SDK `duet.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/duet.py> | Apache-2.0 | Two-process spawn pattern, interactive session loop | `docs/research/orchestrator-dispatch-loop.md` | 2026-03-29 |
| ACP Python SDK `client.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py> | Apache-2.0 | Full ExampleClient implementation, interactive_loop, conn.prompt() with text_block | `docs/research/orchestrator-dispatch-loop.md` | 2026-03-29 |
| OpenAI Symphony poll-dispatch-reconcile | <https://github.com/openai/symphony> | MIT | Daemon poll loop, reconciliation tick, stale detection, retry with backoff | `docs/research/orchestrator-dispatch-loop.md` | 2026-03-29 |

## OwlbearProjectFile Pydantic Model (Tasks #68, #74)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | BaseModel, ConfigDict extra='allow', model_validate_json | `packages/mcp-project/src/owlbear_mcp_project/models.py` | 2026-03-26 |
| Pydantic v2 Fields docs | <https://docs.pydantic.dev/latest/concepts/fields/> | MIT | Field(min_length, max_length) constraints for name and owlbear_path | `packages/mcp-project/src/owlbear_mcp_project/models.py` | 2026-03-26 |
| Pydantic v2 Standard Library Types — Datetimes | <https://docs.pydantic.dev/latest/api/standard_library_types/#datetime-types> | MIT | AwareDatetime rejects naive datetimes; requires timezone info | `packages/mcp-project/src/owlbear_mcp_project/models.py` | 2026-03-26 |
| Pydantic v2 Literal validation | <https://docs.pydantic.dev/latest/api/standard_library_types/#literals> | MIT | Literal type for schema_version and type enum validation patterns | `packages/mcp-project/tests/test_models.py` | 2026-03-26 |

## CLI Trigger Commands Research (Task #22)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer docs (main + testing + subcommands) | <https://typer.tiangolo.com/> | MIT | Type-hint CLI framework, CliRunner testing, subcommand patterns | `docs/research/cli-trigger-commands.md` | 2026-03-29 |
| Click docs (main + testing) | <https://click.palletsprojects.com/en/stable/> | BSD-3 | Comparison framework, CliRunner testing, decorator-based CLI | `docs/research/cli-trigger-commands.md` | 2026-03-29 |
| Typer PyPI (v0.24.1) | <https://pypi.org/project/typer/> | MIT | Dependency chain (click + rich + shellingham), version info | `docs/research/cli-trigger-commands.md` | 2026-03-29 |

## Planner Gate Checker & Selector Research (Task #145)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python 3.12 `re` module docs | <https://docs.python.org/3.12/library/re.html> | PSF-2.0 | Word-boundary regex for atomicity gate, multiline AC pattern matching | `docs/research/planner-gate-checker-selector.md` | 2026-03-29 |
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | Frozen model reuse for DispatchPlan construction in selector | `docs/research/planner-gate-checker-selector.md` | 2026-03-29 |
| Click PyPI (v8.3.1) | <https://pypi.org/project/click/> | BSD-3 | Version info, zero-dep footprint | `docs/research/cli-trigger-commands.md` | 2026-03-29 |

## VS Code Tools Evaluation (Task #95)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot Cheat Sheet | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Complete built-in tool list, `search/usages`, `search/changes`, `vscode/askQuestions` descriptions, Autopilot behavior | `docs/research/vs-code-new-tools-evaluation.md` | 2026-03-28 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool sets, approval model, tool set grouping, `search` set contents | `docs/research/vs-code-new-tools-evaluation.md` | 2026-03-28 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `tools` field semantics: explicit list restricts; missing tool is ignored silently | `docs/research/vs-code-new-tools-evaluation.md` | 2026-03-28 |

## search/changes Skill Integration Research (Task #102)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot Cheat Sheet | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | `#search/changes` tool description, `#search` tool set membership, runtime tool names | `docs/research/search-changes-skill-integration.md` | 2026-03-28 |

## Multi-Project Documentation Guide Research (Task #172)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot customization docs (Mar 2026) | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Parent repository discovery, Chat Customizations editor, Agent Debug Logs — new features since #25 research | `docs/research/multi-project-doc-guide.md` | 2026-03-29 |
| VS Code custom agents docs (Mar 2026) | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Organization-level agent sharing, `chat.agentFilesLocations` settings, agent override behavior updates | `docs/research/multi-project-doc-guide.md` | 2026-03-29 |
| Aider installation guide | <https://aider.chat/docs/install.html> | Apache-2.0 | Setup guide structure: prerequisites, quick start, verification, troubleshooting | `docs/research/multi-project-doc-guide.md` | 2026-03-29 |
| Claude Code getting-started guide | <https://code.claude.com/docs/en/getting-started> | Proprietary | Setup guide structure: system requirements, install, verify, authenticate | `docs/research/multi-project-doc-guide.md` | 2026-03-29 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool set grouping, `search` set contents including `search/changes`, tool set JSON example | `docs/research/search-changes-skill-integration.md` | 2026-03-28 |

## search/usages Skill Integration Research (Task #103)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot Cheat Sheet | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | `search/usages` tool description, runtime name `vscode_listCodeUsages`, supported language types, caller-tracing capability, `getattr` dynamic-call limitation | `docs/research/search-usages-skill-integration.md`, `.github/skills/code-review/SKILL.md`, `.github/skills/tdd-workflow/SKILL.md` | 2026-03-29 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool set JSON example confirming `search/usages` membership in `search` tool set | `docs/research/search-usages-skill-integration.md` | 2026-03-29 |

## Bookmark Pipeline & Refresh Extraction Research (Task #136)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| FastMCP Tools docs | <https://gofastmcp.com/servers/tools> | MIT | `@mcp.tool` decorator registration, `readOnlyHint` annotations, `Annotated` param descriptions, async tool support | `docs/research/extract-bookmark-refresh-mcp.md` | 2026-03-29 |

## Build mcp-knowledge Server Research (Task #16)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK README | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 decorator API, lifespan pattern, resource decorators, Context injection | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 2026-03-29 |
| MCP Reference Memory Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/memory> | MIT | Knowledge-graph-based MCP server prior art, tool/resource patterns | `docs/research/build-mcp-knowledge-server.md` | 2026-03-29 |

## Instruction File Porting Research (Task #10)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | `chat.instructionsFilesLocations` setting, `.instructions.md` file format, discovery locations, applyTo patterns | `instructions/*.instructions.md` | 2026-03-28 |
| VS Code Customization overview | <https://code.visualstudio.com/docs/copilot/customization/overview> | CC-BY-4.0 | Parent repository discovery, monorepo instruction patterns, Chat Customizations editor | `instructions/*.instructions.md` | 2026-03-28 |

## Multi-Project Setup Documentation Research (Task #175)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Parent repository discovery, customization scenarios, get-started steps | `docs/research/multi-project-setup-docs.md` | 2026-03-29 |
| VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agentFilesLocations setting, Diagnostics view access, agent override behavior | `docs/research/multi-project-setup-docs.md` | 2026-03-29 |
| VS Code agent skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | agentSkillsLocations setting, skill discovery mechanisms | `docs/research/multi-project-setup-docs.md` | 2026-03-29 |
| VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server config, MCP: List Servers command, troubleshooting steps | `docs/research/multi-project-setup-docs.md` | 2026-03-29 |
| VS Code troubleshooting docs | <https://code.visualstudio.com/docs/copilot/troubleshooting> | CC-BY-4.0 | Agent Debug Log panel, Chat Debug View, MCP server troubleshooting | `docs/research/multi-project-setup-docs.md` | 2026-03-29 |

## Vector Store + Embedding Pipeline Extraction Research (Task #32)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Qdrant Python client docs | <https://python-client.qdrant.tech/> | Apache-2.0 | Local mode API (`path=` constructor), prefetch/rescore, multivector config | `docs/research/extract-vector-store-embedding-pipeline.md` | 2026-03-29 |
| BGE-M3 model card (BAAI) | <https://huggingface.co/BAAI/bge-m3> | MIT | Model specs (1024-d, 8192 tokens, ~3 GB FP16), FlagEmbedding API, cache location | `docs/research/extract-vector-store-embedding-pipeline.md` | 2026-03-29 |
| Qdrant quickstart guide | <https://qdrant.tech/documentation/quickstart/> | Apache-2.0 | Local mode vs Docker guidance, recommended Python local-only approach | `docs/research/extract-vector-store-embedding-pipeline.md` | 2026-03-29 |

## CancelSignal, Consolidation & Evaluator Extraction Research (Task #135)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python typing.Callable docs | <https://docs.python.org/3/library/typing.html#typing.Callable> | PSF | Async callable type alias pattern for LLM injection | `docs/research/extract-cancel-sandbox-consolidation-evaluator.md` | 2026-03-29 |
| .NET CancellationToken docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC-BY-4.0 | Cooperative cancellation prior art: token-per-operation, linked parent/child composition | `docs/research/extract-cancel-sandbox-consolidation-evaluator.md` | 2026-03-29 |

## ACP Client Library Decomposition Validation (Task #19)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `interfaces.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/interfaces.py> | Apache-2.0 | Full `Client` protocol interface: 10 required async methods, `@param_model` decorators, session_update union types | `docs/research/acp-client-library-decomposition.md` | 2026-03-28 |
| ACP Python SDK `core.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/core.py> | Apache-2.0 | `connect_to_agent()` implementation, 50MB stdio buffer, `ClientSideConnection` wiring confirms NDJSON is SDK-handled | `docs/research/acp-client-library-decomposition.md` | 2026-03-28 |

## Build Dispatch Planner Research (Task #20)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK quickstart | <https://agentclientprotocol.github.io/python-sdk/quickstart/> | Apache-2.0 | `spawn_agent_process` pattern, programmatic session/prompt dispatch | `docs/research/build-dispatch-planner.md` | 2026-03-29 |
| ACP architecture docs | <https://agentclientprotocol.com/get-started/architecture> | Unknown | Agent-client architecture, stdio JSON-RPC setup, MCP server forwarding | `docs/research/build-dispatch-planner.md` | 2026-03-29 |

## KB Curation Process Research (Task #177)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex IngestionPipeline (Document Management) | <https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/> | MIT | doc_id → document_hash dedup, docstore skip-if-unchanged, upsert-on-change pattern | `docs/research/kb-curation-process.md` | 2026-03-29 |

## Instructions README Update Research (Task #109)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Instructions docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | `.instructions.md` format, `applyTo` patterns, YAML frontmatter schema | `docs/research/instructions-readme-update.md` | 2026-03-28 |

## MCP Server Registry Research (Task #18)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | Config schema, stdio/http types, camelCase naming, sandbox/dev mode, input variables | `docs/research/mcp-server-registry.md` | 2026-03-29 |
| VS Code MCP Server Guide | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> | CC-BY-4.0 | Remote server config, gallery install flow, server trust model, troubleshooting | `docs/research/mcp-server-registry.md` | 2026-03-29 |
| GitHub MCP Server README | <https://github.com/github/github-mcp-server> | MIT | Canonical `type:http` config for VS Code mcp.json, OAuth via Copilot | `scripts/setup.py` — `create_mcp_config()` | 2026-03-29 |
| Playwright MCP Server | <https://github.com/microsoft/playwright-mcp> | Apache-2.0 | Evaluated for inclusion; excluded (YAGNI — Node.js dep, not core) | `docs/research/mcp-server-registry.md` | 2026-03-29 |

## Monorepo Tooling Research (Task #6)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| uv workspaces docs | <https://docs.astral.sh/uv/concepts/projects/workspaces/> | MIT | Workspace configuration, member globs, editable installs, single lockfile, requires-python intersection | `docs/research/monorepo-tooling.md` | 2026-03-26 |
| uv dependency management docs | <https://docs.astral.sh/uv/concepts/projects/dependencies/> | MIT | Dependency groups (PEP 735), workspace sources, dev dependency isolation, optional dependencies | `docs/research/monorepo-tooling.md` | 2026-03-26 |
| uv project init docs | <https://docs.astral.sh/uv/concepts/projects/init/> | MIT | uv_build backend as default for new packages, src layout, project.scripts for CLI entry points | `docs/research/monorepo-tooling.md` | 2026-03-26 |
| pydantic-ai monorepo | <https://github.com/pydantic/pydantic-ai> | MIT | Real-world uv workspace with 5+ members, workspace sources, hatchling backend, dependency-groups | `docs/research/monorepo-tooling.md` | 2026-03-26 |
| MCP Python SDK monorepo | <https://github.com/modelcontextprotocol/python-sdk> | MIT | MCP server workspace layout, project.scripts for server entry points, workspace sources | `docs/research/monorepo-tooling.md` | 2026-03-26 |
| pydantic/logfire monorepo | <https://github.com/pydantic/logfire> | MIT | Minimal uv workspace with 1 member, hatchling backend, workspace sources pattern | `docs/research/monorepo-tooling.md` | 2026-03-26 |

## Monorepo Skeleton Implementation Research (Task #7)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| uv workspace docs | <https://docs.astral.sh/uv/concepts/projects/workspaces/> | MIT | Workspace layout, member glob, workspace sources | `docs/research/monorepo-skeleton.md` | 2026-03-27 |
| uv project init docs | <https://docs.astral.sh/uv/concepts/projects/init/> | MIT | uv_build backend, --package flag, src layout convention | `docs/research/monorepo-skeleton.md` | 2026-03-27 |
| VS Code Copilot settings ref | <https://code.visualstudio.com/docs/copilot/reference/copilot-settings> | CC-BY-4.0 | chat.agentFilesLocations, chat.agentSkillsLocations, chat.instructionsFilesLocations settings | `docs/research/monorepo-skeleton.md` | 2026-03-27 |
| VS Code customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Monorepo parent repository discovery, customization file conventions | `docs/research/monorepo-skeleton.md` | 2026-03-27 |

## python.instructions.md v2 Update Research (Task #91)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest — Good Integration Practices | <https://docs.pytest.org/en/stable/explanation/goodpractices.html> | MIT | `--import-mode=importlib` rationale, src-layout test discovery, recommended config | `docs/research/python-instructions-v2-update.md` | 2026-03-29 |
| pytest — Import mechanisms and sys.path | <https://docs.pytest.org/en/stable/explanation/pythonpath.html> | MIT | importlib mode semantics, sys.path non-mutation, duplicate test name support | `docs/research/python-instructions-v2-update.md` | 2026-03-29 |

## pytest-and-linting Skill v2 Paths Research (Task #90)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest — Good Integration Practices | <https://docs.pytest.org/en/stable/explanation/goodpractices.html> | MIT | `--import-mode=importlib` rationale, `testpaths` config, src-layout test discovery | `docs/research/pytest-linting-skill-v2-paths.md` | 2026-03-29 |
| coverage.py configuration reference | <https://coverage.readthedocs.io/en/latest/config.html> | Apache-2.0 | `source_pkgs` vs `source` semantics, TOML config syntax | `docs/research/pytest-linting-skill-v2-paths.md` | 2026-03-29 |
| pytest-cov configuration docs | <https://pytest-cov.readthedocs.io/en/latest/config.html> | MIT | Bare `--cov` picks up `source_pkgs` from config file | `docs/research/pytest-linting-skill-v2-paths.md` | 2026-03-29 |

## v2 Test Infrastructure Research (Task #35)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest Good Integration Practices | <https://docs.pytest.org/en/stable/explanation/goodpractices.html> | MIT | testpaths, import-mode, src layout, test discovery conventions | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |
| pydantic-ai pyproject.toml | <https://github.com/pydantic/pydantic-ai> | MIT | Real-world uv workspace pytest/ruff/coverage config, testpaths approach, filterwarnings | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |
| ruff Configuration docs | <https://docs.astral.sh/ruff/configuration/> | MIT | Hierarchical config, src setting for import sorting, per-file-ignores patterns | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |
| hynek Testing & Packaging | <https://hynek.me/articles/testing-packaging/> | CC | src layout benefits, combined coverage with paths config, source_pkgs approach | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |

## Impeccable Design Skill Research (Task #929)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Enhanced frontend-design skill structure, seven reference files, anti-pattern catalog, and NOTICE-based attribution model | `docs/research/impeccable-design-skills.md` | 2026-03-22 |
| Impeccable website | <https://impeccable.style> | N/A | Public positioning of anti-pattern examples, command taxonomy, and provider support including VS Code Copilot | `docs/research/impeccable-design-skills.md` | 2026-03-22 |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Baseline frontend-design skill that Impeccable extends | `docs/research/impeccable-design-skills.md` | 2026-03-22 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Skills vs custom instructions, progressive loading, and resource-backed skill structure for OwlBear adoption planning | `docs/research/impeccable-design-skills.md` | 2026-03-22 |

## MCP Entry Points Overlap Analysis (Task #120)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK v1 README | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP entry point pattern, `mcp.run()` stdio default, `__main__.py` convention | `docs/research/mcp-entry-points-overlap.md` | 2026-03-29 |
| MCP Quickstart (server) | <https://modelcontextprotocol.io/quickstart/server> | CC-BY-4.0 | Direct execution pattern, `if __name__ == "__main__": mcp.run()` | `docs/research/mcp-entry-points-overlap.md` | 2026-03-29 |

## Build mcp-project Server Research (Task #17)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK v1 README | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 resource/tool decorators, lifespan pattern, Context injection, `mcp.run()` entry point | `docs/research/build-mcp-project-server.md` | 2026-03-28 |
| MCP Resources Spec (2025-06-18) | <https://modelcontextprotocol.io/specification/2025-06-18/server/resources> | CC-BY-4.0 | Custom URI scheme rules (§6.4), resource data types, error handling, annotations | `docs/research/build-mcp-project-server.md` | 2026-03-28 |
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server registration in `.vscode/mcp.json`, dev watch, naming conventions | `docs/research/build-mcp-project-server.md` | 2026-03-28 |

## Expand mcp-kanban Tools Research (Task #56)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK README (v1) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP tool decorator patterns, lifespan context injection, subprocess-wrapping tool design | `docs/research/expand-mcp-kanban-tools.md` | 2026-03-26 |
| kanban-md CLI v0.33.0 | Local binary (`kanban/kanban-md.exe --help`) | N/A | Full CLI command surface, flag comparison vs v1 KanbanToolset signatures | `docs/research/expand-mcp-kanban-tools.md` | 2026-03-26 |

## Frontend-Design Skill Implementation Gate (Task #934)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Raw `frontend-design` skill structure, reference-pack layout, and NOTICE-based attribution model to adapt rather than copy | `docs/research/frontend-design-skill-implementation-gate.md` | 2026-03-22 |
| Impeccable website | <https://impeccable.style> | N/A | Public command taxonomy and reference-pack framing used to bound what #934 should exclude | `docs/research/frontend-design-skill-implementation-gate.md` | 2026-03-22 |

## Copilot Memory Research (Task #5)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code settings reference — Memory settings | <https://code.visualstudio.com/docs/copilot/reference/copilot-settings> | CC-BY-4.0 | Two memory systems (built-in tool vs GitHub-hosted), settings, default states | `docs/research/copilot-memory.md` | 2026-03-26 |
| VS Code cheat sheet — Planning section | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Memory tool description, management command, three storage scopes | `docs/research/copilot-memory.md` | 2026-03-26 |
| GitHub Docs — About agentic memory for Copilot | <https://docs.github.com/en/copilot/concepts/agents/copilot-memory> | CC-BY-4.0 | 28-day auto-expiry, citation-based validation, repository-scoped memories, Pro/Pro+ default enabled | `docs/research/copilot-memory.md` | 2026-03-28 |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Baseline frontend-design wording and design-direction guidance beneath the adapted OwlBear skill | `docs/research/frontend-design-skill-implementation-gate.md` | 2026-03-22 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Skill folder structure, default invocation behavior, and relative resource guidance for OwlBear packaging | `docs/research/frontend-design-skill-implementation-gate.md` | 2026-03-22 |

## ProcessSupervisor ACP Research (Task #58)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | Apache-2.0 | `_shutdown` pattern (terminate/wait/kill), subprocess spawn with stdin/stdout PIPE, `shutil.which` binary resolution | `packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py` | 2026-03-26 |
| mcp-copilot-acp `process-manager.ts` | <https://github.com/bsmi021/mcp-copilot-acp/blob/main/src/process-manager.ts> | MIT | ProcessManager class with restart budget (max 3), `ensure()`/`shutdown()` lifecycle, graceful shutdown grace period | `packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py` | 2026-03-26 |
| Python asyncio subprocess docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | PSF-2.0 | `create_subprocess_exec` API, `Process.terminate()`/`kill()` semantics, Windows ProactorEventLoop notes | `packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py` | 2026-03-26 |

## Real search_knowledge Tool Research (Task #54)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK v1 README | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP lifespan context injection, tool decorator patterns, async tool execution | `docs/research/search-knowledge-tool-impl.md` | 2026-03-26 |
| Qdrant MCP Server (v0.8.1) | <https://github.com/qdrant/mcp-server-qdrant> | Apache-2.0 | Real tool implementation with backend connector, result formatting (XML entry tags), find/store tool patterns | `docs/research/search-knowledge-tool-impl.md` | 2026-03-26 |

## Classify Error ACP Extension Research (Task #60)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| JSON-RPC 2.0 specification | <https://www.jsonrpc.org/specification> | CC | Standard error codes (-32700 to -32603), reserved range -32000 to -32099 | `docs/research/classify-error-acp-extension.md` | 2026-03-26 |
| ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | Apache-2.0 | `RequestError(code, message, data)` interface, factory methods for 7 error codes | `docs/research/classify-error-acp-extension.md` | 2026-03-26 |
| MCP Python SDK `exceptions.py` | <https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/shared/exceptions.py> | MIT | `MCPError.code` pattern confirming JSON-RPC `.code` attribute convention across SDKs | `docs/research/classify-error-acp-extension.md` | 2026-03-26 |

## Frontend-Design Skill RED Test Gate (Task #941)

## Daemon Builder Dispatch Usage Tracking (Task #845)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agent.run API | <https://ai.pydantic.dev/api/agent/> | MIT | AgentRunResult.usage() return shape and usage accumulator parameter | `docs/research/daemon-usage-tracking.md` | 2026-03-25 |
| PydanticAI RunUsage API | <https://ai.pydantic.dev/api/usage/> | MIT | RunUsage dataclass fields and incr method for accumulation pattern | `docs/research/daemon-usage-tracking.md` | 2026-03-25 |

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Required skill directory layout, frontmatter contract, progressive loading, and co-located resource-file model that the RED tests should target | `docs/research/frontend-design-skill-red-test-gate.md` | 2026-03-22 |

## README v2 Rewrite Research (Task #28)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Code README | <https://github.com/anthropics/claude-code> | BSD-3-Clause | Concise README structure: one-liner, get started, plugins, links | `docs/research/readme-v2-rewrite.md` | 2026-03-28 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `.agent.md` format, workspace discovery, agent picker behavior, prerequisites | `docs/research/readme-v2-rewrite.md` | 2026-03-28 |
| VS Code MCP Servers docs | <https://code.visualstudio.com/docs/copilot/customization/mcp-servers> | CC-BY-4.0 | MCP server configuration via `.vscode/mcp.json`, tool discovery, server management | `docs/research/readme-v2-rewrite.md` | 2026-03-28 |

## mcp-kanban Integration Tests Research (Task #57)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK test suite (v1.26.0) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | `mcp.shared.memory.create_connected_server_and_client_session` in-memory testing pattern, `client_session(mcp._mcp_server)` idiom for tool testing without transport | `docs/research/mcp-kanban-integration-tests.md` | 2026-03-27 |
| MCP Transports spec | <https://modelcontextprotocol.io/docs/concepts/transports> | CC-BY-4.0 | stdio transport model: client launches subprocess, newline-delimited JSON-RPC on stdin/stdout | `docs/research/mcp-kanban-integration-tests.md` | 2026-03-27 |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Minimal `frontend-design` package precedent used to avoid over-asserting optional files beyond `SKILL.md` | `docs/research/frontend-design-skill-red-test-gate.md` | 2026-03-22 |
| pbakaus/impeccable | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Reference-pack skill precedent used to justify asserting the seven required `references/*.md` files in the RED contract | `docs/research/frontend-design-skill-red-test-gate.md` | 2026-03-22 |

## owlbear-project.json Schema Specification (Task #53)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| JSON Schema `$schema` keyword | <https://json-schema.org/understanding-json-schema/reference/schema> | Unknown | Schema dialect declaration, `$schema` keyword usage, vocabulary guidelines for extensibility patterns | `docs/research/owlbear-project-json-schema.md` | 2026-03-26 |
| npm package.json spec | <https://docs.npmjs.com/cli/v10/configuring-npm/package-json> | Artistic-2.0 | Project manifest field conventions (name, version, description), open-schema extensibility, versioning patterns | `docs/research/owlbear-project-json-schema.md` | 2026-03-26 |
| pyproject.toml spec (PEP 621) | <https://packaging.python.org/en/latest/specifications/pyproject-toml/> | CC0 | `[project]` table required vs optional fields, `[tool]` open namespace for unknown keys, dynamic metadata | `docs/research/owlbear-project-json-schema.md` | 2026-03-26 |
| Dev Container JSON reference | <https://containers.dev/implementors/json_reference/> | MIT | devcontainer.json schema structure, property categories, schema URL hosting pattern | `docs/research/owlbear-project-json-schema.md` | 2026-03-26 |

## Build Setup Script Research (Task #12)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Agent/skill/instruction location settings format, dict-based path mapping | `docs/research/setup-script.md` | 2026-03-28 |
| VS Code MCP config reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | `.vscode/mcp.json` format, stdio server configuration, camelCase naming | `docs/research/setup-script.md` | 2026-03-28 |
| Copier project scaffolder | <https://github.com/copier-org/copier> | MIT | Template engine approach evaluated as alternative to single-script architecture | `docs/research/setup-script.md` | 2026-03-28 |
| Cookiecutter docs | <https://cookiecutter.readthedocs.io/en/stable/overview.html> | BSD-3-Clause | Template scaffolding approach evaluated as alternative | `docs/research/setup-script.md` | 2026-03-28 |
| Python os.path.relpath docs | <https://docs.python.org/3/library/os.path.html#os.path.relpath> | PSF-2.0 | Cross-platform relative path computation, ValueError on cross-drive Windows paths | `docs/research/setup-script.md` | 2026-03-28 |
| npm init behavior | <https://docs.npmjs.com/cli/v10/commands/npm-init> | Artistic-2.0 | Idempotency pattern (infer defaults, skip existing), per-file skip approach | `docs/research/setup-script.md` | 2026-03-28 |

## OwlbearProjectFile Model Implementation (Task #68)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | `ConfigDict(extra='allow')` semantics, `model_validate_json()` for JSON-first validation | `docs/research/owlbear-project-file-model-impl.md` | 2026-03-26 |
| Pydantic v2 Fields docs | <https://docs.pydantic.dev/latest/concepts/fields/> | MIT | `Field(ge=, le=, min_length=, max_length=)` constraint patterns for schema validation | `docs/research/owlbear-project-file-model-impl.md` | 2026-03-26 |
| Pydantic v2 Standard Library Types — Datetimes | <https://docs.pydantic.dev/latest/api/standard_library_types/#datetime-types> | MIT | `AwareDatetime` type for enforcing timezone-aware datetimes without custom validators | `docs/research/owlbear-project-file-model-impl.md` | 2026-03-26 |

## Argument-Hint for User-Invocable Skills (Task #43)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | `argument-hint` optional YAML frontmatter field — hint text shown in chat input when skill invoked as slash command | `docs/research/argument-hint-user-invocable-skills.md` | 2026-03-27 |
| agentskills.io specification | <https://agentskills.io/specification> | Unknown | Confirmed `argument-hint` is VS Code-specific extension, not part of agentskills.io open spec | `docs/research/argument-hint-user-invocable-skills.md` | 2026-03-27 |

## ACP Error Handling Strategy (Task #47)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| JSON-RPC 2.0 specification | <https://www.jsonrpc.org/specification> | CC-BY | Standard error codes (-32700 to -32603), error object structure, notification semantics | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |
| ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | Apache-2.0 | `RequestError` class with factory methods for all 7 ACP/JSON-RPC error codes | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |
| ACP Python SDK `examples/gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | Apache-2.0 | Process shutdown pattern (terminate, wait_for 5s, kill), RequestError handling per method | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |
| ACP Python SDK `examples/client.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py> | Apache-2.0 | Subprocess spawn + cleanup pattern, returncode-based crash detection | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |
| mcp-copilot-acp | <https://github.com/bsmi021/mcp-copilot-acp> | MIT | Timeout (300s default), max restarts (3), process recovery configuration | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |
| ACP specification (architecture) | <https://agentclientprotocol.com/get-started/architecture> | N/A | Protocol architecture, stdio transport design, no built-in timeout | `docs/research/acp-error-handling-strategy.md` | 2026-03-26 |

## Scaffold mcp-kanban Research (Task #39)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK README (v1 stable) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 `@mcp.tool()`, lifespan pattern, stdio transport, `mcp.run()` entry point | `docs/research/scaffold-mcp-kanban.md` | 2026-03-27 |
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server registration format in `.vscode/mcp.json`, dev watch mode | `docs/research/scaffold-mcp-kanban.md` | 2026-03-27 |
| OwlBear KanbanToolset (v1) | `v1/src/owlbear/tools/kanban.py` | N/A (internal) | `_run_kanban()` subprocess helper, 7 tool signatures, hook emission pattern | `docs/research/scaffold-mcp-kanban.md` | 2026-03-27 |
| modelcontextprotocol/servers | <https://github.com/modelcontextprotocol/servers> | MIT | Reference MCP server patterns, CLI-wrapping examples, ecosystem conventions | `docs/research/scaffold-mcp-kanban.md` | 2026-03-27 |

## Ingest and Graph Tools mcp-knowledge Research (Task #55)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Qdrant MCP Server (v0.8.1) | <https://github.com/qdrant/mcp-server-qdrant> | Apache-2.0 | Two-tool surface (store/find), metadata parameter design, tool description patterns | `docs/research/ingest-graph-tools-mcp-knowledge.md` | 2026-03-26 |
| MCP Official Memory Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/memory> | MIT | 8-tool graph CRUD surface, entity/relation model, `read_graph` no-pagination pattern | `docs/research/ingest-graph-tools-mcp-knowledge.md` | 2026-03-26 |
| FastMCP Tools Documentation | <https://gofastmcp.com/servers/tools> | N/A | `@mcp.tool` decorator, `Annotated` param descriptions, `readOnlyHint` annotations, error handling | `docs/research/ingest-graph-tools-mcp-knowledge.md` | 2026-03-26 |

## AcpClient Test Strategy Research (Task #94)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK `client/connection.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | Apache-2.0 | `ClientSideConnection` API surface: `initialize`, `new_session`, `prompt`, `cancel`, `close` method signatures and return types | `docs/research/acp-client-test-strategy.md` | 2026-03-28 |
| ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | Apache-2.0 | `RequestError(code, message, data)` constructor and factory methods for mocking | `docs/research/acp-client-test-strategy.md` | 2026-03-28 |

## Scaffold mcp-knowledge Research (Task #40)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK README (v1 stable) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 lifespan pattern, decorator API, stdio transport, `mcp.run()` entry point | `docs/research/scaffold-mcp-knowledge.md` | 2026-03-26 |
| Qdrant MCP Server | <https://github.com/qdrant/mcp-server-qdrant> | Apache-2.0 | Two-tool surface (store/find), env var config, lifespan with Qdrant client, VS Code registration pattern | `docs/research/scaffold-mcp-knowledge.md` | 2026-03-26 |
| MCP Official Memory Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/memory> | MIT | Knowledge graph MCP server with 8 tools, in-memory graph pattern, entity/relation model | `docs/research/scaffold-mcp-knowledge.md` | 2026-03-26 |
| MCP Resources Spec | <https://modelcontextprotocol.io/docs/concepts/resources> | CC-BY-4.0 | Resource primitive definition, URI templates, read-only context data pattern | `docs/research/scaffold-mcp-knowledge.md` | 2026-03-26 |

## Voice Addon STT with Moonshine (Task #50)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice GitHub (v0.0.51) | <https://github.com/moonshine-ai/moonshine> | MIT | Full Python API: MicTranscriber, TranscriptEventListener, ModelArch, get_model_for_language() | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |
| Moonshine mic_transcriber.py source | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/mic_transcriber.py> | MIT | MicTranscriber wraps Transcriber + sounddevice.InputStream, event dispatch on audio thread | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |
| Moonshine transcriber.py source | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/transcriber.py> | MIT | Stream._emit() typed event dispatch, TranscriptEventListener ABC, ctypes C bindings | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |
| Moonshine Ollama voice example | <https://github.com/moonshine-ai/moonshine/blob/main/examples/python/ollama-voice/ollama_voice.py> | MIT | Real-world TranscriptEventListener subclass, on_line_completed for downstream processing | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |
| v1 StreamingSTT | `v1/src/owlbear/voice/streaming_stt.py` | N/A (internal) | Lazy creation, async bridge, start/stop/close lifecycle | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |
| v1 STTEngine (batch) | `v1/src/owlbear/voice/stt.py` | N/A (internal) | _ensure_transcriber() lazy loading pattern | `docs/research/voice-addon-stt-moonshine.md` | 2026-03-26 |

## Context Hydration Migration Re-Research (Task #826)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python unittest.mock docs | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | PSF | Official module-local patch target guidance confirming correct seam after migration | `docs/research/context-hydration-migration-already-implemented.md` | 2026-03-26 |

## Scaffold mcp-project Server Research (Task #41)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK README | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 decorator patterns (@mcp.tool, @mcp.resource), stdio transport, entry point conventions | `docs/research/scaffold-mcp-project-server.md` | 2026-03-26 |
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | .vscode/mcp.json stdio server registration format, dev watch, naming conventions | `docs/research/scaffold-mcp-project-server.md` | 2026-03-26 |
| modelcontextprotocol/servers | <https://github.com/modelcontextprotocol/servers> | MIT | Reference MCP server package structures, entry point patterns, uvx execution | `docs/research/scaffold-mcp-project-server.md` | 2026-03-26 |
| Cosmic Python ch. 2 — Repository Pattern | <https://www.cosmicpython.com/book/chapter_02_repository.html> | CC-BY-NC-ND | Dependency-direction inversion prior art for keeping core logic free of adapter imports | `docs/research/context-hydration-migration-already-implemented.md` | 2026-03-26 |

## ACP Protocol Deep-Dive (Task #1)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP specification (official) | <https://agentclientprotocol.com/> | Apache-2.0 | Protocol architecture, lifecycle, message types, capabilities negotiation | `docs/research/acp-protocol.md` | 2026-03-26 |
| ACP GitHub (schema + repo) | <https://github.com/agentclientprotocol/agent-client-protocol> | Apache-2.0 | JSON schema (v0.11.3), all request/response/notification types, error codes | `docs/research/acp-protocol.md` | 2026-03-26 |
| ACP Python SDK | <https://github.com/agentclientprotocol/python-sdk> | Apache-2.0 | Official client/agent library (v0.9.0), connect_to_agent flow, Pydantic models, examples | `docs/research/acp-protocol.md` | 2026-03-26 |
| mcp-copilot-acp | <https://github.com/bsmi021/mcp-copilot-acp> | MIT | Real-world ACP client impl, session lifecycle, timeout patterns, YOLO mode | `docs/research/acp-protocol.md` | 2026-03-26 |
| rest-acp | <https://github.com/iot2020/rest-acp> | MIT | Session management patterns, multi-turn context, process lifecycle | `docs/research/acp-protocol.md` | 2026-03-26 |

## ACP Hello-World Script Research (Task #45)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ACP Python SDK quickstart | <https://agentclientprotocol.github.io/python-sdk/quickstart/> | Apache-2.0 | spawn_agent_process helper, connect_to_agent pattern, Client interface requirements | `docs/research/acp-hello-world.md` | 2026-03-26 |
| Copilot CLI ACP server docs | <https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server> | CC-BY-4.0 | Official --acp --stdio flags, TypeScript integration example, stdio transport details | `docs/research/acp-hello-world.md` | 2026-03-26 |
| Copilot CLI about page | <https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli> | CC-BY-4.0 | --allow-all-tools flag, tool approval options, security considerations | `docs/research/acp-hello-world.md` | 2026-03-26 |
| ACP SDK contrib docs | <https://agentclientprotocol.github.io/python-sdk/contrib/> | Apache-2.0 | SessionAccumulator, ToolCallTracker utility patterns for future use | `docs/research/acp-hello-world.md` | 2026-03-26 |

## Setup Script Project JSON Generation (Task #69)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python os.path.relpath docs | <https://docs.python.org/3/library/os.path.html#os.path.relpath> | PSF-2.0 | Pure string-based relative path computation, cross-drive ValueError on Windows | `docs/research/setup-script-project-json-generation.md` | 2026-03-26 |
| Python pathlib PurePath.as_posix docs | <https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.as_posix> | PSF-2.0 | Forward-slash normalization for cross-platform JSON path storage | `docs/research/setup-script-project-json-generation.md` | 2026-03-26 |
| npm init CLI reference | <https://docs.npmjs.com/cli/v10/commands/npm-init> | Artistic-2.0 | Default inference pattern (name from dirname), idempotency behavior | `docs/research/setup-script-project-json-generation.md` | 2026-03-26 |

## Test: owlbear-project.json Generation Research (Task #75)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest tmp_path fixture docs | <https://docs.pytest.org/en/stable/how-to/tmp_path.html> | MIT | `tmp_path` fixture for filesystem isolation in tests, session-scoped `tmp_path_factory` | `docs/research/test-project-json-generation.md` | 2026-03-26 |
| Pydantic v2 Serialization docs | <https://docs.pydantic.dev/latest/concepts/serialization/> | MIT | `model_dump_json(indent=2)` for JSON serialization, `model_validate_json()` for round-trip testing | `docs/research/test-project-json-generation.md` | 2026-03-26 |

## search_structured Method Research (Task #70)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex NodeWithScore schema | <https://developers.llamaindex.ai/python/framework-api-reference/schema/> | MIT | `NodeWithScore(node, score)` pattern — separating scored wrapper from data node, frozen Pydantic BaseModel result types | `docs/research/search-structured-method.md` | 2026-03-26 |
| Qdrant MCP Server (v0.8.1) | <https://github.com/qdrant/mcp-server-qdrant> | Apache-2.0 | `qdrant-find` tool returns information as separate messages, XML-tagged entry format for structured results | `docs/research/search-structured-method.md` | 2026-03-26 |

## Voice Addon Architecture Research (Task #30)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice | <https://github.com/moonshine-ai/moonshine> | MIT (English) | Streaming STT models (26-245M params), live latency benchmarks, event-based API, built-in VAD+diarization | `docs/research/voice-addon-architecture.md` | 2026-03-26 |
| OpenAI Whisper | <https://github.com/openai/whisper> | MIT | Reference STT model sizes (39M-1.5B), WER baselines, batch-only 30s fixed window architecture | `docs/research/voice-addon-architecture.md` | 2026-03-26 |
| Kokoro TTS | <https://github.com/hexgrad/kokoro> | Apache-2.0 | 82M param neural TTS, generator-based streaming API, espeak-ng dependency, multi-language support | `docs/research/voice-addon-architecture.md` | 2026-03-26 |
| Piper TTS (piper1-gpl) | <https://github.com/OHF-Voice/piper1-gpl> | GPL-3.0 | Fast local neural TTS, C++ core, license change from original MIT to GPL-3.0, maintenance status | `docs/research/voice-addon-architecture.md` | 2026-03-26 |
| Silero VAD | <https://github.com/snakers4/silero-vad> | MIT | Voice Activity Detection, <1ms per chunk, 2MB model, ONNX Runtime support | `docs/research/voice-addon-architecture.md` | 2026-03-26 |

## User-Invocable Skills Research (Task #42)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | `user-invocable` SKILL.md frontmatter property, slash-command visibility control, behavior matrix | `docs/research/user-invocable-skills.md` | 2026-03-26 |

## GraphEnricher Cancellation Test Approach (Task #1000)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | PSF-2.0 | `Task.cancel()` semantics, `asyncio.gather(return_exceptions=True)` shutdown pattern, strong-ref `background_tasks` set idiom | `docs/research/graphenricher-cancellation-test-approach.md` | 2026-03-25 |

## Cancellation Regression Coverage Gap Analysis (Task #872)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | PSF-2.0 | CancelledError propagation semantics; gather(return\_exceptions=True) re-raise pattern for regression test design | `docs/research/cancellation-regression-coverage.md` | 2026-03-26 |
| .NET CancellationToken cooperative pattern | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC-BY-4.0 | Linked token composition and cross-boundary regression testing patterns for cooperative cancellation | `docs/research/cancellation-regression-coverage.md` | 2026-03-26 |

## EntityExtractor Benchmark Corpus Implementation Gate (Task #912)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| spaCy data formats docs | <https://spacy.io/api/data-formats> | MIT | Text-plus-annotation corpus shapes for entity evaluation benchmarks | `docs/research/entity-extractor-corpus-implementation-gate.md` | 2026-03-26 |
| GraphRAG inputs docs | <https://microsoft.github.io/graphrag/index/inputs/> | MIT | Document schema (id, text, title, metadata) and text-unit provenance model for benchmark corpus design | `docs/research/entity-extractor-corpus-implementation-gate.md` | 2026-03-26 |

## Impeccable Command Pattern Research (Task #930)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable | <https://github.com/pbakaus/impeccable> | Apache-2.0 | `source/skills/*`, generated `.agents/.claude` outputs, build sync, `teach-impeccable`, and the audit-normalize-polish command pipeline | `docs/research/impeccable-command-patterns.md` | 2026-03-22 |
| Impeccable website | <https://impeccable.style> | N/A | Public command taxonomy, staged workflow categories, supported-tool matrix, and changelog entries for the unified skills architecture | `docs/research/impeccable-command-patterns.md` | 2026-03-22 |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Baseline shared-skill precedent used to separate Impeccable's reusable knowledge layer from its added command layer | `docs/research/impeccable-command-patterns.md` | 2026-03-22 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | `user-invocable`, `argument-hint`, slash-command behavior, progressive loading, and skill-vs-prompt tradeoffs for OwlBear adoption | `docs/research/impeccable-command-patterns.md` | 2026-03-22 |

## Ruflo Analysis (Task #947)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ruvnet/ruflo README | <https://github.com/ruvnet/ruflo> | MIT | High-level platform claims, worker catalog, hook system, MCP surface, swarm taxonomy, and programmatic usage surface | `docs/research/ruflo-analysis.md` | 2026-03-23 |
| ruvnet/ruflo AGENTS.md | <https://raw.githubusercontent.com/ruvnet/ruflo/main/AGENTS.md> | MIT | Codex or Claude coordination model, agent types, execution responsibilities, and command patterns | `docs/research/ruflo-analysis.md` | 2026-03-23 |
| ruvnet/ruflo agent definitions | <https://github.com/ruvnet/ruflo/tree/main/agents> | MIT | YAML agent definitions and `.agents` compatibility surface | `docs/research/ruflo-analysis.md` | 2026-03-23 |
| ruvnet/ruflo package.json | <https://raw.githubusercontent.com/ruvnet/ruflo/main/package.json> | MIT | Published package shape, Node requirement, CLI bin, and optional JS package ecosystem | `docs/research/ruflo-analysis.md` | 2026-03-23 |
| ruvnet/ruflo v3 docs | <https://github.com/ruvnet/ruflo/tree/main/v3> | MIT | Modular package layout, MCP-first module split, and plugin or microkernel framing | `docs/research/ruflo-analysis.md` | 2026-03-23 |
| ruvnet/ruflo LICENSE | <https://raw.githubusercontent.com/ruvnet/ruflo/main/LICENSE> | MIT | Reuse conditions for code or configuration copying and adaptation | `docs/research/ruflo-analysis.md` | 2026-03-23 |

## TASK_COMPLETE Audit-Map Advisory Worker Research (Task #954)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ruvnet/ruflo README | <https://github.com/ruvnet/ruflo> | MIT | 12 context-triggered background workers (`audit`, `map`, `testgaps`, `document`) and auto-trigger patterns for validating OwlBear worker design | `docs/research/task-complete-audit-map-advisory-worker.md` | 2026-03-24 |

## Tool-Invoked Knowledge Cancellation Research (Task #877)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| .NET CancellationTokenSource/Token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC-BY-4.0 | Token source (write-side) vs token (read-side) split; CreateLinkedTokenSource for parent/child composition; one token per cancelable operation | `docs/research/tool-invoked-cancellation.md` | 2026-03-25 |
| PydanticAI Function Tools docs | <https://ai.pydantic.dev/tools/> | MIT | FunctionToolset tool registration patterns; bound methods access self not RunContext; confirmed RunContext-free tool signatures for knowledge toolsets | `docs/research/tool-invoked-cancellation.md` | 2026-03-25 |
| Python asyncio task docs | <https://docs.python.org/3/library/asyncio-task.html> | PSF-2.0 | `create_task()` strong-reference lifecycle, `Semaphore` bounded concurrency, and cooperative cancellation patterns | `docs/research/task-complete-audit-map-advisory-worker.md` | 2026-03-24 |

## CancelSlot Validation Research (Task #1001)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| .NET CancellationTokenSource/Token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC-BY-4.0 | Write-side/read-side split pattern; CreateLinkedTokenSource composition; validated CancelSlot maps to CancellationTokenSource | `docs/research/cancel-slot-validation.md` | 2026-03-25 |
| AnyIO cancellation docs | <https://anyio.readthedocs.io/en/stable/cancellation.html> | MIT | Cooperative cancellation via cancel scopes in Python async; confirms polling `is_set()` is idiomatic for async-native code | `docs/research/cancel-slot-validation.md` | 2026-03-25 |

## Frontend Audit Prompt Design (Task #944)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable `/audit` SKILL.md | <https://github.com/pbakaus/impeccable/blob/main/source/skills/audit/SKILL.md> | Apache-2.0 | 5-dimension scored audit structure (a11y, perf, theming, responsive, anti-patterns), P0–P3 severity scheme, 0–20 health score, recommended-commands section | `docs/research/frontend-audit-prompt-design.md` | 2026-03-25 |
| pbakaus/impeccable README | <https://github.com/pbakaus/impeccable> | Apache-2.0 | `audit → normalize → polish` pipeline, scoped audit via area argument, command-chaining UX | `docs/research/frontend-audit-prompt-design.md` | 2026-03-25 |
| axe-core rule taxonomy | <https://github.com/dequelabs/axe-core> | MPL-2.0 | Impact tiers (critical/serious/moderate/minor), WCAG category grouping precedent | `docs/research/frontend-audit-prompt-design.md` | 2026-03-25 |

## Hook-Triggered Background Worker Pilot (Task #949)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ruvnet/ruflo README | <https://github.com/ruvnet/ruflo> | MIT | Background worker catalog (`audit`, `map`, `testgaps`, `document`) and daemon or hook framing used to bound the candidate pilot set | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |
| ruvnet/ruflo AGENTS.md | <https://raw.githubusercontent.com/ruvnet/ruflo/main/AGENTS.md> | MIT | Hook, task, and coordination concepts used to compare OwlBear trigger fit and advisory scope | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |
| Python asyncio task docs | <https://docs.python.org/3/library/asyncio-task.html> | PSF | Strong-reference requirement for background tasks plus timeout and cancellation guidance for supervised fire-and-forget work | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |
| Python asyncio sync docs | <https://docs.python.org/3/library/asyncio-sync.html> | PSF | `Semaphore` and `Event` semantics for bounded concurrency and cooperative shutdown of daemon workers | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |

## Hook-Triggered Background Worker Supervision (Task #953)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio task docs | <https://docs.python.org/3/library/asyncio-task.html> | PSF | `create_task()` strong-reference guidance, `TaskGroup` lifecycle, and cancellation behavior for hook-owned background work | `docs/research/hook-triggered-background-worker-supervision.md` | 2026-03-23 |
| Python asyncio sync docs | <https://docs.python.org/3/library/asyncio-sync.html> | PSF | `Semaphore` and `Event` semantics used to compare bounded hook-worker supervision options | `docs/research/hook-triggered-background-worker-supervision.md` | 2026-03-23 |
| aiohttp advanced docs | <https://docs.aiohttp.org/en/stable/web_advanced.html> | Apache-2.0 | Cleanup-time background task tracking and graceful shutdown patterns used to justify plugging hook-worker drain into OwlBear bootstrap cleanup | `docs/research/hook-triggered-background-worker-supervision.md` | 2026-03-23 |

## HookEvent Reaction Routing (Task #950)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Trigger plus action model, traced action failures, inferred targets, and notification actions used to shape a config-driven router instead of event-bus mutation | `docs/research/hookevent-reaction-routing.md` | 2026-03-23 |
| Prefect create automations guide | <https://docs.prefect.io/v3/how-to-guides/automations/creating-automations> | N/A (docs) | YAML/JSON automation schema and ordered action examples used to propose explicit OwlBear reaction rules | `docs/research/hookevent-reaction-routing.md` | 2026-03-23 |
| Celery task guide | <https://docs.celeryq.dev/en/stable/userguide/tasks.html> | BSD-3-Clause | Retry/backoff options, task handlers, and exhausted-retry behavior used to evaluate OwlBear retry reuse instead of a second retry engine | `docs/research/hookevent-reaction-routing.md` | 2026-03-23 |
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | Signal-based lifecycle observation and retry/failure hooks used to compare event-bus boundaries and non-blocking handler expectations | `docs/research/hookevent-reaction-routing.md` | 2026-03-23 |
| ruvnet/ruflo README | <https://github.com/ruvnet/ruflo> | MIT | Original hook and routing inspiration that led to task #950 and framed the event-to-action research question | `docs/research/hookevent-reaction-routing.md` | 2026-03-23 |

## HookReaction Schema and Router Wiring (Task #955)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Trigger/action structure, ordered actions, and inferred-target patterns used to justify explicit but minimal HookReaction rules | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |
| Prefect create automations guide | <https://docs.prefect.io/v3/how-to-guides/automations/creating-automations> | N/A (docs) | YAML/JSON automation examples used to compare free-form dicts versus typed rule models | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |
| Pydantic models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | Nested model behavior, concrete container guidance, and extra-field handling for the `hook_reactions` schema recommendation | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |
| Pydantic validators docs | <https://docs.pydantic.dev/latest/concepts/validators/> | MIT | Field/model validator patterns used to recommend startup-safe rule validation and shallow matcher checks | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |
| Pydantic settings docs | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/> | MIT | `env_nested_delimiter`, nested complex parsing, and partial-update behavior used to fit HookReaction rules into OwlBear settings | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | Signal/handler decoupling precedent used to keep HookRegistry observational and place routing in a separate handler | `docs/research/hookreaction-schema-router-wiring.md` | 2026-03-23 |

## Hook Reaction Retry Delegation (Task #956)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Celery task retry docs | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | BSD-3-Clause | `self.retry()` reuses task-owned counters; signals can trigger retry through the same mechanism; one retry counter per task pattern | `docs/research/hook-reaction-retry-delegation.md` | 2026-03-24 |
| Temporal Python failure detection docs | <https://docs.temporal.io/develop/python/failure-detection> | MIT | `RetryPolicy` owned by the scheduler, not the activity; retry state at orchestrator level, not executor level | `docs/research/hook-reaction-retry-delegation.md` | 2026-03-24 |
| Prefect automations triggers docs | <https://docs.prefect.io/v3/automate/events/automations-triggers> | N/A (docs) | Event-driven actions delegate to existing executors; action tracing for failure attribution | `docs/research/hook-reaction-retry-delegation.md` | 2026-03-24 |

## Voice Addon Stdio Protocol Design (Task #49)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| NDJSON spec v1.0.0 | <https://github.com/ndjson/ndjson-spec> | Free (custom) | NDJSON framing standard: one JSON object per line, UTF-8, `\n` terminated, no embedded newlines | `docs/research/voice-stdio-protocol.md` | 2026-03-26 |
| JSON Lines spec | <https://jsonlines.org/> | N/A | Complementary NDJSON spec: UTF-8, each line a valid JSON value, `\n` terminator | `docs/research/voice-stdio-protocol.md` | 2026-03-26 |
| MCP stdio transport spec | <https://modelcontextprotocol.io/specification/2025-03-26/basic/transports> | CC-BY-4.0 | Gold-standard subprocess stdio protocol: NDJSON framing, client launches subprocess, shutdown sequence | `docs/research/voice-stdio-protocol.md` | 2026-03-26 |
| MCP Python SDK stdio client | <https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/stdio.py> | MIT | Subprocess lifecycle management: spawn, stdin/stdout streams, three-phase shutdown (close stdin, terminate, kill) | `docs/research/voice-stdio-protocol.md` | 2026-03-26 |
| ACP Python SDK `examples/client.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py> | Apache-2.0 | asyncio subprocess spawn, returncode-based crash detection, terminate+wait cleanup pattern | `docs/research/voice-stdio-protocol.md` | 2026-03-26 |

## Retry Executor Wiring (Task #985)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Celery task retry docs | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | BSD-3-Clause | Centralized retry state pattern; `self.retry()` reuses task-owned counters confirming idempotent retry approach | `docs/research/retry-executor-wiring.md` | 2026-03-24 |
| Temporal Python failure detection docs | <https://docs.temporal.io/develop/python/failure-detection> | MIT | RetryPolicy at scheduler level; non-retryable errors bypass retry confirming budget-exceeded skip pattern | `docs/research/retry-executor-wiring.md` | 2026-03-24 |
| Prefect automations triggers docs | <https://docs.prefect.io/v3/automate/events/automations-triggers> | N/A (docs) | Event-driven actions delegate to existing executors via payload matching; confirms match-predicate approach for outcome filtering | `docs/research/retry-executor-wiring.md` | 2026-03-24 |

## Expose Reaction Executors via HookRegistry (Task #991)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Flask API docs — Flask.extensions | <https://flask.palletsprojects.com/en/stable/api/#flask.Flask.extensions> | BSD-3-Clause | Central app object stores extension state as a dict attribute; validates registry-attribute pattern for OwlBear HookRegistry | `docs/research/expose-reaction-executors.md` | 2026-03-24 |
| Celery Application docs — app.tasks | <https://docs.celeryq.dev/en/stable/userguide/application.html> | BSD-3-Clause | App object exposes task registry as dict attribute for late binding; confirms mutable-dict-on-registry as standard pattern | `docs/research/expose-reaction-executors.md` | 2026-03-24 |

## Budget-Exceeded Outcome Emission (Task #993)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Celery task retry docs | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | BSD-3-Clause | `dont_autoretry_for` excludes specific exception types from retry; `Task.throws` marks expected errors as non-error states | `docs/research/budget-exceeded-outcome-emission.md` | 2026-03-24 |
| Temporal Python failure detection docs | <https://docs.temporal.io/develop/python/failure-detection> | MIT | `ApplicationError(non_retryable=True)` bypasses retry; `non_retryable_error_types` in RetryPolicy distinguishes permanent from transient failures | `docs/research/budget-exceeded-outcome-emission.md` | 2026-03-24 |

## Council Protocol C Validation (Task #976)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Level 3 programmatic hand-off and agent delegation patterns; confirmed asyncio.gather sufficiency for parallel perspective agents | `docs/research/council-protocol-c-validation.md` | 2026-03-24 |
| PydanticAI graph beta parallel docs | <https://ai.pydantic.dev/graph/beta/parallel/> | MIT | Broadcasting and join patterns for formal fan-out/fan-in; evaluated as YAGNI for 2-agent council | `docs/research/council-protocol-c-validation.md` | 2026-03-24 |

## Frontend-Normalize Prompt Research (Task #945)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable `/normalize` skill | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Plan/Execute/Clean Up structure, 8 normalization dimensions, never-list guardrails, mandatory design-context preparation | `docs/research/frontend-normalize-prompt.md` | 2026-03-24 |
| Impeccable website | <https://impeccable.style> | N/A | Public audit/normalize/polish pipeline, normalize usage examples, command taxonomy | `docs/research/frontend-normalize-prompt.md` | 2026-03-24 |
| VS Code prompt file docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | `.prompt.md` frontmatter schema, `${input:}` syntax, Markdown link file references, tool list priority | `docs/research/frontend-normalize-prompt.md` | 2026-03-24 |

## question_pending Default Hook Surface (Task #962)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Prefect events docs | <https://docs.prefect.io/v3/concepts/events> | N/A (docs) | Observed-event model and matching-event trigger behavior used to justify keeping defaults aligned to real emitters | `docs/research/question-pending-default-hook-surface.md` | 2026-03-23 |
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Trigger/action model for notification automations, used to compare live events versus speculative config surfaces | `docs/research/question-pending-default-hook-surface.md` | 2026-03-23 |
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | Concrete dispatched-signal model used to prefer live signal inventories over dead defaults | `docs/research/question-pending-default-hook-surface.md` | 2026-03-23 |
| GitHub Actions events docs | <https://docs.github.com/en/actions/reference/events-that-trigger-workflows> | N/A (docs) | Supported trigger and activity tables, plus unsupported-event notes, used to justify removing dead default event names from user-facing surfaces | `docs/research/question-pending-default-hook-surface.md` | 2026-03-23 |

## Dispatched Agent Runtime Context (Task #951)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI instructions docs | <https://ai.pydantic.dev/agents/#instructions> | MIT | Static vs dynamic vs runtime instructions, plus append order for per-run context injection | `docs/research/dispatched-agent-runtime-context.md` | 2026-03-23 |
| PydanticAI Agent API | <https://ai.pydantic.dev/api/agent/> | MIT | Per-run `instructions` and `metadata` kwargs used to separate LLM-visible context from observability context | `docs/research/dispatched-agent-runtime-context.md` | 2026-03-23 |
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Delegation patterns and shared deps or usage flow relevant to child-agent dispatch | `docs/research/dispatched-agent-runtime-context.md` | 2026-03-23 |
| ruvnet/ruflo AGENTS.md | <https://raw.githubusercontent.com/ruvnet/ruflo/main/AGENTS.md> | MIT | Layered coordination context and runtime prompt surfaces that motivated task #951 | `docs/research/dispatched-agent-runtime-context.md` | 2026-03-23 |

## BearClaw Board Command Research (Task #905)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README / command docs | <https://github.com/antopolskiy/kanban-md> | MIT | `board`, `list --json`, `log --json`, `assignee`, `claimed_by`, and global output flags for scripting a board view | `docs/research/bearclaw-board-command.md` | 2026-03-21 |
| Rich Tables docs | <https://rich.readthedocs.io/en/stable/tables.html> | MIT | Table sections, column configuration, and empty-table handling for a grouped terminal board | `docs/research/bearclaw-board-command.md` | 2026-03-21 |
| Typer Commands docs | <https://typer.tiangolo.com/tutorial/commands/> | MIT | Dedicated command registration conventions for a `board` command module | `docs/research/bearclaw-board-command.md` | 2026-03-21 |
| Typer Testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | `CliRunner` invocation and output assertions for command tests | `docs/research/bearclaw-board-command.md` | 2026-03-21 |

## Design-Context Onboarding Prompt Research (Task #943)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Impeccable repo (`/teach-impeccable` pattern) | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Scan-first, ask-only-missing, persist-to-file onboarding flow studied indirectly via parent research #930 | `docs/research/design-context-onboarding-prompt.md` | 2026-03-24 |
| VS Code Prompt Files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | Frontmatter format, file references via relative paths, `${input:}` syntax, and prompt invocation behavior | `docs/research/design-context-onboarding-prompt.md` | 2026-03-24 |
| VS Code Customization Overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Prompt files for repeatable tasks confirmed; skills for reusable knowledge; agents for persistent personas | `docs/research/design-context-onboarding-prompt.md` | 2026-03-24 |

## BearClaw Board Implementation Gate (Task #910)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README / command docs | <https://github.com/antopolskiy/kanban-md> | MIT | `list --json`, `log --action move --json`, board auto-discovery, and config semantics for the implementation seam | `docs/research/bearclaw-board-command-implementation-gate.md` | 2026-03-21 |
| Rich Tables docs | <https://rich.readthedocs.io/en/stable/tables.html> | MIT | Table sections, column styling, and explicit empty-table behavior for grouped board output | `docs/research/bearclaw-board-command-implementation-gate.md` | 2026-03-21 |
| Typer Add Typer docs | <https://typer.tiangolo.com/tutorial/subcommands/add-typer/> | MIT | `app.add_typer()` composition for wiring a dedicated board command module into the root CLI | `docs/research/bearclaw-board-command-implementation-gate.md` | 2026-03-21 |
| Python `datetime` docs | <https://docs.python.org/3/library/datetime.html> | PSF | `datetime.fromisoformat()` support for ISO 8601 timestamps with UTC offsets from kanban JSON and move logs | `docs/research/bearclaw-board-command-implementation-gate.md` | 2026-03-21 |

## BearClaw Board Failure-Handling Gate (Task #920)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `subprocess` docs | <https://docs.python.org/3/library/subprocess.html> | PSF | `run(..., check=False, capture_output=True, text=True)` behavior plus `OSError` and return-code handling for missing executables and child failures | `docs/research/bearclaw-board-command-failure-handling.md` | 2026-03-21 |
| Python `json` docs | <https://docs.python.org/3/library/json.html> | PSF | `JSONDecodeError` failure semantics and parse-location details for malformed JSON payloads | `docs/research/bearclaw-board-command-failure-handling.md` | 2026-03-21 |
| Click exception handling docs | <https://click.palletsprojects.com/en/stable/exceptions/> | BSD-3-Clause | stderr rendering and exit-code behavior for user-facing CLI failures | `docs/research/bearclaw-board-command-failure-handling.md` | 2026-03-21 |
| Typer exceptions docs | <https://typer.tiangolo.com/tutorial/exceptions/> | MIT | behavior of uncaught exceptions and Rich traceback output in Typer apps | `docs/research/bearclaw-board-command-failure-handling.md` | 2026-03-21 |

## BearClaw Board Failure-Test RED Gate (Task #924)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `subprocess` docs | <https://docs.python.org/3/library/subprocess.html> | PSF | Missing-executable `OSError`, `run(..., check=False, capture_output=True, text=True)`, and return-code handling for staged CLI failure tests | `docs/research/bearclaw-board-command-failure-tests-red-gate.md` | 2026-03-21 |
| Python `json` docs | <https://docs.python.org/3/library/json.html> | PSF | `JSONDecodeError` semantics for malformed task-list and move-log payload assertions | `docs/research/bearclaw-board-command-failure-tests-red-gate.md` | 2026-03-21 |
| Typer Testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | `CliRunner` invocation plus stdout or stderr assertions for command-level RED tests | `docs/research/bearclaw-board-command-failure-tests-red-gate.md` | 2026-03-21 |
| Click exception handling docs | <https://click.palletsprojects.com/en/stable/exceptions/> | BSD-3-Clause | stderr rendering and exit-code behavior that the RED tests should preserve through `_cli_error` | `docs/research/bearclaw-board-command-failure-tests-red-gate.md` | 2026-03-21 |
| Typer exceptions docs | <https://typer.tiangolo.com/tutorial/exceptions/> | MIT | Uncaught exception behavior and Rich traceback output as the failure mode to avoid for routine board CLI errors | `docs/research/bearclaw-board-command-failure-tests-red-gate.md` | 2026-03-21 |

## BearClaw Board Kanban JSON Fixture Helpers (Task #923)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest fixtures reference | <https://docs.pytest.org/en/stable/reference/fixtures.html> | MIT | `conftest.py` fixture availability across multiple files and why a board-only helper should not become a global test helper yet | `docs/research/bearclaw-board-kanban-json-fixtures.md` | 2026-03-22 |
| pytest how-to fixtures | <https://docs.pytest.org/en/stable/how-to/fixtures.html> | MIT | factory-style fixture and helper patterns for reusable test arrangement data | `docs/research/bearclaw-board-kanban-json-fixtures.md` | 2026-03-22 |
| Python `json` docs | <https://docs.python.org/3/library/json.html> | PSF | `json.dumps()` semantics for generating paired task-list and move-log JSON payload strings from Python structures | `docs/research/bearclaw-board-kanban-json-fixtures.md` | 2026-03-22 |
| Typer Testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | keeping board assertions at the `CliRunner` boundary while refactoring only test-arrangement helpers | `docs/research/bearclaw-board-kanban-json-fixtures.md` | 2026-03-22 |

## BearClaw Board Age-Threshold Styling (Task #921)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README / config docs | <https://github.com/antopolskiy/kanban-md> | MIT | `tui.age_thresholds` as the supported TUI age color threshold config seam | `docs/research/bearclaw-board-age-threshold-styling.md` | 2026-03-21 |
| Rich Tables docs | <https://rich.readthedocs.io/en/stable/tables.html> | MIT | `Table.add_row()` renderables, column-vs-row styling scope, and section behavior for grouped output | `docs/research/bearclaw-board-age-threshold-styling.md` | 2026-03-21 |
| Rich Style docs | <https://rich.readthedocs.io/en/stable/style.html> | MIT | `color(<number>)` numeric color syntax and `Style.parse()` validation for config-driven styles | `docs/research/bearclaw-board-age-threshold-styling.md` | 2026-03-21 |
| PyYAML docs | <https://pyyaml.org/wiki/PyYAMLDocumentation> | MIT | `safe_load()` and `YAMLError` behavior for defensive YAML config parsing | `docs/research/bearclaw-board-age-threshold-styling.md` | 2026-03-21 |

## BearClaw Board Age-Threshold Styling RED Gate (Task #925)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README / config docs | <https://github.com/antopolskiy/kanban-md> | MIT | `tui.age_thresholds` config semantics and the live threshold shape the RED tests need to simulate | `docs/research/bearclaw-board-age-threshold-styling-red-gate.md` | 2026-03-21 |
| Rich Console docs | <https://rich.readthedocs.io/en/stable/console.html> | MIT | Non-terminal ANSI stripping plus `FORCE_COLOR`, `TTY_COMPATIBLE`, and `TTY_INTERACTIVE` for test-visible style output | `docs/research/bearclaw-board-age-threshold-styling-red-gate.md` | 2026-03-21 |
| Rich Style docs | <https://rich.readthedocs.io/en/stable/style.html> | MIT | `color(<number>)` numeric palette syntax and the normalized style effect the RED tests should assert | `docs/research/bearclaw-board-age-threshold-styling-red-gate.md` | 2026-03-21 |
| Typer Testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | `CliRunner.invoke()` boundary testing and output assertions for CLI RED tests | `docs/research/bearclaw-board-age-threshold-styling-red-gate.md` | 2026-03-21 |

## BearClaw Board RED Test Gate (Task #909)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README / command docs | <https://github.com/antopolskiy/kanban-md> | MIT | `list --json`, `log --json`, `--action move`, and output flags for the mocked board-command test seam | `docs/research/bearclaw-board-command-red-gate.md` | 2026-03-21 |
| Rich Tables docs | <https://rich.readthedocs.io/en/stable/tables.html> | MIT | Stable table assertions, sections, and empty-table fallback guidance for CLI tests | `docs/research/bearclaw-board-command-red-gate.md` | 2026-03-21 |
| Typer Testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | `CliRunner` invocation and output assertions for RED-phase command tests | `docs/research/bearclaw-board-command-red-gate.md` | 2026-03-21 |
| Typer Add Typer docs | <https://typer.tiangolo.com/tutorial/subcommands/add-typer/> | MIT | Typer app composition and command exposure through `add_typer()` | `docs/research/bearclaw-board-command-red-gate.md` | 2026-03-21 |

## EntityExtractor Gleaning Benchmark Research (Task #891)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | Apache-2.0 | Optional glean step, 15-25% recall claim, and benchmark-first algorithm outline | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | MIT | `extract_graph.max_gleanings` and `extract_claims.max_gleanings`, plus model metrics hooks as prior art for multi-pass extraction and cost visibility | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | Text-unit provenance and merge-by-title or type extraction flow | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |
| Microsoft GraphRAG manual prompt tuning docs | <https://microsoft.github.io/graphrag/prompt_tuning/manual_prompt_tuning/> | MIT | Extraction prompt as a separable tuning seam for a default-off prototype | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |
| scikit-learn `recall_score` docs | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | BSD-3-Clause | Recall definition and averaging choices for gold-vs-pred entity evaluation | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | MIT | Gold annotation scoring conventions and per-type PRF framing | `docs/research/entity-extractor-gleaning-benchmark.md` | 2026-03-21 |

## EntityExtractor Recall Harness Research (Task #906)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| scikit-learn `recall_score` docs | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | BSD-3-Clause | Exact recall definition plus `micro`, `macro`, and per-label reporting options to mirror in a custom scorer | `docs/research/entity-extractor-code-corpus-recall-harness.md` | 2026-03-21 |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | MIT | `ents_r` and `ents_per_type` conventions as prior art for overall and per-type entity reporting | `docs/research/entity-extractor-code-corpus-recall-harness.md` | 2026-03-21 |
| pytest marker docs | <https://docs.pytest.org/en/stable/example/markers.html> | MIT | Registered custom markers and `-m` selection for opt-in benchmark execution | `docs/research/entity-extractor-code-corpus-recall-harness.md` | 2026-03-21 |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | TextUnit provenance and merge-by-title-and-type extraction semantics for stable gold-key design | `docs/research/entity-extractor-code-corpus-recall-harness.md` | 2026-03-21 |

## EntityExtractor Benchmark Corpus Research (Task #911)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG inputs docs | <https://microsoft.github.io/graphrag/index/inputs/> | MIT | Stable document ids, JSON or text input schema, and metadata carriage as prior art for checked-in corpus records | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | TextUnit provenance and merge-by-title-and-type semantics for stable gold entity identity | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |
| spaCy data formats docs | <https://spacy.io/api/data-formats> | MIT | Text-plus-annotation corpus structures for checked-in evaluation data | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | MIT | Exact-match and per-type evaluation conventions for entity scoring | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |
| PydanticAI testing docs | <https://ai.pydantic.dev/testing/> | MIT | `TestModel`, `FunctionModel`, and `ALLOW_MODEL_REQUESTS=False` as prior art for model-free tests | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |
| pytest marker docs | <https://docs.pytest.org/en/stable/example/markers.html> | MIT | Registered markers and `-m` selection for keeping live benchmark execution opt-in | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | 2026-03-21 |

## EntityExtractor Gleaning Prototype Research (Task #907)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | MIT | `extract_graph.max_gleanings`, optional glean cycles, and model metrics hooks as prior art for a default-off multi-pass seam with benchmark-visible cost data | `docs/research/entity-extractor-gleaning-prototype.md` | 2026-03-21 |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | Merge-by-title-and-type graph extraction semantics and post-extraction consolidation behavior for stable dedup keys | `docs/research/entity-extractor-gleaning-prototype.md` | 2026-03-21 |
| Microsoft GraphRAG manual prompt tuning docs | <https://microsoft.github.io/graphrag/prompt_tuning/manual_prompt_tuning/> | MIT | Extraction prompts as overrideable seams, supporting a dedicated missed-entities follow-up prompt | `docs/research/entity-extractor-gleaning-prototype.md` | 2026-03-21 |
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | Apache-2.0 | Optional glean stage, 15-25% recall claim, and normalization after gleaning as prior art for a two-pass benchmark prototype | `docs/research/entity-extractor-gleaning-prototype.md` | 2026-03-21 |

## EntityExtractor Gleaning Evaluation Research (Task #908)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | Apache-2.0 | Optional glean step and benchmark-driven rollout posture for multi-pass extraction | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | MIT | `max_gleanings` as a configurable extraction knob instead of a forced default | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |
| scikit-learn `recall_score` docs | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | BSD-3-Clause | Micro recall and per-label recall definitions for the benchmark gate | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | MIT | Per-type PRF reporting conventions for extraction evaluation | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |
| PydanticAI agents docs | <https://ai.pydantic.dev/agents/> | MIT | Run-result usage access for token and request accounting | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |
| Python `time` docs | <https://docs.python.org/3/library/time.html> | PSF | `time.perf_counter()` guidance for high-resolution elapsed-time measurement | `docs/research/entity-extractor-gleaning-evaluation-plan.md` | 2026-03-21 |

## Planner Temp Task Hygiene (Task #855)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields and validation in structured issue forms; precedent for rejecting underspecified work items at intake | `docs/research/planner-temp-task-hygiene.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | Disabling blank issues and steering contributors into templates/forms instead of free-form placeholders | `docs/research/planner-temp-task-hygiene.md` | 2026-03-21 |

## Planner Placeholder Guardrails (Task #899)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields, defaults, and validation as intake-time controls against placeholder work items | `docs/research/planner-placeholder-guardrails.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | `blank_issues_enabled: false` as prior art for refusing blank work items before they enter the queue | `docs/research/planner-placeholder-guardrails.md` | 2026-03-21 |
| Atlassian Support - Configure advanced work item workflows | <https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/> | N/A (docs) | Validators block invalid transition input before work items advance; precedent for stop/refine behavior instead of downstream cleanup | `docs/research/planner-placeholder-guardrails.md` | 2026-03-21 |

## Placeholder Task Rejection Guidance (Task #900)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields and field-level validation in issue forms; precedent for refusing underspecified work items instead of inferring missing scope | `docs/research/placeholder-task-rejection-guidance.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | `blank_issues_enabled: false` and structured template chooser configuration; precedent for disabling blank intake paths | `docs/research/placeholder-task-rejection-guidance.md` | 2026-03-21 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/user/project/description_templates/> | CC-BY-SA-4.0 | Standardized issue and work-item description templates; precedent for requiring scoped bodies instead of empty placeholders | `docs/research/placeholder-task-rejection-guidance.md` | 2026-03-21 |

## Architect Placeholder Rejection Rules (Task #902)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields and validations in structured issue forms; prior art for refusing underspecified work items instead of refining invented scope | `docs/research/architect-placeholder-task-rejection-rules.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | `blank_issues_enabled: false` as explicit prior art for disabling blank intake paths | `docs/research/architect-placeholder-task-rejection-rules.md` | 2026-03-21 |
| Atlassian Support - Configure advanced work item workflows | <https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/> | N/A (docs) | Validators check transition input before the transition is performed and failed validators stop the work item from progressing | `docs/research/architect-placeholder-task-rejection-rules.md` | 2026-03-21 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/user/project/description_templates/> | CC-BY-SA-4.0 | Description templates and defaults as prior art for requiring scoped work-item bodies instead of empty placeholders | `docs/research/architect-placeholder-task-rejection-rules.md` | 2026-03-21 |

## Planner Agent Placeholder Rejection Rules (Task #903)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields and validation as intake-time controls; prior art for treating placeholder titles and blank bodies as invalid input | `docs/research/planner-agent-placeholder-rejection-rules.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | `blank_issues_enabled: false` as prior art for refusing blank intake paths instead of letting placeholders through | `docs/research/planner-agent-placeholder-rejection-rules.md` | 2026-03-21 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/user/project/description_templates/> | CC-BY-SA-4.0 | Standardized scoped work-item descriptions through reusable templates and defaults rather than empty bodies | `docs/research/planner-agent-placeholder-rejection-rules.md` | 2026-03-21 |

## Researcher Placeholder-Task Rejection Rules (Task #901)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | N/A (docs) | Required fields and validations as prior art for rejecting placeholder or underspecified work before research begins | `docs/research/researcher-placeholder-task-rejection-rules.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates for your repository | <https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | N/A (docs) | `blank_issues_enabled: false` as precedent for refusing blank intake paths instead of clarifying them downstream | `docs/research/researcher-placeholder-task-rejection-rules.md` | 2026-03-21 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/user/project/description_templates/> | CC-BY-SA-4.0 | Standardized scoped work-item descriptions and defaults rather than empty task bodies | `docs/research/researcher-placeholder-task-rejection-rules.md` | 2026-03-21 |
| Atlassian Support - Configure advanced work item workflows | <https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/> | N/A (docs) | Workflow validators as prior art for blocking invalid transition input before a work item advances | `docs/research/researcher-placeholder-task-rejection-rules.md` | 2026-03-21 |

## Core Re-export Removal Research (Task #812)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Google Python Style Guide §2.2 | <https://google.github.io/styleguide/pyguide.html#22-imports> | CC-BY-4.0 | Import conventions: favors `from x.y import z` over package-level re-exports for applications | `docs/research/core-init-reexport-removal.md` | 2026-03-15 |
| PEP 8 — Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | PSF | `__all__` defines public API surface; unmentioned names are implementation details | `docs/research/core-init-reexport-removal.md` | 2026-03-15 |

## PydanticAI Re-export Compatibility Validation (Task #813)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI v1.63.0 source (installed) | <https://github.com/pydantic/pydantic-ai> | MIT | Agent.__init__, AbstractToolset, FunctionToolset — no import scanning, no __init_subclass__ registry, all tool discovery is explicit | `docs/research/pydanticai-re-export-compat.md` | 2026-03-15 |
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | CC-BY-4.0 | Agent construction, toolset registration, dependency injection — all explicit parameters | `docs/research/pydanticai-re-export-compat.md` | 2026-03-15 |
| PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | CC-BY-4.0 | FunctionToolset, WrapperToolset, AbstractToolset — no package scanning, explicit registration only | `docs/research/pydanticai-re-export-compat.md` | 2026-03-15 |

## ColBERT Scalar Quantization Research (Task #434)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Qdrant late-interaction article | <https://qdrant.tech/articles/late-interaction-models/> | Apache-2.0 | Multivector uint8 quantization benchmarks: SciFact/NFCorpus nDCG@10 (<1% delta) | `docs/research/colbert-scalar-quantization.md` | 2026-03-13 |
| Qdrant scalar quantization article | <https://qdrant.tech/articles/scalar-quantization/> | Apache-2.0 | SQ theory, Arxiv/Gist recall benchmarks, oversampling+rescore patterns | `docs/research/colbert-scalar-quantization.md` | 2026-03-13 |
| Qdrant quantization guide | <https://qdrant.tech/documentation/guides/quantization/> | Apache-2.0 | ScalarQuantization API, per-vector config, rescore/oversampling params | `docs/research/colbert-scalar-quantization.md` | 2026-03-13 |
| Qdrant collections docs | <https://qdrant.tech/documentation/concepts/collections/> | Apache-2.0 | Per-vector quantization_config confirmation (v1.1.1+) | `docs/research/colbert-scalar-quantization.md` | 2026-03-13 |

## SkillRegistry Glob Fix Research (Task #780)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python 3.12 pathlib.Path.glob() docs | <https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.glob> | PSF | `glob("*/SKILL.md")` matches one-level subdirs; `**` recurses. Confirmed pattern semantics for fix. | `docs/research/skillregistry-glob-fix.md` | 2026-03-13 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Canonical convention: each skill in own subdir with `SKILL.md`; `name` must match parent dir | `docs/research/skillregistry-glob-fix.md` | 2026-03-13 |

## Retro Skill Research (Task #786)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| garrytan/gstack retro v2.0 | <https://github.com/garrytan/gstack/blob/main/retro/SKILL.md> | MIT | 14-step retro workflow: git metrics, 45min session detection, per-contributor breakdown, streak tracking, compare mode, conventional commit categorization | `docs/research/retro-skill.md` | 2026-03-13 |
| IonicaBizau/git-stats v3.5 | <https://github.com/IonicaBizau/git-stats> | MIT | GitHub-like contribution calendars, per-author additions/deletions stats, date-range filtering, Node.js CLI for local git statistics | `docs/research/retro-skill.md` | 2026-03-13 |

## Error and Rescue Map Research (Task #785)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| gstack plan-eng-review SKILL.md | <https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md> | MIT | "Failure modes" required output: per-codepath failure scenario + test coverage + error handling + user impact; architecture review failure scenario requirement | `docs/research/error-rescue-map.md` | 2026-03-13 |
| FMEA (Wikipedia / MIL-STD-1629A) | <https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis> | CC-BY-SA-4.0 | Industry-standard failure analysis: Item → Failure Mode → Cause → Effect → Severity → Probability → Detection → Risk Level. Software FMEA variant with existence/controls/detectability | `docs/research/error-rescue-map.md` | 2026-03-13 |

## Two-Pass Review Checklist Research (Task #784)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Google Engineering Practices — Code Review Standard | <https://google.github.io/eng-practices/review/reviewer/standard.html> | CC-BY-3.0 | "Nit:" prefix convention for non-blocking review comments; reviewer should not block progress on polish | `docs/research/two-pass-review-checklist.md` | 2026-03-13 |
| Conventional Comments | <https://conventionalcomments.org/> | CC-BY-3.0 | Label taxonomy (issue/suggestion/nitpick) with blocking/non-blocking decorations for structured review feedback | `docs/research/two-pass-review-checklist.md` | 2026-03-13 |

## gstack Agent Patterns (Task #783)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| garrytan/gstack v1.1.0 | <https://github.com/garrytan/gstack> | MIT | 8 Claude Code skills: two-pass review checklist with suppressions, Error & Rescue Map failure analysis template, retro/metrics skill, structured question protocol, scope modes, QA health scoring | `docs/research/gstack-agent-patterns.md` | 2026-03-13 |

## Knowledge-ops SKILL.md Research (Task #774)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex Tools docs | <https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/> | MIT | "Tool selection relies strongly on tool name and description" — validates investment in SKILL.md guidance | `docs/research/knowledge-ops-skill.md` | 2026-03-13 |
| PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | MIT | FunctionToolset pattern, progressive disclosure via toolset composition | `docs/research/knowledge-ops-skill.md` | 2026-03-13 |

## ContextInjectionHook Dead Code Analysis (Task #772)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI — Instructions (runtime) | <https://ai.pydantic.dev/agents/#instructions> | MIT | Runtime `instructions=` parameter behavior — appended to static + dynamic instructions | `docs/research/context-injection-hook-dead-code.md` | 2026-03-13 |

## BoardContextProvider Implementation (Task #770)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| cachetools TTLCache docs | <https://cachetools.readthedocs.io/en/latest/> | MIT | TTL caching patterns, `TTLCache` with `time.monotonic()` timer; decided against as dependency for single-value cache (YAGNI) | `docs/research/board-context-provider.md` | 2026-03-13 |
| Python `time.monotonic()` docs | <https://docs.python.org/3/library/time.html#time.monotonic> | PSF | Monotonic clock for TTL computation — cannot go backwards, unaffected by system clock updates | `docs/research/board-context-provider.md` | 2026-03-13 |

## Botasaurus Feature Evaluation (Task #748)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| omkarcloud/botasaurus v4.0.97 | <https://github.com/omkarcloud/botasaurus> | MIT | Anti-detection patterns, human cursor (Bezier curves), decorator-based config, two-layer caching, tiny cookie profiles, proxy rotation, parallel execution | `docs/research/botasaurus.md` | 2026-03-12 |

## Paperclip AI Orchestration (Task #746)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| paperclipai/paperclip | <https://github.com/paperclipai/paperclip> | MIT | Heartbeat protocol, budget enforcement model, blocked-task dedup, adapter architecture, PARA memory, org chart hierarchy, cost API, approval workflow | `docs/research/paperclip.md` | 2026-03-12 |

## Olanetsoft Workflow Patterns (Task #747)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Olanetsoft AI agent workflow gist | <https://gist.githubusercontent.com/Olanetsoft/5931f1861d2ee9bcefb16774ff21e41e/raw/e4231969f53af71ffaeb4bb61fa7cfa13317f1a6/workflow.md> | Unknown | 6 workflow orchestration patterns (plan node, subagent strategy, self-improvement loop, verification, elegance, autonomous bug fixing) + task management + core principles | `docs/research/olanetsoft-workflow.md` | 2026-03-12 |

## Orchestration & Agent Frameworks Epic (Task #580)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Agent delegation, programmatic hand-off, deep agents, graphs | `docs/research/orchestration-agent-frameworks.md` | 2026-03-07 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | LLM-based speaker selection, candidate functions, user feedback | `docs/research/orchestration-agent-frameworks.md` | 2026-03-07 |
| CrewAI Crews docs | <https://docs.crewai.com/concepts/crews> | Apache-2.0 | Sequential/hierarchical process, memory, crew output, streaming | `docs/research/orchestration-agent-frameworks.md` | 2026-03-07 |

## Visuals, Diagrams & MCP Integrations (Task #582)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| hustcc/mcp-mermaid | <https://github.com/hustcc/mcp-mermaid> | MIT | MCP Mermaid rendering patterns, output format options | `docs/research/visuals-diagrams-mcp.md` | 2026-03-07 |
| antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | MIT | Python MCP server, Kroki fallback strategy, diagram type support | `docs/research/visuals-diagrams-mcp.md` | 2026-03-07 |
| Kroki.io | <https://kroki.io/> | MIT | Unified diagram rendering API, supported types/formats | `docs/research/visuals-diagrams-mcp.md` | 2026-03-07 |
| peng-shawn/mermaid-mcp-server | <https://github.com/peng-shawn/mermaid-mcp-server> | MIT | Puppeteer-based Mermaid rendering, file save patterns | `docs/research/visuals-diagrams-mcp.md` | 2026-03-07 |
| excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | MIT | MCP Apps extension, cheat-sheet tool pattern | `docs/research/excalidraw-mcp.md` | 2026-03-07 |
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | 26-tool programmatic canvas, element CRUD, WebSocket sync | `docs/research/visuals-diagrams-mcp.md` | 2026-03-07 |

## Visual Output Skill (Task #706)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer v0.6.3 | <https://github.com/nicobailon/visual-explainer> | MIT | Workflow phases (think/structure/style/deliver), Mermaid routing table, aesthetic constraints, anti-slop guards | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |
| Anthropic Agent Skills spec | <https://agentskills.io> | Apache-2.0 | SKILL.md format standard (YAML frontmatter + markdown instructions) | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |

## HTML Diagram Templates (Task #708)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer templates/ | <https://github.com/nicobailon/visual-explainer/tree/main/plugins/visual-explainer/templates> | MIT | 3 reference HTML templates: architecture (CSS Grid cards, depth tiers), data-table (HTML table, KPI cards, status badges), mermaid-flowchart (Mermaid CDN, zoom/pan JS) | `.github/skills/visual-output/templates/` | 2026-03-10 |
| nicobailon/visual-explainer css-patterns.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/references/css-patterns.md> | MIT | CSS reference patterns: theme setup, card components, depth tiers, grid layouts, Mermaid containers, animations, overflow protection | `docs/research/html-diagram-templates.md` | 2026-03-10 |

## BearClaw Decision Commands (Task #767)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| python-frontmatter 1.1.0 | <https://github.com/eyeseast/python-frontmatter> | MIT | YAML frontmatter parse/dump API, compared against manual yaml.safe_load (decided: manual) | `docs/research/bearclaw-decision-commands.md` | 2026-03-13 |

## BearClaw Decision Tests Research (Task #778)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | CliRunner `input=` for interactive prompt testing | `docs/research/bearclaw-decision-tests.md` | 2026-03-13 |
| Rich Prompt docs | <https://rich.readthedocs.io/en/stable/prompt.html> | MIT | Prompt.ask Console.input() stdin behavior — findings: incompatible with CliRunner stdin redirect | `docs/research/bearclaw-decision-tests.md` | 2026-03-13 |
| Typer prompt tutorial | <https://typer.tiangolo.com/tutorial/prompt/> | MIT | `typer.prompt()`, `typer.confirm()`, Rich Prompt integration patterns | `docs/research/bearclaw-decision-commands.md` | 2026-03-13 |
| Rich prompt module | <https://rich.readthedocs.io/en/stable/prompt.html> | MIT | `Prompt.ask(choices=...)`, `Confirm.ask()` for interactive CLI flows | `docs/research/bearclaw-decision-commands.md` | 2026-03-13 |

## Cheat-Sheet Tool Pattern (Task #718)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | MIT | `read_me` companion tool pattern for pre-loading domain context | `docs/research/cheat-sheet-tool.md` | 2026-03-13 |
| DougTrajano/pydantic-ai-skills | <https://github.com/DougTrajano/pydantic-ai-skills> | MIT | Progressive disclosure with `list_skills`/`load_skill` tools for PydanticAI | `docs/research/cheat-sheet-tool.md` | 2026-03-13 |
| Agent Skills spec | <https://agentskills.io> | Apache-2.0 | Open standard for on-demand skill loading in agents | `docs/research/cheat-sheet-tool.md` | 2026-03-13 |
| PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | MIT | PreparedToolset, dynamic tool definitions, composition patterns | `docs/research/cheat-sheet-tool.md` | 2026-03-13 |

## Project-Recap Visual Command (Task #709)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer — project-recap.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/commands/project-recap.md> | MIT | 8-section project recap HTML structure, data gathering pattern | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |
| Aider-AI/aider — RepoMap | <https://github.com/Aider-AI/aider/blob/main/aider/repomap.py> | Apache-2.0 | Repo overview concept validation (tree-sitter + PageRank codebase map) | `docs/research/project-recap-command.md` | 2026-03-10 |
| VS Code prompt files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | .prompt.md format specification (frontmatter, variables, tool lists) | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |

## Session Hook Emission (Task #711)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK — Lifecycle | <https://openai.github.io/openai-agents-python/ref/lifecycle/> | MIT | `on_agent_start`/`on_agent_end` hooks pattern, payload design | `docs/research/session-hook-emission.md` | 2026-03-09 |
| PydanticAI — Agents docs | <https://ai.pydantic.dev/agents/> | MIT | Agent run lifecycle, event streaming (no built-in session hooks) | `docs/research/session-hook-emission.md` | 2026-03-09 |

## Accessibility-Tree Snapshot (Task #726)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| browser-use `DomService` | <https://github.com/browser-use/browser-use> | MIT | CDP `Accessibility.getFullAXTree` approach, AX node flattening, session lifecycle (create/detach per call) | `src/owlbear/tools/browser/manager.py` | 2026-03-11 |

## Excalidraw Diagram Skill (Task #628)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Compact Board-State Context Injection (Task #744)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Mission Control `generate-context.ts` | <https://github.com/MeisnerDan/mission-control/blob/main/mission-control/scripts/generate-context.ts> | MIT | Token-optimized workspace snapshot (~650 tokens), section structure (projects, inbox, kanban pipeline, in-progress detail, agent workload, quick stats) | `docs/research/compact-board-context.md` | 2026-03-13 |
| PydanticAI Instructions docs | <https://ai.pydantic.dev/agents/#instructions> | MIT | Runtime `instructions=` parameter semantics: appends to agent instructions, reevaluated per run, not accumulated from history | `docs/research/compact-board-context.md` | 2026-03-13 |
| Claude Code Memory docs | <https://code.claude.com/docs/en/memory> | — | CLAUDE.md context injection patterns, 200-line limit, topic file organization | `docs/research/compact-board-context.md` | 2026-03-13 |
| coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | MIT | Excalidraw JSON generation methodology, element library, color palette, layout patterns — compressed from ~450 to ~150 lines | `.github/skills/excalidraw-diagram/` | 2026-03-11 |

## ExcalidrawRenderService Research Update (Task #629)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| coleam00/excalidraw-diagram-skill render pipeline | <https://github.com/coleam00/excalidraw-diagram-skill> | MIT | render_excalidraw.py + render_template.html: Playwright + esm.sh exportToSvg → screenshot pattern | `docs/research/excalidraw-render-update.md` | 2026-03-12 |
| Kroki #1742 font bug | <https://github.com/yuzutech/kroki/issues/1742> | MIT | Excalidraw font rendering broken on kroki.io free tier (upstream VITE_PKG_VERSION mismatch) | `docs/research/excalidraw-render-update.md` | 2026-03-12 |
| @excalidraw/utils (npm) | <https://www.npmjs.com/package/@excalidraw/utils> | MIT | Standalone exportToSvg/exportToBlob without React dependency | `docs/research/excalidraw-render-update.md` | 2026-03-12 |

## Consolidate trafilatura Extras (Task #569)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python Packaging Guide â€” pyproject.toml | <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/> | CC-BY-SA-4.0 | Optional-dependencies syntax, extras best practices | `docs/research/consolidate-trafilatura-extras.md` | 2026-03-07 |
| uv docs â€” optional dependencies | <https://docs.astral.sh/uv/concepts/projects/dependencies/#optional-dependencies> | MIT | uv extras handling, self-referencing extras support | `docs/research/consolidate-trafilatura-extras.md` | 2026-03-07 |
| httpx pyproject.toml | <https://github.com/encode/httpx/blob/master/pyproject.toml> | BSD-3-Clause | Flat, self-contained extras pattern (prior art) | `docs/research/consolidate-trafilatura-extras.md` | 2026-03-07 |

## DAEMON_STARTUP Hook Event (Task #624)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| FastAPI lifespan events | <https://fastapi.tiangolo.com/advanced/events/> | MIT | Startup/shutdown event patterns, `on_event("startup")`, lifespan context manager | `docs/research/daemon-startup-hook.md` | 2026-03-07 |
| Starlette lifespan | <https://starlette.dev/lifespan/> | BSD-3-Clause | Lifespan async context manager, fire-before-serve pattern, state sharing | `docs/research/daemon-startup-hook.md` | 2026-03-07 |
| Django signals reference | <https://docs.djangoproject.com/en/5.0/ref/signals/> | BSD-3-Clause | Signal patterns (request_started, pre/post_migrate), no process-level startup signal | `docs/research/daemon-startup-hook.md` | 2026-03-07 |
| pydantic pyproject.toml | <https://github.com/pydantic/pydantic/blob/main/pyproject.toml> | MIT | Extras vs dependency-groups patterns (prior art) | `docs/research/consolidate-trafilatura-extras.md` | 2026-03-07 |

## Rigor Profiles (Task #618)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave `/nw:rigor` command | <https://github.com/nWave-ai/nWave> | MIT | 5-level rigor profile system, settings matrix, profile schema, per-task quality scaling | `docs/research/rigor-profiles.md` | 2026-03-07 |
| Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Max-3 fix cycles, automated quality gates, model-agnostic eval approach | `docs/research/rigor-profiles.md` | 2026-03-07 |

## Retrospective Learning Hook (Task #621)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Conductor retrospective agent | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Post-track retrospective â†’ patterns.md + errors.json knowledge layer | `docs/research/retrospective-learning-hook.md` | 2026-03-07 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Verbal self-reflection stored in episodic memory buffer for agent learning | `docs/research/retrospective-learning-hook.md` | 2026-03-07 |

## WIP Continuity Store Research (Task #615)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| quoroom-ai/room agent-loop.ts | <https://github.com/quoroom-ai/room/blob/main/src/shared/agent-loop.ts> | MIT | WIP save/load pattern, CONTINUE FORWARD prompt injection, auto-WIP fallback, momentum gap | `docs/research/wip-continuity-store.md` | 2026-03-07 |
| LangGraph durable execution | <https://docs.langchain.com/oss/python/langgraph/durable-execution> | MIT | Checkpoint persistence concept, thread-id keyed state, resume semantics | `docs/research/wip-continuity-store.md` | 2026-03-07 |

## HeartbeatRunner Research (Task #616)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | MIT | Proactive agent timer pattern, HEARTBEAT_OK suppression contract | `docs/research/heartbeat-runner.md` | 2026-03-07 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | PSF | TaskGroup structured concurrency for sibling coroutines | `docs/research/heartbeat-runner.md` | 2026-03-07 |
| APScheduler user guide | <https://apscheduler.readthedocs.io/en/latest/userguide.html> | MIT | Scheduler framework evaluation (rejected â€” YAGNI) | `docs/research/heartbeat-runner.md` | 2026-03-07 |

## Rich Table CLI Research (Task #630)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rich Tables docs | <https://rich.readthedocs.io/en/latest/tables.html> | MIT | Table API, add_column, add_row, add_section, box styles, Column options | `docs/research/rich-table-cli.md` | 2026-03-07 |
| Rich Console docs | <https://rich.readthedocs.io/en/latest/console.html> | MIT | Terminal auto-detection, is_terminal, NO_COLOR env var, pipe behavior | `docs/research/rich-table-cli.md` | 2026-03-07 |

## Enhanced bearclaw status with rich.Panel (Task #631)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| rich-cli Panel + Table pattern | <https://github.com/Textualize/rich-cli/blob/main/src/rich_cli/__main__.py> | MIT | Panel wrapping Table for structured CLI output, border_style convention | `src/bearclaw/cli.py` (`_daemon_status`) | 2026-03-07 |
| Prefect server CLI status display | <https://github.com/PrefectHQ/prefect/blob/main/src/prefect/cli/_server_utils.py> | Apache-2.0 | Plain text for status, Table for service listing â€” informed key-value layout choice | `docs/research/enhanced-bearclaw-status.md` | 2026-03-07 |

## Knowledge Sub-Packages Research (Task #566)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex core layout | <https://github.com/run-llama/llama_index/tree/main/llama-index-core/llama_index/core> | MIT | Sub-package organization at scale (40+ dirs), splitting rationale | `docs/research/knowledge-subpackages.md` | 2026-03-07 |
| LangChain core layout | <https://github.com/langchain-ai/langchain/tree/master/libs/core/langchain_core> | MIT | Sub-package organization, domain grouping per concern | `docs/research/knowledge-subpackages.md` | 2026-03-07 |
| Python Guide â€” Structuring Your Project | <https://docs.python-guide.org/writing/structure/> | CC-BY-NC-SA-3.0 | PEP 20 "flat is better than nested", module/package guidance | `docs/research/knowledge-subpackages.md` | 2026-03-07 |
| Ionel Cristian Maries â€” Packaging a Python library | <https://blog.ionelmc.ro/2014/05/25/python-packaging/> | Blog | "Flat is better than nested" for data; src-layout advocacy | `docs/research/knowledge-subpackages.md` | 2026-03-07 |

## Role Policy Before Agent Construction (Task #561)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agent constructor docs | <https://ai.pydantic.dev/agents/> | MIT | Agent init signature, stateless construction, no I/O side effects | `docs/research/role-policy-before-agent-construction.md` | 2026-03-07 |
| PydanticAI Toolsets â€” FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | MIT | `toolset.filtered()` API, compose-before-construct pattern | `docs/research/role-policy-before-agent-construction.md` | 2026-03-07 |

## Role System Complexity Evaluation (Task #565)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Toolsets â€” FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | MIT | Native tool filtering as simpler alternative to custom role policy | `docs/research/role-system-complexity.md` | 2026-03-07 |
| CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | Apache-2.0 | Per-agent tools list, no role-based access abstraction | `docs/research/role-system-complexity.md` | 2026-03-07 |

## Workflow, Dashboards & Developer Tools (Task #583)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Textualize/rich | <https://github.com/Textualize/rich> | MIT | Terminal formatting: tables, progress bars, panels, tracebacks | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| Textualize/textual | <https://github.com/Textualize/textual> | MIT | TUI framework evaluation for future dashboard | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| otel-tui | <https://github.com/ymtdzzz/otel-tui> | Apache-2.0 | Terminal OTel viewer for observability display | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| Rich progress docs | <https://rich.readthedocs.io/en/latest/progress.html> | MIT | Multi-task progress bar patterns | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |

## Textual TUI Dashboard Evaluation (Task #633)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| darrenburns/posting | <https://github.com/darrenburns/posting> | Apache-2.0 | Textual HTTP client TUI â€” real-world complexity reference (~6k LOC) | `docs/research/textual-tui-dashboard.md` | 2026-03-07 |
| tconbeer/harlequin | <https://github.com/tconbeer/harlequin> | MIT | Textual SQL IDE â€” large-scale Textual app, DataTable usage | `docs/research/textual-tui-dashboard.md` | 2026-03-07 |
| Textual reactivity guide | <https://textual.textualize.io/guide/reactivity/> | MIT | Reactive attributes, watch methods, data binding for live updates | `docs/research/textual-tui-dashboard.md` | 2026-03-07 |
| Textual layout guide | <https://textual.textualize.io/how-to/design-a-layout/> | MIT | Dock, FR units, containers â€” dashboard panel layout patterns | `docs/research/textual-tui-dashboard.md` | 2026-03-07 |

## ks_ Rename Research (Task #560)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer docs â€” Custom Command Name | <https://typer.tiangolo.com/tutorial/commands/name/> | MIT | Function name vs CLI command name decoupling | `docs/research/ks-rename.md` | 2026-03-07 |
| Typer docs â€” SubCommands Single File | <https://typer.tiangolo.com/tutorial/subcommands/single-file/> | MIT | Canonical `{group}_{action}` function naming pattern | `docs/research/ks-rename.md` | 2026-03-07 |

## PydanticAI Deprecation Warnings Research (Task #556)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI changelog v0.8.1 | <https://ai.pydantic.dev/changelog/> | MIT | Deprecation of bare model names (PR #2711), required `provider:model` format | `docs/research/pydanticai-deprecation-warnings.md` | 2026-03-07 |
| PydanticAI `infer_model()` source | local `.venv/.../pydantic_ai/models/__init__.py` | MIT | Warning trigger logic: string without `:` + known prefix â†’ DeprecationWarning | `docs/research/pydanticai-deprecation-warnings.md` | 2026-03-07 |

## Conftest Extraction Research (Task #555)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest docs â€” conftest.py fixtures | <https://docs.pytest.org/en/stable/reference/fixtures.html> | MIT | Fixture scoping, conftest auto-discovery, sharing fixtures across files | `docs/research/conftest-extraction.md` | 2026-03-07 |
| pytest docs â€” how to use fixtures | <https://docs.pytest.org/en/stable/how-to/fixtures.html> | MIT | Factory-as-fixture pattern, fixture organization best practices | `docs/research/conftest-extraction.md` | 2026-03-07 |

## Optional Tool Graceful Degradation Research (Task #611)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain `guard_import()` | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/utils/utils.py> | MIT | `guard_import()` fail-with-guidance pattern for missing optional deps | `docs/research/optional-tool-graceful-degradation.md` | 2026-03-07 |
| Haystack `LazyImport` | <https://github.com/deepset-ai/haystack/blob/main/haystack/lazy_imports.py> | Apache-2.0 | Deferred `ImportError` context manager for optional deps | `docs/research/optional-tool-graceful-degradation.md` | 2026-03-07 |

## Slack Channel send_file Research (Task #552)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack SDK Web Client docs | <https://docs.slack.dev/tools/python-slack-sdk/web/index.html> | MIT | `files_upload_v2` usage pattern, parameters, threading support | `docs/research/slack-send-file.md` | 2026-03-07 |
| Slack `files.upload` API reference | <https://docs.slack.dev/reference/methods/files.upload> | N/A | Confirmed deprecation of old API; v2 via `getUploadURLExternal` + `completeUploadExternal` is required | `docs/research/slack-send-file.md` | 2026-03-07 |
| slack_sdk `AsyncWebClient` source | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/web/async_client.py> | MIT | `files_upload_v2` 3-step implementation details | `docs/research/slack-send-file.md` | 2026-03-07 |

## Knowledge `__init__.py` Trim Research (Task #550)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 8 â€” Public and Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | PSF | `__all__` guidance, public vs internal naming, re-export conventions | `docs/research/knowledge-init-trim.md` | 2026-03-07 |
| Google Python Style Guide â€” Imports | <https://google.github.io/styleguide/pyguide.html#22-imports> | CC-BY-3.0 | Import conventions, module-level imports, package API patterns | `docs/research/knowledge-init-trim.md` | 2026-03-07 |

## Browser Snapshot Tool Design (Task #727)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| browser-use Agent + BrowserStateSummary | <https://github.com/browser-use/browser-use> | MIT | DOM state exposure pattern, selector_map for interactive elements, automatic state injection | `docs/research/browser-snapshot-tool.md` | 2026-03-10 |
| Stagehand observe() API | <https://github.com/browserbase/stagehand> | MIT | High-level browser observation primitives, alternative to raw snapshot | `docs/research/browser-snapshot-tool.md` | 2026-03-10 |
| Playwright CDPSession docs | <https://playwright.dev/python/docs/api/class-cdpsession> | Apache-2.0 | CDPSession.send() API, detach lifecycle, usage pattern for Accessibility domain | `docs/research/browser-snapshot-tool.md` | 2026-03-10 |

## Rich Traceback and RichHandler Research (Task #632)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rich logging docs | <https://rich.readthedocs.io/en/stable/logging.html> | MIT | `RichHandler` constructor params, Console isolation, markup=False safety | `docs/research/rich-traceback-richhandler.md` | 2026-03-07 |
| Rich traceback docs | <https://rich.readthedocs.io/en/stable/traceback.html> | MIT | `install()` API, `suppress` param, `show_locals` flag | `docs/research/rich-traceback-richhandler.md` | 2026-03-07 |
| `RichHandler` source (Textualize/rich) | <https://github.com/Textualize/rich/blob/master/rich/logging.py> | MIT | Handler emits via `Console.print()`, independent of other handlers' formatters | `docs/research/rich-traceback-richhandler.md` | 2026-03-07 |
| Litestar logging config | <https://github.com/litestar-org/litestar/blob/main/litestar/logging/config.py> | MIT | Prior art: `RichTracebackFormatter` usage in structured logging config | `docs/research/rich-traceback-richhandler.md` | 2026-03-07 |

## Re-exports in Empty `__init__.py` Research (Task #549)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python import system docs | <https://docs.python.org/3/reference/import.html#regular-packages> | PSF | `__init__.py` semantics, submodule binding rules | `docs/research/init-reexports.md` | 2026-03-07 |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> | MIT | 100+ re-export pattern for library public API | `docs/research/init-reexports.md` | 2026-03-07 |
| httpx `__init__.py` | <https://github.com/encode/httpx> | BSD-3 | Heavy re-export + `__all__` pattern for library | `docs/research/init-reexports.md` | 2026-03-07 |

## Lazy-Singleton OwlBearSettings Research (Task #536)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| FastAPI Settings docs | <https://fastapi.tiangolo.com/advanced/settings/> | MIT | `@lru_cache` singleton pattern for pydantic-settings; official recommendation from Typer/FastAPI author | `docs/research/lazy-singleton-settings.md` | 2026-03-07 |
| Typer Callback docs | <https://typer.tiangolo.com/tutorial/commands/callback/> | MIT | `@app.callback()` pattern for shared CLI state; sub-Typer propagation limitations | `docs/research/lazy-singleton-settings.md` | 2026-03-07 |

## Brittle Prompt Assertions Research (Task #554)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI test_agent.py | <https://github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py> | MIT | How PydanticAI tests agents â€” behavior-based, never asserts on prompt content | `docs/research/brittle-prompt-assertions.md` | 2026-03-07 |
| CheckList (Ribeiro et al. 2020) | <https://arxiv.org/abs/2005.04118> | N/A | Invariance/directional testing principles for ML â€” test properties not literals | `docs/research/brittle-prompt-assertions.md` | 2026-03-07 |
| Eugene Yan â€” Testing ML Systems | <https://eugeneyan.com/writing/testing-ml/> | N/A | Implementation vs learned-behavior tests; assert on properties not exact outputs | `docs/research/brittle-prompt-assertions.md` | 2026-03-07 |

## Docstring Style Standardization Research (Task #543)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Ruff pydocstyle convention docs | <https://docs.astral.sh/ruff/settings/#lintpydocstyleconvention> | MIT | `convention = "google"` setting; which D rules are included/excluded per convention | `docs/research/docstring-style.md` | 2026-03-07 |
| Ruff FAQ: Google/NumPy docstrings | <https://docs.astral.sh/ruff/faq/#does-ruff-support-numpy-or-google-style-docstrings> | MIT | Exact rule set for Google convention; incremental enablement workflow | `docs/research/docstring-style.md` | 2026-03-07 |

## Slack Sender Validation Research (Task #526)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack `message.im` event reference | <https://docs.slack.dev/reference/events/message.im> | Slack ToS | DM event payload structure; `user` field identifies sender | `docs/research/slack-sender-validation.md` | 2026-03-07 |
| Slack Events API docs | <https://docs.slack.dev/apis/events-api> | Slack ToS | Event wrapper structure; `user` field on inner event; `bot_message` subtype; server-side rate limits (30K/workspace/60min) | `docs/research/slack-sender-validation.md` | 2026-03-07 |

## ErrorJournal Async-Safety Research (Task #541)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `asyncio.to_thread` | <https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread> | PSF | stdlib API for offloading blocking I/O to thread pool; confirmed uses `run_in_executor` internally | `docs/research/error-journal-async.md` | 2026-03-07 |
| aiofiles library (v25.1.0) | <https://github.com/Tinche/aiofiles> | Apache-2.0 | Async file I/O library; confirmed it also uses `run_in_executor` under the hood; evaluated as alternative approach | `docs/research/error-journal-async.md` | 2026-03-07 |

## Init Re-exports Research (Task #549)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs — Regular packages | <https://docs.python.org/3/reference/import.html#regular-packages> | PSF | `__init__.py` execution semantics; `from .foo import Bar` binding behavior | `docs/research/init-re-exports.md` | 2026-03-15 |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> | MIT | Re-export pattern: eager imports + `__all__` tuple, grouped by source module | `docs/research/init-re-exports.md` | 2026-03-15 |

## Hardcoded Model Defaults Research (Task #551)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | MIT | Agent model parameter patterns; model is caller-provided, not settings-integrated | `docs/research/hardcoded-model-defaults.md` | 2026-03-07 |
| pydantic-settings docs | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/> | MIT | BaseSettings as single source of truth pattern; env var override; field defaults centralized | `docs/research/hardcoded-model-defaults.md` | 2026-03-07 |

## BrowserConfig Nesting Research (Task #553)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic-settings docs â€” nested models | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values> | MIT | `env_nested_delimiter`, `nested_model_default_partial_update`, nested BaseModel env var mapping | `docs/research/browser-config-nesting.md` | 2026-03-07 |
| pydantic-settings test suite | <https://github.com/pydantic/pydantic-settings/blob/main/tests/test_settings.py> | MIT | `test_nested_env_complex_values`, `test_class_nested_model_default_partial_update` â€” confirmed `env_prefix` + `env_nested_delimiter='__'` pattern works with nested BaseModel fields | `docs/research/browser-config-nesting.md` | 2026-03-07 |

## CLI Error-Exit Pattern Research (Task #532)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer â€” Terminating docs | <https://typer.tiangolo.com/tutorial/terminating/> | MIT | `typer.Exit` usage patterns, canonical error-exit idiom | `docs/research/cli-error-exit.md` | 2026-03-07 |
| Typer GitHub repo | <https://github.com/fastapi/typer> | MIT | Confirmed no built-in error helper; user-space pattern | `docs/research/cli-error-exit.md` | 2026-03-07 |
| Slack Security Best Practices | <https://docs.slack.dev/authentication/best-practices-for-security> | Slack ToS | "Validate message source" pattern; rate-limiting guidance; prompt injection mitigation for AI apps; comprehensive logging | `docs/research/slack-sender-validation.md` | 2026-03-07 |

## ErrorJournal Dedup Key Research (Task #567)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Sentry Issue Grouping docs | <https://docs.sentry.io/concepts/data-management/event-grouping/> | BSL-1.1 | Fingerprint-based event dedup: hash of (exception_type, value, stack_trace); grouping hierarchy; time-window suppression | `docs/research/error-journal-dedup.md` | 2026-03-07 |
| structlog processors docs | <https://www.structlog.org/en/stable/processors.html> | MIT | Processor-chain filtering pattern; `DropEvent` for dedup-style suppression; composable filter-before-write design | `docs/research/error-journal-dedup.md` | 2026-03-07 |

## Exception Hierarchy Research (Task #539)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx exceptions module | <https://github.com/encode/httpx/blob/master/httpx/_exceptions.py> | BSD-3 | Single-root `HTTPError(Exception)` hierarchy pattern; MI for timeout cross-cutting | `docs/research/exception-hierarchy.md` | 2026-03-07 |
| requests exceptions module | <https://github.com/psf/requests/blob/main/src/requests/exceptions.py> | Apache-2.0 | `RequestException(IOError)` root; MI pattern `ConnectTimeout(ConnectionError, Timeout)` | `docs/research/exception-hierarchy.md` | 2026-03-07 |
| Click exceptions module | <https://github.com/pallets/click/blob/main/src/click/exceptions.py> | BSD-3 | `ClickException(Exception)` root; intentional exclusion of `Abort`/`Exit` from hierarchy | `docs/research/exception-hierarchy.md` | 2026-03-07 |
| Django core exceptions | <https://github.com/django/django/blob/main/django/core/exceptions.py> | BSD-3 | No single root â€” flat exceptions; studied as anti-pattern | `docs/research/exception-hierarchy.md` | 2026-03-07 |

## Centralize trafilatura.extract Research (Task #537)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | Apache-2.0 | `extract()` API params (`output_format`, `include_links`, `url`); `extract_metadata()` API; `Extractor` settings class | `docs/research/centralize-trafilatura.md` | 2026-03-07 |
| trafilatura GitHub repo | <https://github.com/adbar/trafilatura> | Apache-2.0 | Confirmed extract API surface, optional params, metadata extraction | `docs/research/centralize-trafilatura.md` | 2026-03-07 |
| Slack `message` event subtypes | <https://docs.slack.dev/reference/events/message> | Slack ToS | `bot_message` subtype has no `user` field; full subtype taxonomy for filtering | `docs/research/slack-sender-validation.md` | 2026-03-07 |
| Bolt for Python event listening | <https://docs.slack.dev/tools/bolt-python/concepts/event-listening> | Slack ToS | Subtype filtering pattern; `bot_message` filter via event dict matching | `docs/research/slack-sender-validation.md` | 2026-03-07 |

## Declarative Tool Registration Research (Task #538)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Toolsets docs (v1.67) | <https://ai.pydantic.dev/toolsets/> | MIT | `FunctionToolset` registration APIs: `@toolset.tool`, `tools=` constructor, `add_function()`; no class-level declarative API exists | `docs/research/declarative-tool-registration.md` | 2026-03-07 |
| pydantic-ai-skills | <https://github.com/DougTrajano/pydantic-ai-skills> | MIT | Third-party `SkillsToolset`; uses same imperative `add_function()`-style pattern, no declarative class API | `docs/research/declarative-tool-registration.md` | 2026-03-07 |

## TOML Config Resolution Research (Task #545)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic-settings docs â€” Other settings source | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#other-settings-source> | MIT | `TomlConfigSettingsSource` API, `toml_file` model_config, `settings_customise_sources` override pattern | `docs/research/toml-config-resolution.md` | 2026-03-07 |
| pydantic-settings docs â€” Field value priority | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#field-value-priority> | MIT | Default source priority ordering (CLI > init > env > dotenv > secrets > defaults) | `docs/research/toml-config-resolution.md` | 2026-03-07 |

## Validator Role Policy Research (Task #524)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP LLM06:2025 Excessive Agency | <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/> | CC-BY-SA | Least-privilege tool access for LLM agents; allow-list over deny-list; minimize extensions guidance | `docs/research/validator-role-policy.md` | 2026-03-07 |
| NVIDIA NeMo-Guardrails security guidelines | <https://github.com/NVIDIA/NeMo-Guardrails/blob/main/docs/security/guidelines.md> | Apache-2.0 | Scoped action permissions for AI agents; explicit tool grants | `docs/research/validator-role-policy.md` | 2026-03-07 |

## Security Audit Log Research (Task #525)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC-BY-SA-4.0 | Security event taxonomy (when/where/who/what), retention guidance, append-only audit trail, events to log | `docs/research/security-audit-log.md` | 2026-03-07 |
| Python logging.handlers docs | <https://docs.python.org/3/library/logging.handlers.html> | PSF | FileHandler append mode, RotatingFileHandler vs non-rotating, handler comparison for audit use case | `docs/research/security-audit-log.md` | 2026-03-07 |
| structlog docs | <https://www.structlog.org/en/stable/> | MIT | Structured logging approach evaluation, processor chain pattern | `docs/research/security-audit-log.md` | 2026-03-07 |

## Startfile Allowlist Research (Task #527)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python os.startfile docs | <https://docs.python.org/3/library/os.html#os.startfile> | PSF | ShellExecute behavior, security implications of opening arbitrary file types | `docs/research/startfile-allowlist.md` | 2026-03-07 |
| OWASP Unrestricted File Upload | <https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload> | CC-BY-SA | Allowlist-over-denylist guidance for file type validation | `docs/research/startfile-allowlist.md` | 2026-03-07 |

## Bootstrap Patching Elimination Research (Task #523)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Fowler â€” DI and IoC | <https://martinfowler.com/articles/injection.html> | CC-BY | Constructor injection as preferred DI form; setter injection anti-pattern when constructor is feasible | `docs/research/bootstrap-patching-elimination.md` | 2026-03-07 |
| python-dependency-injector docs | <https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html> | BSD-3 | DI principles in Python; constructor injection vs service locator trade-offs | `docs/research/bootstrap-patching-elimination.md` | 2026-03-07 |

## Ingest Complexity Reduction Research (Task #517)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex IngestionPipeline | <https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/ingestion/pipeline.py> | MIT | Orchestrator-only pipeline pattern; separate docstore for status/dedup; composable transformation stages | `docs/research/ingest-complexity-reduction.md` | 2026-03-06 |
| Haystack Pipelines docs | <https://docs.haystack.deepset.ai/docs/pipelines> | Apache-2.0 | Directed graph of independent Component classes; pipeline as routing/orchestration only | `docs/research/ingest-complexity-reduction.md` | 2026-03-06 |
| Python Patterns: Composition over Inheritance | <https://python-patterns.guide/gang-of-four/composition-over-inheritance/> | CC-BY-SA | SRP via composition; delegate concerns to separate objects; orchestrator composes helpers | `docs/research/ingest-complexity-reduction.md` | 2026-03-06 |

## Slack Receive Timeout Research (Task #513)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | Slack ToS | WebSocket idle behavior, ping-pong keepalive, connection refresh, disconnect protocol | `docs/research/slack-receive-timeout.md` | 2026-03-06 |
| slack_sdk SocketModeClient (aiohttp) | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/socket_mode/aiohttp/__init__.py> | MIT | Auto-reconnect, ping-pong monitoring, session lifecycle, `is_ping_pong_failing()` | `docs/research/slack-receive-timeout.md` | 2026-03-06 |
| Bolt for Python AsyncBaseSocketModeHandler | <https://github.com/slackapi/bolt-python/blob/main/slack_bolt/adapter/socket_mode/async_base_handler.py> | MIT | Official idle pattern: `asyncio.sleep(inf)` after connect, event-driven push model via listeners | `docs/research/slack-receive-timeout.md` | 2026-03-06 |

## Dependency Inversion Research (Task #502)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Cosmic Python Ch.3 â€” Coupling & Abstractions | <https://www.cosmicpython.com/book/chapter_03_abstractions.html> | CC-BY-NC-ND | Functional Core / Imperative Shell, dependency injection via abstractions, callback-based DI for decoupling I/O from business logic | `docs/research/memory-tools-dependency-inversion.md` | 2026-03-06 |
| Python typing.Protocol (PEP 544) | <https://docs.python.org/3/library/typing.html#typing.Protocol> | PSF | Protocol-based structural subtyping for dependency inversion, Callable type hints for callback injection | `docs/research/memory-tools-dependency-inversion.md` | 2026-03-06 |

## Agent Pattern Research (Task #22)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw | <https://github.com/openclaw/openclaw> | MIT | Agent loop, ChannelPlugin adapter, JSONL sessions, hook system, heartbeat, auth rotation, build pipeline, AGENTS.md repo guidelines, multi-agent safety rules, docs linking conventions | `src/owlbear/core/agent.py` (agent loop), `src/owlbear/channels/` (ChannelPlugin adapter), `src/owlbear/memory/session.py` (JSONL sessions), `src/owlbear/core/hooks.py` (hook system), `.github/agents/orchestrator.agent.md` (multi-agent safety) | 2026-02-22 |
| Nanobot | <https://github.com/HKUDS/nanobot> | MIT | MessageBus, Tool ABC, LiteLLM provider, progressive skill loading, two-layer memory, SubagentManager (restricted tool sets, max iterations, result announcement) | `src/owlbear/channels/` (MessageBus), `src/owlbear/skills/registry.py` (progressive skill loading), `src/owlbear/memory/` (two-layer memory), `.github/agents/orchestrator.agent.md` (subagent dispatch pattern) | 2026-02-22 |
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | MIT | Claude Code hooks (13 event types), builder/validator team pattern, meta-agent factory, Plan W Team Lead (supervisor dispatch), TTS integration, safety guards, PostToolUse validators | `src/owlbear/core/hooks.py` (hook events), `.github/agents/builder.agent.md` (builder role), `.github/agents/reviewer.agent.md` (validator role), `.github/agents/architect.agent.md` (Plan W Team Lead + Meta-Agent reasoning), `.github/agents/writer.agent.md` (Validator report pattern) | 2026-02-22 |

## Agent Architecture Optimization (2026-02-26)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | MIT | Plan W Team Lead pattern (supervisor dispatch, dependency chains), Meta-Agent factory (architecture reasoning), Validator structured report (PASS/FAIL with evidence) | `.github/agents/architect.agent.md` (Plan W Team Lead + Meta-Agent inspiration), `.github/agents/writer.agent.md` (Validator report pattern), `.github/agents/orchestrator.agent.md` (named agent routing via `agentName`) | 2026-02-26 |
| OpenClaw | <https://github.com/openclaw/openclaw> | MIT | AGENTS.md repo guidelines, multi-agent workspace safety rules, docs linking conventions (Mintlify) | `.github/agents/writer.agent.md` (docs linking conventions), `.github/copilot-instructions.md` (multi-agent safety guardrails) | 2026-02-26 |
| Nanobot SubagentManager | <https://github.com/HKUDS/nanobot> | MIT | Restricted tool registration per subagent, max iteration limits, result injection via message bus | `.github/agents/orchestrator.agent.md` (dispatch routing with tool inheritance) | 2026-02-26 |
| CrewAI | <https://docs.crewai.com/> | MIT | Agent role/goal/backstory pattern, hierarchical process (manager agent), `allow_delegation`, sequential process, researcher â†’ reporting_analyst pattern | `.github/agents/architect.agent.md` (hierarchical manager pattern), `.github/agents/writer.agent.md` (reporting analyst pattern) | 2026-02-26 |

## Path Sandboxing Research (Task #497)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python pathlib docs | <https://docs.python.org/3/library/pathlib.html> | PSF | `Path.resolve()` + `Path.is_relative_to()` â€” canonical path sandbox pattern | `src/owlbear/paths.py` (`sandbox_path`) | 2026-03-06 |
| OWASP Path Traversal | <https://owasp.org/www-community/attacks/Path_Traversal> | CC BY-SA 4.0 | Threat model: `../` traversal, null-byte injection, absolute path escape | `src/owlbear/paths.py` (`sandbox_path`) | 2026-03-06 |

## kanban-md (Project Management Tool)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README + built-in skills | <https://github.com/antopolskiy/kanban-md> | MIT | CLI reference (commands, flags, output formats), built-in agent skills (`kanban-md` skill, `kanban-based-development` skill), config.yml schema, claim semantics, pick algorithm, classes of service | `.github/skills/kanban-md/SKILL.md` (adapted from built-in `kanban-md` skill), `.github/skills/kanban-based-development/SKILL.md` (adapted from built-in `kanban-based-development` skill), `kanban/config.yml` | 2026-02-07 |
| kanban-md v0.32.2 "Hotkey Net" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.32.2> | MIT | TUI keyboard shortcuts, batch operations, compact output format | `.github/skills/kanban-md/SKILL.md` (TUI shortcuts section) | 2026-02-24 |
| kanban-md v0.33.0 "True North" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.33.0> | MIT | `pick` self-contained output (prints full task details), `--no-body` flag, automatic ID consistency repair, malformed task detection | `.github/skills/kanban-md/SKILL.md` (pick command docs), `.github/skills/kanban-based-development/SKILL.md` (removed redundant show-after-pick) | 2026-02-26 |

## Ingest Concurrency Limit Research (Task #516)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” asyncio.Semaphore | <https://docs.python.org/3/library/asyncio-sync.html#semaphore> | PSF | Semaphore API for bounding concurrent coroutine access to a resource | `docs/research/ingest-concurrency-limit.md` | 2026-03-06 |
| Python docs â€” asyncio.TaskGroup | <https://docs.python.org/3/library/asyncio-task.html#task-groups> | PSF | Structured concurrency alternative (rejected â€” breaks fire-and-forget) | `docs/research/ingest-concurrency-limit.md` | 2026-03-06 |
| Python docs â€” create_task fire-and-forget | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | PSF | Background-tasks set pattern, strong reference requirement | `docs/research/ingest-concurrency-limit.md` | 2026-03-06 |
| SuperFastPython â€” Asyncio Semaphore | <https://superfastpython.com/asyncio-semaphore/> | N/A | Worked example of semaphore limiting concurrent task execution | `docs/research/ingest-concurrency-limit.md` | 2026-03-06 |

## Error Recovery Research (Task #471)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python Logging Cookbook â€” Multiple handlers | <https://docs.python.org/3/howto/logging-cookbook.html> | PSF | Multi-handler pattern: if one sink fails, others capture. Validated that `logger.exception()` always reaches RotatingFileHandler. | `docs/research/recover-from-error-swallowing.md` | 2026-03-06 |
| 12-Factor App â€” XI. Logs | <https://12factor.net/logs> | CC-BY | "Treat logs as event streams." Errors must never vanish; local file logging is the backstop. | `docs/research/recover-from-error-swallowing.md` | 2026-03-06 |

## httpx Timeout Convention (Task #460)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx Timeouts docs | <https://www.python-httpx.org/advanced/timeouts/> | BSD-3 | `httpx.Timeout` API â€” per-phase timeout configuration (connect, read, write, pool) | `docs/research/httpx-timeout.md`, all `httpx.AsyncClient` call sites | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai> | MIT | `DEFAULT_HTTP_TIMEOUT=600`, `connect=5` pattern for LLM streaming clients | `src/owlbear/providers/copilot.py` (`Timeout(600, connect=5)`) | 2026-03-06 |

## Bootstrap Startup Summary Research (Task #492)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Django System Check Framework | <https://docs.djangoproject.com/en/5.1/topics/checks/> | BSD-3 | Tagged checks with severity levels (Debug-Critical), extensible `@register` decorator, errors block startup. Severity classification model. | `docs/research/bootstrap-startup-summary.md` | 2026-03-06 |
| Celery Worker Banner | <https://github.com/celery/celery/blob/main/celery/apps/worker.py> | BSD-3 | `emit_banner()` prints `[config]`/`[queues]`/`[tasks]` sections at startup. Single structured dump of system state. Banner format inspiration. | `docs/research/bootstrap-startup-summary.md` | 2026-03-06 |
| Spring Boot Auto-configuration report | <https://docs.spring.io/spring-boot/reference/using/auto-configuration.html> | Apache-2.0 | `--debug` flag prints condition evaluation (positive/negative matches). Positive/negative match concept. | `docs/research/bootstrap-startup-summary.md` | 2026-03-06 |
| FastAPI Lifespan Events | <https://fastapi.tiangolo.com/advanced/events/> | MIT | `@asynccontextmanager` pattern for startup/shutdown lifecycle events. | `docs/research/bootstrap-startup-summary.md` | 2026-03-06 |

## Command Guard Blocklist Research (Task #494)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Code â€” Security + Sandboxing + Permissions docs | <https://code.claude.com/docs/en/security>, <https://code.claude.com/docs/en/sandboxing>, <https://code.claude.com/docs/en/permissions> | N/A (docs) | Permission-based architecture, OS-level sandbox (Seatbelt/bubblewrap) as primary control, command blocklist (`curl`/`wget`) as defense-in-depth, explicit "Bash permission patterns are fragile" warning | `docs/research/command-guard-blocklist.md` | 2026-03-06 |
| OpenAI Codex CLI â€” README (Security model) | <https://github.com/openai/codex/blob/main/codex-cli/README.md> | Apache-2.0 | 3-tier approval mode (Suggest/Auto Edit/Full Auto), OS sandbox (`sandbox-exec`/Docker), no command blocklist â€” relies on sandbox + approval | `docs/research/command-guard-blocklist.md` | 2026-03-06 |
| Docker seccomp profiles | <https://docs.docker.com/engine/security/seccomp/> | Apache-2.0 (docs) | Allowlist approach for syscalls (deny ~44 of 300+), defense-in-depth layering with capabilities | `docs/research/command-guard-blocklist.md` | 2026-03-06 |

## Toolset Alias Auto-Registration Research (Task #488)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 487 â€” `__init_subclass__` | <https://peps.python.org/pep-0487/> | PSF | Subclass registration pattern via `__init_subclass__`; evaluated as Option B (rejected â€” requires mixin since PydanticAI `FunctionToolset` is external) | `docs/research/toolset-alias-auto-registration.md` | 2026-03-06 |
| Python Data Model â€” `__init_subclass__` | <https://docs.python.org/3/reference/datamodel.html#object.__init_subclass__> | PSF | Official reference for the `__init_subclass__` hook; used to verify Option B feasibility | `docs/research/toolset-alias-auto-registration.md` | 2026-03-06 |

## ClawFeed Research (Task #591)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kevinho/clawfeed | <https://github.com/kevinho/clawfeed> | MIT | Feed curation architecture, typed source registry with per-type config, externalized curation rules as markdown templates, raw_items dedup pipeline, fixed-length digest generation, SKILL.md convention, bookmark deep-dive pattern | `docs/research/clawfeed.md` | 2026-03-06 |

## Visual Explainer Research (Task #592)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | MIT | Self-contained HTML diagram generation skill: SKILL.md workflow (think/structure/style/deliver), Mermaid routing table (content type â†’ rendering approach), aesthetic constraint system (forbidden colors/fonts, curated palettes), HTML templates (architecture, data-table, mermaid-flowchart, slide-deck), CSS patterns (theme vars, depth tiers, zoom controls), diff-review/project-recap command prompts | `docs/research/visual-explainer.md` | 2026-03-06 |
| Anthropic skills repo | <https://github.com/anthropics/skills> | Apache-2.0 | Agent Skills specification, plugin marketplace pattern, skill packaging conventions (SKILL.md + commands + references + templates) | `docs/research/visual-explainer.md` (prior art) | 2026-03-06 |
| Dammyjay93/interface-design | <https://github.com/Dammyjay93/interface-design> | MIT | Design system memory pattern (system.md persistence across sessions), design token management, audit/extract commands, direction presets | `docs/research/visual-explainer.md` (prior art comparison) | 2026-03-06 |

## Approval Scope Limits Research (Task #498)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OAuth 2.0 RFC 6749 S3.3 | <https://www.rfc-editor.org/rfc/rfc6749#section-3.3> | N/A (RFC) | Scope parameter for narrowing access tokens, `expires_in` for time-limited grants, refresh token rotation pattern | `docs/research/approval-scope-limits.md` | 2026-03-07 |
| GitHub OAuth Scopes | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps> | N/A (docs) | Hierarchical scope model (parent absorbs child), fine-grained permission narrowing, normalized scopes | `docs/research/approval-scope-limits.md` | 2026-03-07 |
| AWS IAM Condition Keys | <https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html> | N/A (docs) | `StringEquals`/`StringLike` for arg-pattern conditions, `aws:TokenIssueTime` + date conditions for time-based expiry, request-context condition evaluation | `docs/research/approval-scope-limits.md` | 2026-03-07 |

## Bootstrap Split Research (Task #480)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” Regular packages | <https://docs.python.org/3/reference/import.html#regular-packages> | PSF | Module-to-package migration semantics, `__init__.py` re-export mechanism | `docs/research/bootstrap-split.md` | 2026-03-06 |
| Flask `__init__.py` | <https://github.com/pallets/flask/blob/main/src/flask/__init__.py> | BSD-3 | Re-export pattern: 39-line `__init__.py` re-exporting from submodules for backwards compatibility | `docs/research/bootstrap-split.md` | 2026-03-06 |
| Pydantic `__init__.py` | <https://github.com/pydantic/pydantic/blob/main/pydantic/__init__.py> | MIT | Lazy `__getattr__` re-export for large packages, `__all__` + `_dynamic_imports` pattern | `docs/research/bootstrap-split.md` | 2026-03-06 |
| PydanticAI toolsets/ package | <https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/toolsets> | MIT | Package split structure: abstract.py, function.py, combined.py, wrapper.py â€” one concern per file | `docs/research/bootstrap-split.md` | 2026-03-06 |

## Excalidraw Diagram Skill Research (Task #593)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | MIT | Prompt-driven Excalidraw JSON generation, render-view-fix loop via Playwright, modular reference files (color palette, element templates, JSON schema), section-by-section large diagram strategy | `docs/research/excalidraw-diagram-skill.md`, `.github/skills/excalidraw-diagram/` | 2026-03-06 |
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | 26-tool MCP server architecture, element-level CRUD, describe_scene + get_canvas_screenshot closed feedback loop, read_diagram_guide design prompt pattern | `docs/research/excalidraw-diagram-skill.md` | 2026-03-06 |
| lesleslie/excalidraw-mcp | <https://github.com/lesleslie/excalidraw-mcp> | BSD-3 | Python FastMCP hybrid architecture, element_factory pattern, process_manager for canvas server lifecycle | `docs/research/excalidraw-diagram-skill.md` | 2026-03-06 |
| Excalidraw export utilities | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export> | MIT | Official `exportToSvg`, `exportToCanvas`, `exportToBlob` APIs for programmatic rendering | `docs/research/excalidraw-diagram-skill.md` | 2026-03-06 |

## ExcalidrawRenderService Research (Task #629)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kroki Excalidraw support | <https://kroki.io/#support> | MIT | Kroki already renders Excalidraw JSON to SVG via companion container; SVG-only output; font rendering issues (#1742) | `docs/research/excalidraw-render-service.md` | 2026-03-07 |
| yuzutech/kroki-excalidraw | <https://docs.kroki.io/kroki/setup/install/> | MIT | Companion container architecture, self-hosted font fix (#1998), companion required for Excalidraw diagram type | `docs/research/excalidraw-render-service.md` | 2026-03-07 |
| @excalidraw/utils (npm) | <https://www.npmjs.com/package/@excalidraw/utils> | MIT | Standalone export utilities (exportToSvg, exportToBlob) without React dependency, UMD bundle | `docs/research/excalidraw-render-service.md` | 2026-03-07 |

## CDP Context Isolation Research (Task #495)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Playwright `Browser.new_context()` API | <https://playwright.dev/python/docs/api/class-browser#browser-new-context> | Apache-2.0 | Context isolation guarantees ("won't share cookies/cache"), `Browser.close()` cleanup semantics for created contexts | `docs/research/cdp-context-isolation.md` | 2026-03-06 |
| Chrome DevTools Protocol â€” `Target.createBrowserContext` | <https://chromedevtools.github.io/devtools-protocol/tot/Target/#method-createBrowserContext> | BSD-3 | CDP-level mechanism for incognito-like context creation, `disposeOnDetach` option, `disposeBrowserContext` cleanup | `docs/research/cdp-context-isolation.md` | 2026-03-06 |
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | Apache-2.0 | CDP connection fidelity considerations, default context access via `browser.contexts[0]` pattern | `docs/research/cdp-context-isolation.md` | 2026-03-06 |

## Copilot OAuth Research (Task #30)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Graphicator | `C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator` | (own project) | Device-flow OAuth (auth/copilot.py), agent factory routing (agents/__init__.py), provider config, editor headers, test patterns | `src/owlbear/auth/copilot.py`, `src/owlbear/providers/copilot.py` | 2026-02-26 |
| GitHub OAuth docs | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow> | N/A | RFC 8628 device-flow spec, error codes (authorization_pending, slow_down, expired_token, access_denied), rate limits | `src/owlbear/auth/copilot.py` | 2026-02-26 |

## PydanticAI Integration Research (Tasks #37â€“#45)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI | <https://github.com/pydantic/pydantic-ai> | MIT | Agent class, messages.py, tools.py, providers/openai.py, FunctionToolset, TypeAdapter serialization | `src/owlbear/core/agent.py`, `src/owlbear/memory/session.py`, validation tests | 2026-02-26 |
| pydantic-deepagents | <https://github.com/vstorm-co/pydantic-deepagents> | MIT | HookEvent/HookRegistry pattern (middleware/hooks.py), SkillsToolset pattern, MEMORY.md persistence, agent factory anti-pattern | `src/owlbear/core/hooks.py` (adapted HookEvent/HookRegistry pattern) | 2026-02-26 |

## Teams Integration Research (Task #47)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| M365 Agents SDK (Python) | <https://github.com/microsoft/Agents-for-python> | MIT | Teams bot architecture, Activity model, migration from Bot Framework SDK | `docs/research/teams-integration.md` (comparison) | 2026-02-27 |
| M365 Agents SDK Migration Guide | <https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/bf-migration-python> | N/A | Package mapping, initialization patterns, Teams bot examples | `docs/research/teams-integration.md` (comparison) | 2026-02-27 |
| Microsoft Graph API â€” Teams notifications | <https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview> | N/A | Subscription model, webhook requirements, 60-min expiry | `docs/research/teams-integration.md` (real-time options analysis) | 2026-02-27 |
| Composio Microsoft Teams toolkit | <https://composio.dev/toolkits/microsoft_teams> | N/A | 180 Teams tools inventory, MCP gateway model, OAuth2 managed auth | `docs/research/teams-integration.md` (comparison) | 2026-02-27 |

## Slack Integration Research (Task #83)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | N/A | Socket Mode protocol: WebSocket connection, envelope acknowledgment, no public endpoint | `docs/research/slack-integration.md` (architecture analysis) | 2026-02-27 |
| Bolt for Python (slack_bolt) | <https://github.com/slackapi/bolt-python> | MIT | AsyncApp, SocketModeHandler, decorator patterns, AI Assistant class | `docs/research/slack-integration.md` (comparison) | 2026-02-27 |
| Python Slack SDK (slack_sdk) | <https://github.com/slackapi/python-slack-sdk> | MIT | SocketModeClient (aiohttp), AsyncWebClient, listener pattern | `docs/research/slack-integration.md` (recommendation), future `src/owlbear/channels/slack.py` | 2026-02-27 |
| slack_sdk Socket Mode docs | <https://docs.slack.dev/tools/python-slack-sdk/socket-mode> | N/A | Async SocketModeClient usage, aiohttp/websockets backends, event processing | `docs/research/slack-integration.md` (implementation approach) | 2026-02-27 |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | MIT | Official AI assistant bot using Socket Mode, thread management, OpenAI integration | `docs/research/slack-integration.md` (prior art) | 2026-02-27 |

## Voice I/O Research (Task #49)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| faster-whisper | <https://github.com/SYSTRAN/faster-whisper> | MIT | CTranslate2-based Whisper reimplementation: 4x faster, int8 quantization, built-in Silero VAD, model size benchmarks (small CPU: 1m42s int8 vs 6m58s openai/whisper), no FFmpeg dependency | `docs/research/voice-io.md` (STT recommendation), future `src/owlbear/voice/stt.py` | 2026-02-27 |
| openai/whisper | <https://github.com/openai/whisper> | MIT | Reference Whisper implementation: model size table (tiny 39M â†’ large 1550M), accuracy baselines, .en model variants for English-only use | `docs/research/voice-io.md` (model size comparison) | 2026-02-27 |
| pyttsx3 | <https://pypi.org/project/pyttsx3/> | MPL-2.0 | Offline TTS library: SAPI5 on Windows, eSpeak on Linux, AVSpeech on macOS, sync API (engine.say/runAndWait), voice and rate configuration | `docs/research/voice-io.md` (TTS recommendation), future `src/owlbear/voice/tts.py` | 2026-02-27 |
| Silero VAD | <https://github.com/snakers4/silero-vad> | MIT | Voice Activity Detection: <1ms per chunk on CPU, integrated into faster-whisper's vad_filter parameter, 6000+ language support | `docs/research/voice-io.md` (VAD strategy) | 2026-02-27 |
| SpeechRecognition | <https://pypi.org/project/SpeechRecognition/> | BSD-3 | Unified STT API wrapping Whisper, faster-whisper, Google, Vosk; PyAudio microphone abstraction; evaluated but not recommended (unnecessary abstraction layer) | `docs/research/voice-io.md` (comparison) | 2026-02-27 |
| PyAudio | <https://pypi.org/project/PyAudio/> | MIT | PortAudio Python bindings for cross-platform mic capture; prebuilt Windows wheels; supports WASAPI, DirectSound, WDM-KS | `docs/research/voice-io.md` (audio input recommendation), future `src/owlbear/voice/recorder.py` | 2026-02-27 |
| edge-tts | <https://github.com/rany2/edge-tts> | GPL-3.0 | Microsoft Edge online TTS: high-quality neural voices, async Python API; evaluated but not recommended for MVP (requires internet, violates offline-first principle) | `docs/research/voice-io.md` (TTS comparison) | 2026-02-27 |

## Retry Decorators Research (Task #470)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | Apache-2.0 | `@retry` decorator API, `wait_exponential_jitter`, `retry_if_exception`, `before_sleep_log`, async support | `docs/research/retry-decorators.md` (retry policy design) | 2026-03-06 |
| Slack SDK RetryHandler docs | <https://docs.slack.dev/tools/python-slack-sdk/web/#retryhandler> | N/A | Built-in `ConnectionErrorRetryHandler` + `RateLimitErrorRetryHandler`, backoff+jitter | `docs/research/retry-decorators.md` (Slack retry strategy) | 2026-03-06 |
| AWS Exponential Backoff and Jitter | <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> | N/A | Full Jitter algorithm for distributed retry, thundering herd prevention | `docs/research/retry-decorators.md` (wait strategy rationale) | 2026-03-06 |

## Multi-Agent Orchestration Research (Task #587)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| conductor-orchestrator-superpowers | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Evaluate-Loop (Planâ†’EvalPlanâ†’Executeâ†’EvalExecâ†’Fix), DAG parallel execution, file-based message bus, Board of Directors deliberation, agent-factory worker templates, retrospective agent pattern, anti-rationalization tables, plan-critiquer red-team framework, verification-before-completion iron law | `docs/research/conductor-orchestrator-superpowers.md` (analysis); future: retrospective hook, agent prompt enhancements | 2026-03-06 |
| obra/superpowers | <https://github.com/obra/superpowers> | MIT | Base skill framework conductor extends (72.6k stars); subagent-driven-development, dispatching-parallel-agents, verification-before-completion patterns | `docs/research/conductor-orchestrator-superpowers.md` (prior art validation) | 2026-03-06 |

## CDP Tab Groups Research (Task #65)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| CDP Target Domain (tip-of-tree) | <https://chromedevtools.github.io/devtools-protocol/tot/Target/> | N/A | Full Target domain spec: `createTarget` parameters, `TargetInfo` properties â€” confirmed no tab group support in CDP | `docs/research/cdp-tab-groups.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabGroups` API | <https://developer.chrome.com/docs/extensions/reference/api/tabGroups> | N/A | Tab group management API: `get`, `move`, `query`, `update` â€” only official way to manage tab groups | `docs/research/cdp-tab-groups.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabs.group()` | <https://developer.chrome.com/docs/extensions/reference/api/tabs#method-group> | N/A | `chrome.tabs.group()` â€” assigns tabs to groups, creates groups | `docs/research/cdp-tab-groups.md` (analysis) | 2026-02-27 |
| Puppeteer issue #13215 | <https://github.com/puppeteer/puppeteer/issues/13215> | N/A | Feature request for tab groups closed as "not planned" â€” confirms CDP limitation | `docs/research/cdp-tab-groups.md` (prior art) | 2026-02-27 |
| Playwright Chrome Extensions docs | <https://playwright.dev/python/docs/chrome-extensions> | N/A | Extension loading via `--load-extension`, persistent context requirement, Edge sideloading removal | `docs/research/cdp-tab-groups.md` (feasibility) | 2026-02-27 |

## Token Usage Tracking Research (Task #82)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI `pydantic_ai.usage` | <https://ai.pydantic.dev/api/usage/> | MIT | `RunUsage`/`RequestUsage` dataclasses, `RequestUsage.extract()` genai-prices integration, token fields (input, output, cache_write, cache_read), `total_tokens` property | `docs/research/token-usage-tracking.md` (analysis), future `src/owlbear/observability/usage.py` | 2026-02-27 |
| genai-prices (Pydantic) | <https://github.com/pydantic/genai-prices> | MIT | `calc_price()` API for LLM cost estimation, `Usage` dataclass, `UpdatePrices` background updater, provider/model coverage (900+ models, 30+ providers) | `docs/research/token-usage-tracking.md` (recommendation), future `src/owlbear/observability/cost.py` | 2026-02-27 |
| LiteLLM | <https://github.com/BerriAI/litellm> | MIT | `model_prices_and_context_window.json` comprehensive pricing DB, cost tracking patterns in proxy server | `docs/research/token-usage-tracking.md` (comparison, not adopted â€” too heavy) | 2026-02-27 |

## Knowledge Graph Research (Task #50)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| tool.graphicator | (own project) | â€” | SQLite + sqlite-vec knowledge graph: schema.py (DDL, freeze triggers), graph.py (CRUD), vectors.py (rowid_map bridge, similarity search), models.py (Pydantic records) | `src/owlbear/memory/knowledge/` (schema, graph, vectors, models adapted from db/ package) | 2026-02-27 |
| sqlite-vec | <https://github.com/asg017/sqlite-vec> | Apache-2.0/MIT | Vector search SQLite extension: vec0 virtual table, float/int8/binary vectors, metadata filtering, KNN queries | `src/owlbear/memory/knowledge/schema.py`, `src/owlbear/memory/knowledge/vectors.py` | 2026-02-27 |
| FastEmbed (Qdrant) | <https://github.com/qdrant/fastembed> | Apache-2.0 | Local ONNX-based embedding generation: TextEmbedding API, BAAI/bge-small-en-v1.5 default model (384-dim), no GPU needed | `src/owlbear/memory/knowledge/embeddings.py` | 2026-02-27 |
| nano-graphrag | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal GraphRAG (~1100 LOC): networkx graph + nano-vectordb, pluggable backends | `docs/research/knowledge-graph.md` (architecture comparison) | 2026-02-27 |
| LightRAG (HKUDS) | <https://github.com/HKUDS/LightRAG> | MIT | Full-featured GraphRAG: 4-storage-type architecture, networkx default graph, entity-relationship extraction | `docs/research/knowledge-graph.md` (architecture comparison) | 2026-02-27 |

## Terminal Tool Research (Task #121)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio subprocess docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | PSF | `create_subprocess_shell` API, `communicate()` + `wait_for()` timeout pattern, process cleanup on timeout | `docs/research/terminal-tool.md` (implementation approach), future `src/owlbear/tools/terminal.py` | 2026-02-27 |
| OpenHands ActionExecutor | <https://github.com/All-Hands-AI/OpenHands> | MIT | `CmdRunAction` â†’ `CmdOutputObservation` pattern: structured command results with exit codes, BashSession management | `docs/research/terminal-tool.md` (prior art comparison) | 2026-02-27 |
| Aider run_cmd | <https://github.com/Aider-AI/aider> | Apache-2.0 | Shell command execution with `subprocess.run`, token-aware output handling, git/test/lint command patterns | `docs/research/terminal-tool.md` (prior art comparison) | 2026-02-27 |

## Embedding & Vector DB Research (Tasks #232â€“#239)

### Papers & Academic Sources

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Cormack et al. (2009) â€” RRF paper | <https://dl.acm.org/doi/10.1145/1571941.1572114> | N/A | Original Reciprocal Rank Fusion algorithm: `1/(k+rank)`, k=60, outperforms Condorcet and individual rank learning on TREC | `docs/research/dual-embedding-rrf.md` (RRF formula and analysis) | 2026-02-28 |
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | N/A | Single model producing dense (1024-d) + sparse + ColBERT; self-knowledge distillation; MIRACL/MLDR/NarrativeQA benchmarks; ColBERT reranking quality tables | `docs/research/dual-embedding-rrf.md`, `docs/research/graph-augmented-retrieval.md`, `docs/research/bge-m3-integration.md`, `docs/research/colbert-vs-crossencoder.md` | 2026-02-28 |
| Wang et al. 2024 "Best Practices in RAG" | <https://arxiv.org/abs/2407.01219> | N/A | RAG pipeline analysis with retrieval + reranking strategy recommendations | `docs/research/retrieve-rerank.md` (prior art) | 2026-02-28 |

### Embedding Model Cards (HuggingFace)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BAAI/bge-m3 | <https://huggingface.co/BAAI/bge-m3> | MIT | Multi-functionality (dense+sparse+ColBERT), 8192 tokens, FP16/FP32 CPU behavior, ONNX file tree (dense-only ONNX, .pt linear heads) | `docs/research/dual-embedding-rrf.md`, `docs/research/retrieve-rerank.md`, `docs/research/graph-augmented-retrieval.md`, `docs/research/bge-m3-integration.md` | 2026-02-28 |
| BAAI/bge-large-en-v1.5 | <https://huggingface.co/BAAI/bge-large-en-v1.5> | MIT | MTEB scores (64.23 avg, 54.29 retrieval), 335M params, 1024d, ONNX available | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| BAAI/bge-reranker-v2-m3 | <https://huggingface.co/BAAI/bge-reranker-v2-m3> | Apache-2.0 | Cross-encoder specs (568M params), BEIR NDCG@10 (54.17), MIRACL reranking eval | `docs/research/retrieve-rerank.md`, `docs/research/colbert-vs-crossencoder.md` | 2026-02-28 |
| snowflake-arctic-embed-l | <https://huggingface.co/Snowflake/snowflake-arctic-embed-l> | Apache-2.0 | Best BEIR retrieval score (55.98) among FastEmbed models, 335M params, 1024d, purpose-built for retrieval | `docs/embedding-model-shootout.md` (recommendation) | 2026-02-28 |
| mxbai-embed-large-v1 | <https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1> | Apache-2.0 | Best overall MTEB average (64.68), Matryoshka + binary quantization support, 335M, 1024d | `docs/embedding-model-shootout.md` (runner-up) | 2026-02-28 |
| nomic-embed-text-v1.5 | <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5> | Apache-2.0 | Matryoshka dims (64â€“768), 8192 context, 137M params, MTEB avg 62.28 | `docs/research/dual-embedding-rrf.md`, `docs/research/retrieve-rerank.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| gte-large-en-v1.5 | <https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5> | MIT | 8192 tokens, 409M params, 1024d, best retrieval (57.91) of any feasible model, custom architecture | `docs/embedding-model-shootout.md` (deferred) | 2026-02-28 |
| jina-embeddings-v3 | <https://huggingface.co/jinaai/jina-embeddings-v3> | CC-BY-NC-4.0 | 0.6B params, CC-BY-NC-4.0 license confirmed (non-commercial only), not in FastEmbed | `docs/research/retrieve-rerank.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| e5-mistral-7b-instruct | <https://huggingface.co/intfloat/e5-mistral-7b-instruct> | MIT | 7B params, 4096d, infeasible on 16 GB RAM (FP16 â‰ˆ 14 GB), no ONNX | `docs/embedding-model-shootout.md` (disqualified) | 2026-02-28 |
| MTEB Leaderboard | <https://huggingface.co/spaces/mteb/leaderboard> | N/A | Third-party benchmark scores for embedding models (MTEB avg, BEIR retrieval nDCG@10) | `docs/embedding-model-shootout.md` (benchmarks) | 2026-02-28 |

### Reranker Model Cards

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| jina-reranker-v2-base-multilingual | <https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual> | CC-BY-NC-4.0 | 278M params, BEIR/MIRACL benchmarks (54.83 NDCG@10), CC-BY-NC-4.0 license restriction | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| cross-encoder/ms-marco-MiniLM-L-12-v2 | <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2> | Apache-2.0 | 33M param lightweight reranker, MS Marco TREC DL'19 (74.31), MRR@10 (39.02) | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |

### Vector Database & Retrieval Tools

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| qdrant-client (v1.17.0) | <https://github.com/qdrant/qdrant-client> | Apache-2.0 | Local mode (QdrantLocal), brute-force numpy, persistence (SQLite+pickle), portalocker locking, 20K threshold, congruence tests | `docs/research/qdrant-local.md`, `docs/research/qdrant-local-features.md` | 2026-02-28 |
| Qdrant vectors docs | <https://qdrant.tech/documentation/concepts/vectors> | N/A | Named vectors, sparse vectors, multivectors (ColBERT MAX_SIM) | `docs/research/qdrant-local.md` | 2026-02-28 |
| Qdrant hybrid queries docs | <https://qdrant.tech/documentation/concepts/hybrid-queries> | N/A | Prefetch, RRF/DBSF fusion, multi-stage queries | `docs/research/qdrant-local.md` | 2026-02-28 |
| Qdrant "Hybrid Search Revamped" article | <https://qdrant.tech/articles/hybrid-search> | N/A | ColBERT HNSW optimization (m=0), prefetchâ†’ColBERT rescore pattern, fusion vs reranking comparison | `docs/research/qdrant-local.md`, `docs/research/colbert-vs-crossencoder.md` | 2026-02-28 |
| Qdrant late-interaction article | <https://qdrant.tech/articles/late-interaction-models/> | N/A | BEIR late-interaction benchmarks, ColBERT quantization impact, output-token reranking | `docs/research/colbert-vs-crossencoder.md` | 2026-02-28 |
| Azure AI Search â€” RRF docs | <https://learn.microsoft.com/azure/search/hybrid-search-ranking> | N/A | Production RRF implementation: parallel query execution, k=60, weighted fusion, score decomposition | `docs/research/dual-embedding-rrf.md` (prior art) | 2026-02-28 |
| Milvus multi-vector hybrid search | <https://milvus.io/docs/multi-vector-search.md> | N/A | Dense + sparse + RRF in production: `AnnSearchRequest`, `RRFRanker`, BGE-M3 example | `docs/research/dual-embedding-rrf.md` (prior art) | 2026-02-28 |
| FastEmbed supported models | <https://qdrant.github.io/fastembed/examples/Supported_Models/> | Apache-2.0 | Full ONNX model inventory (dense, sparse SPLADE++, late-interaction ColBERT, rerankers) with sizes; bge-m3 absent from all lists | `docs/embedding-model-shootout.md`, `docs/research/dual-embedding-rrf.md`, `docs/research/retrieve-rerank.md`, `docs/research/graph-augmented-retrieval.md`, `docs/research/bge-m3-integration.md` | 2026-02-28 |

### Integration Samples & GitHub Repos

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| bge-m3-qdrant-sample | <https://github.com/yuniko-software/bge-m3-qdrant-sample> | N/A | Full bge-m3 + Qdrant integration: collection creation, embedding, named vectors, hybrid search | `docs/research/qdrant-local.md`, `docs/research/bge-m3-integration.md` | 2026-02-28 |
| workshop-ultimate-hybrid-search | <https://github.com/qdrant/workshop-ultimate-hybrid-search> | N/A | Official Qdrant hybrid search evaluation workshop; `query_points` API patterns for sparse/RRF search | `docs/research/qdrant-local.md`, `tests/benchmarks/search.py` (`_sparse_search`, `_hybrid_rrf_search`) | 2026-02-28 |
| FlagEmbedding (v1.3.5) | <https://github.com/FlagOpen/FlagEmbedding> | MIT | M3Embedder/BGEM3FlagModel code analysis: constructor behavior (NOT lazy), encode() internals, sparse/ColBERT processing, FP16 CPU auto-disable, dependency chain | `docs/research/bge-m3-integration.md` | 2026-02-28 |
| FastEmbed issue #107 (bge-m3 support) | <https://github.com/qdrant/fastembed/issues/107> | N/A | 2+ year open issue; maintainer confirmed sparse/ColBERT heads need ONNX export | `docs/research/bge-m3-integration.md` | 2026-02-28 |
| FastEmbed PR #602 (bge-m3 dense only) | <https://github.com/qdrant/fastembed/pull/602> | N/A | Feb 2026 PR adding dense-only ONNX bge-m3 embedding, no sparse/ColBERT, no reviewer | `docs/research/bge-m3-integration.md` | 2026-02-28 |
| RAG-Fusion | <https://github.com/Raudaschl/rag-fusion> | N/A | Multi-query + RRF pattern: generate query variants, search each, fuse results | `docs/research/dual-embedding-rrf.md` (prior art) | 2026-02-28 |
| Microsoft GraphRAG | <https://microsoft.github.io/graphrag/query/local_search> | MIT | Local Search entity expansion pattern: embed query â†’ find entities â†’ fan out to neighbors, community reports â†’ prioritize â†’ fill context window | `docs/research/graph-augmented-retrieval.md` (prior art, architecture) | 2026-02-28 |
| neo4j-graphrag-python | <https://github.com/neo4j/neo4j-graphrag-python> | Apache-2.0 | VectorCypherRetriever pattern: vector search â†’ Cypher graph traversal â†’ collect neighbor data â†’ merge into context | `docs/research/graph-augmented-retrieval.md` (prior art) | 2026-02-28 |
| SBERT Retrieve & Re-Rank guide | <https://www.sbert.net/examples/applications/retrieve_rerank/> | N/A | Canonical bi-encoder + cross-encoder architecture description, quality hierarchy (cross-encoder > ColBERT > bi-encoder) | `docs/research/retrieve-rerank.md`, `docs/research/colbert-vs-crossencoder.md` | 2026-02-28 |

## Moonshine Voice Research (Task #240)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | STT engine with native streaming (ergodic encoder), OnnxRuntime C++ backend, Python/Swift/Java bindings, Tinyâ€“Medium model range (26Mâ€“245M), bundled native .dll/.so | `docs/research/moonshine-vs-whisper.md` (recommendation) | 2026-02-28 |
| Moonshine v2 paper | <https://arxiv.org/abs/2602.12241> | N/A | Ergodic streaming encoder architecture, sliding-window attention, benchmark methodology | `docs/research/moonshine-vs-whisper.md` (architecture analysis) | 2026-02-28 |
| Moonshine v1 paper | <https://arxiv.org/abs/2410.15608> | N/A | First-gen flexible-duration input (no fixed 30s Whisper window) | `docs/research/moonshine-vs-whisper.md` (architecture analysis) | 2026-02-28 |
| Flavors of Moonshine paper | <https://arxiv.org/abs/2509.02523> | N/A | Language-specific mono-lingual models, per-language accuracy analysis | `docs/research/moonshine-vs-whisper.md` (analysis) | 2026-02-28 |
| HuggingFace OpenASR Leaderboard | <https://huggingface.co/spaces/hf-audio/open_asr_leaderboard> | N/A | Independent WER scoring methodology for STT models, English benchmark standard | `docs/research/moonshine-vs-whisper.md` (benchmark verification) | 2026-02-28 |
| whisper.cpp (ggml-org) | <https://github.com/ggml-org/whisper.cpp> | MIT | C/C++ Whisper implementation, quantization (Q5_0), AVX2 optimization, Vulkan GPU support, stream example | `docs/research/moonshine-vs-whisper.md` (comparison) | 2026-02-28 |

## Knowledge Pipeline Framework Research (Task #262)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex | <https://github.com/run-llama/llama_index> | MIT | Full RAG framework; PropertyGraphIndex; Qdrant integration; document management; embedding integrations; 300+ integration packages | `docs/research/knowledge-pipeline.md` (comparison matrix) | 2026-02-28 |
| Cognee | <https://github.com/topoteretes/cognee> | Apache 2.0 | Knowledge engine with KG+vector; EmbeddingEngine Protocol pattern; task pipeline architecture; provenance tracking (source_pipeline/source_task); Kuzu embedded graph DB; ontology resolution; cloned to `docs/research/cognee/` for deep analysis | `docs/research/knowledge-pipeline.md` (comparison matrix, provenance pattern recommendation) | 2026-02-28 |
| Microsoft GraphRAG | <https://github.com/microsoft/graphrag> | MIT | Graph enrichment pipeline; community detection (Leiden algorithm); hierarchical summaries; global search patterns; v3 modular packages | `docs/research/knowledge-pipeline.md` (comparison matrix, community detection recommendation) | 2026-02-28 |
| txtai | <https://github.com/neuml/txtai> | Apache 2.0 | All-in-one embeddings DB; graph module (NetworkX); topic modeling via community detection; config-driven graph building; embedding-similarity edges | `docs/research/knowledge-pipeline.md` (comparison matrix, config-driven graph pattern) | 2026-02-28 |
| Haystack (deepset) | <https://github.com/deepset-ai/haystack> | Apache 2.0 | Pipeline orchestrator; Component protocol design; `qdrant-haystack` integration; typed input/output pipeline validation; DocumentStore abstraction | `docs/research/knowledge-pipeline.md` (comparison matrix, component protocol validation) | 2026-02-28 |
| R2R (SciPhi) | <https://github.com/SciPhi-AI/R2R> | MIT | Server-based RAG system; REST API architecture; knowledge graph features; eliminated due to server-only architecture | `docs/research/knowledge-pipeline.md` (elimination analysis) | 2026-02-28 |
| Unstructured.io | <https://github.com/Unstructured-IO/unstructured> | Apache 2.0 | Document processing library; 130+ format support; eliminated â€” intake layer only | `docs/research/knowledge-pipeline.md` (elimination analysis) | 2026-02-28 |

## Web Search Tool Research (Task #292)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ddgs (deedy5) | <https://github.com/deedy5/ddgs> | MIT | DuckDuckGo metasearch library: `DDGS().text()` API returning `{title, href, body}` dicts, multi-engine fallback, `RatelimitException`, sync-only API wrapped with `asyncio.to_thread()` | `src/owlbear/tools/web_search.py` (`_web_search` tool) | 2026-03-01 |
| LangChain DuckDuckGoSearchRun | <https://python.langchain.com/docs/integrations/tools/ddg> | MIT | Thin wrapper over `duckduckgo-search`; snippet-concatenation formatting pattern (adapted to numbered markdown list) | `src/owlbear/tools/web_search.py` (result formatting inspiration) | 2026-03-01 |
| trafilatura | <https://github.com/adbar/trafilatura> | Apache-2.0 | Web content extraction: `extract()` with `output_format="markdown"`, `include_links=True`; fallback-to-raw-HTML pattern | `src/owlbear/tools/web_search.py` (via `extract_content` from `content_extractor`); `src/owlbear/web_extract.py` (`extract_markdown` leaf helper) | 2026-03-01 |

## Conversation Router Research (Task #296)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen SelectorGroupChat | <https://github.com/microsoft/autogen> | MIT | LLM-based speaker selection with prompt template (`{roles}`, `{participants}`, `{history}`), `selector_func` override, `candidate_func` filtering, retry with feedback | `docs/research/conversation-router.md` (prior art comparison), `src/owlbear/agents/orchestrator.md` (prompt-based routing pattern) | 2026-03-01 |
| Semantic Router (aurelio-labs) | <https://github.com/aurelio-labs/semantic-router> | MIT | Embedding-based intent routing: `Route` objects with utterances, cosine similarity classification, sub-10ms decisions; evaluated but not adopted (YAGNI â€” embedding infra overkill for 6-agent system) | `docs/research/conversation-router.md` (prior art comparison) | 2026-03-01 |
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Agent delegation pattern, output functions for hand-off, `RunContext.usage` propagation; confirmed prompt-based routing as simplest approach | `docs/research/conversation-router.md` (recommendation basis), `src/owlbear/agents/orchestrator.md` (routing rules) | 2026-03-01 |

## Bootstrap/Assembly Research (Task #263)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Nanobot (deep read) | <https://github.com/HKUDS/nanobot> | MIT | Startup wiring sequence (gateway command), MessageBus pattern, ChannelManager config-driven init, ContextBuilder system prompt assembly, MemoryStore two-layer consolidation (MEMORY.md + HISTORY.md via LLM tool call), SessionManager JSONL + last_consolidated pointer | `docs/research/bootstrap-assembly.md` (analysis), `src/owlbear/bootstrap.py`, future `src/owlbear/channels/manager.py` | 2026-02-28 |

## Browser Automation Research (Task #264)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| browser-use (v0.12.0) | <https://github.com/browser-use/browser-use> | MIT | CDP `cdp_url` parameter, `channel: 'msedge'`, `enable_default_extensions`, AI browser agent architecture | `docs/research/browser-automation.md` (comparison) | 2026-02-28 |
| crawl4ai (v0.8.0) | <https://github.com/unclecode/crawl4ai> | Apache 2.0 | `BrowserConfig.cdp_url`, `browser_mode` enum, deep crawl strategies (BFS/DFS + crash recovery), prefetch mode | `docs/research/browser-automation.md` (comparison) | 2026-02-28 |
| Stagehand (v3.6.1) | <https://github.com/browserbase/stagehand> | MIT | AI browser automation framework, TypeScript-first, Browserbase cloud service dependency â€” eliminated | `docs/research/browser-automation.md` (comparison) | 2026-02-28 |
| readabilipy (v0.3.0) | <https://pypi.org/project/readabilipy/> | MIT | Mozilla Readability.js Python wrapper, Node.js dependency | `docs/research/browser-automation.md` (content extraction comparison) | 2026-02-28 |

## Moonshine Streaming Research (Task #246)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | Transcriber/Stream/MicTranscriber Python API, event model (LineStarted/LineTextChanged/LineCompleted), VAD integration, ModelArch enum, audio format requirements, session lifecycle | `docs/research/moonshine-streaming.md`, future `src/owlbear/voice/stt.py`, future `src/owlbear/voice/streaming_stt.py` | 2026-02-28 |

## Content Hashing Research (Task #253)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain indexing API | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/indexing/api.py> | MIT | Content+metadata dual hashing (SHA-1/SHA-256), RecordManager pattern, cleanup modes (incremental/full/scoped_full), `_get_document_with_hash()`, `IndexingResult` tracking | `docs/research/content-hashing.md` (comparison), future `src/owlbear/memory/knowledge/ingest.py` (delta re-ingest pattern) | 2026-02-28 |
| LlamaIndex IngestionPipeline | <https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/> | MIT | `doc_id â†’ document_hash` map in docstore, duplicate detection, skip-if-unchanged pattern, IngestionCache for node+transformation hashing | `docs/research/content-hashing.md` (comparison) | 2026-02-28 |
| LightRAG (content hashing) | <https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py> | MIT | MD5 content-addressed document IDs, DocStatusStorage (PENDINGâ†’PROCESSINGâ†’PROCESSED/FAILED), `adelete_by_doc_id()` comprehensive deletion cascade (chunks â†’ entities â†’ relationships â†’ rebuild affected graph), duplicate detection via `full_docs.filter_keys()` | `docs/research/content-hashing.md` (deletion pattern, comparison) | 2026-02-28 |

## Intra-Document Graph Builder Research (Task #255)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG (Edge et al.) | <https://arxiv.org/abs/2404.16130> | N/A | Entity merge + description summarization pattern; cross-chunk consolidation | `docs/research/intra-document-graph.md`, future `src/owlbear/memory/knowledge/graph_builder.py` | 2026-02-28 |
| MS GraphRAG Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow> | MIT | 6-phase indexing pipeline architecture | `docs/research/intra-document-graph.md` | 2026-02-28 |
| LlamaIndex PropertyGraphIndex | <https://developers.llamaindex.ai/docs/llamaindex/module_guides/indexing/lpg_index_guide> | MIT | SchemaLLMPathExtractor, constrained extraction | `docs/research/intra-document-graph.md` | 2026-02-28 |
| nano-graphrag (intra-doc patterns) | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal extract-merge-summarize pattern (~1100 LOC) | `docs/research/intra-document-graph.md` | 2026-02-28 |

## Source Registry Research (Task #254)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex Data Connectors | <https://developers.llamaindex.ai/python/framework/module_guides/loading/connector/> | MIT | Reader â†’ Document pattern, LlamaHub connector registry, type-specific loaders â€” informed SourceType enum design | `docs/research/source-registry.md` (comparison) | 2026-03-01 |
| APScheduler v4 (pre-release) | <https://github.com/agronholm/apscheduler> | MIT | Cron/interval/calendar triggers, SQLite data store, async-native v4 â€” evaluated but not adopted (YAGNI; manual refresh recommended, scheduling deferred to phase-14) | `docs/research/source-registry.md` (scheduling comparison) | 2026-03-01 |

## Inter-Document Graph Builder Research (Task #256)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG (Edge et al.) | <https://arxiv.org/abs/2404.16130> | N/A | Scaling data (~8Kâ€“15K entities per 1M tokens), entity merging by name match, Leiden community detection pipeline â€” used as comparison baseline; implementation chose embedding pre-filter approach instead | `docs/research/inter-document-graph-builder.md` (comparison analysis, scaling reference) | 2026-02-28 |
| GraphRAG Indexing Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | 6-phase pipeline (chunk â†’ extract â†’ graph â†’ community â†’ summarize â†’ embed) â€” evaluated as approach D; not adopted (YAGNI â€” community detection not needed yet) | `docs/research/inter-document-graph-builder.md` (pipeline comparison) | 2026-02-28 |
| Neo4j entity resolution (Senzing) | <https://neo4j.com/developer-blog/entity-resolved-knowledge-graphs/> | N/A | Entity deduplication across datasets via record linkage; different use case from relationship inference â€” not adopted | `docs/research/inter-document-graph-builder.md` (comparison) | 2026-02-28 |

## Project Definition Workflow Research (Task #294)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| gpt-engineer preprompts | <https://github.com/gpt-engineer-org/gpt-engineer/tree/main/gpt_engineer/preprompts> | MIT | `clarify` â†’ `generate` two-phase pipeline; clarify asks one question at a time; philosophy sets coding constraints | `docs/research/project-definition-workflow.md`, `.github/skills/project-definition/SKILL.md` (workflow step design) | 2026-03-01 |
| Devika ARCHITECTURE.md | <https://github.com/stitionai/devika/blob/main/ARCHITECTURE.md> | MIT | Agent Core â†’ Planner â†’ Researcher â†’ Coder pipeline; Planner generates step-by-step plan with focus area; agents are stateless, core manages state | `docs/research/project-definition-workflow.md`, `.github/skills/project-definition/SKILL.md` (6-step workflow pattern) | 2026-03-01 |
| PydanticAI output docs | <https://ai.pydantic.dev/output/> | MIT | `output_type=SomeModel` for structured output; validated structured extraction pattern (`Agent[None, ProjectDefinition]`) | `docs/research/project-definition-workflow.md` (recommendation B: internal structured extraction) | 2026-03-01 |
| aider chat modes | <https://aider.chat/docs/usage/modes.html> | N/A | ask/code workflow â€” discuss first, execute second; architect mode pairs reasoning model with editor model | `docs/research/project-definition-workflow.md` (prior art comparison) | 2026-03-01 |

## Slack Rich Messaging Research (Task #297)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Block Kit â€” Blocks reference | <https://docs.slack.dev/reference/block-kit/blocks> | N/A | Block types (header, section, actions, divider, image, context), max 50 blocks/message, mrkdwn text type | `src/owlbear/channels/slack.py` (`send_blocks`), `docs/research/slack-rich-messaging.md` | 2026-03-01 |
| slack_sdk `AsyncWebClient` (v3.40.1) | <https://github.com/slackapi/python-slack-sdk> | MIT | `chat_postMessage(blocks=...)`, `files_upload_v2` 3-step upload, `thread_ts` threading | `src/owlbear/channels/slack.py` (`send_blocks`, `send_image`), `docs/research/slack-rich-messaging.md` | 2026-03-01 |
| Slack mrkdwn formatting | <https://api.slack.com/reference/surfaces/formatting> | N/A | Markdown â†’ mrkdwn conversion rules: bold, italic, strike, links, code passthrough | `src/owlbear/channels/slack_mrkdwn.py` (`markdown_to_mrkdwn`), `docs/research/slack-rich-messaging.md` | 2026-03-01 |

## Multi-Project Session Research (Task #300)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Devika ProjectManager | <https://github.com/stitionai/devika> | MIT | SQLite-backed `Projects` model, per-project conversation stacks, name â†’ slug pattern, CRUD store pattern | `src/owlbear/projects/models.py` (`_slugify`, `Project` model), `src/owlbear/projects/store.py` (`ProjectStore` CRUD), `docs/research/multi-project-session.md` | 2026-03-01 |
| Nanobot SessionManager | <https://github.com/HKUDS/nanobot> | MIT | JSONL sessions keyed by workspace, workspace-scoped context loading, consolidation pattern | `docs/research/multi-project-session.md` (architecture reference) | 2026-03-01 |
| Mem0 memory scoping | <https://github.com/mem0ai/mem0> | Apache-2.0 | Multi-level memory via user_id/agent_id/run_id metadata, scope-as-filter-parameter pattern | `docs/research/multi-project-session.md` (scoping pattern analysis) | 2026-03-01 |

## Error Recovery Research (Tasks #357â€“#358)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Retries docs | <https://ai.pydantic.dev/retries/> | MIT | `AsyncTenacityTransport`, `RetryConfig`, `wait_retry_after` for HTTP-level retry with Retry-After header support | `src/owlbear/providers/copilot.py` (`_build_retry_transport`, `create_copilot_client`) | 2026-03-01 |

## JsonlStore Base Class Research (Task #465)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain BaseStore | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/stores.py> | MIT | `Generic[K, V]` ABC pattern for typed storage with abstract methods | `docs/research/jsonl-store-base-class.md` (design pattern reference) | 2026-03-06 |

## SLF001 Public API Research (Task #466)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Ruff SLF001 rule | <https://docs.astral.sh/ruff/rules/private-member-access/> | MIT | Rule definition, Pythonic fix pattern (use public interface) | `docs/research/slf001-public-api.md` | 2026-03-06 |

## Terminal CWD Confinement Research (Task #467)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Aider `Commands.cmd_run()` | <https://github.com/Aider-AI/aider/blob/main/aider/commands.py> | Apache-2.0 | Forces `cwd=self.coder.root` for all shell commands; path confinement via `startswith()` | `docs/research/terminal-cwd-confinement.md` | 2026-03-06 |

## Restrict Token File Permissions Research (Task #468)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Copilot Transport Retry Network Errors Research (Task #469)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx Exceptions docs | <https://www.python-httpx.org/exceptions/> | BSD-3 | Exception hierarchy: `ConnectError`/`TimeoutException` are `TransportError` subtypes, separate from `HTTPStatusError` | `docs/research/copilot-retry-network-errors.md` | 2026-03-06 |
| tenacity API docs | <https://tenacity.readthedocs.io/en/latest/api.html> | Apache-2.0 | `retry_if_exception_type` accepts tuple of exception types for multi-type retry | `docs/research/copilot-retry-network-errors.md` | 2026-03-06 |
| PydanticAI `retries.py` | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/retries.py> | MIT | `AsyncTenacityTransport` wraps inner transport call in tenacity `@retry` â€” network exceptions caught if retry condition matches | `docs/research/copilot-retry-network-errors.md` | 2026-03-06 |

## Symphony Multi-Agent Orchestration Research (Task #584)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| openai/symphony | <https://github.com/openai/symphony> | Apache-2.0 | Poll-dispatch-reconcile daemon pattern, workspace isolation, continuation turns, exponential backoff retry, WORKFLOW.md config/prompt contract, orchestrator state machine, agent runner protocol, stall detection | `docs/research/symphony.md` | 2026-03-06 |
| Harness Engineering (OpenAI blog) | <https://openai.com/index/harness-engineering/> | N/A | Agent-first development philosophy: repo as system of record, AGENTS.md as table of contents, layered architecture enforcement, progressive disclosure, entropy/garbage-collection patterns | `docs/research/symphony.md` | 2026-03-06 |
| Codex ExecPlans (OpenAI cookbook) | <https://developers.openai.com/cookbook/articles/codex_exec_plans> | N/A | Self-contained living execution plan documents (PLANS.md): Progress/Decision Log/Surprises sections, milestone-based validation, self-contained novice-guiding specs | `docs/research/symphony.md` | 2026-03-06 |
| Ansible VaultEditor.write_data() | <https://github.com/ansible/ansible/blob/devel/lib/ansible/parsing/vault/__init__.py> | GPL-3.0 | Secure file write pattern: `os.umask(0o077)` â†’ `os.open(path, O_CREAT\|O_EXCL\|O_RDWR\|O_TRUNC, 0o600)` â†’ `os.write()`. Atomic creation with restricted permissions, no TOCTOU race. | `docs/research/restrict-token-permissions.md` | 2026-03-06 |
| Python `os.open()` / `os.chmod()` docs | <https://docs.python.org/3/library/os.html#os.open> | PSF | `os.open(path, flags, mode)` creates files atomically with permissions. On Windows, `os.chmod` only affects read-only flag; ACLs need `icacls` or `pywin32`. | `docs/research/restrict-token-permissions.md` | 2026-03-06 |

## Multi-Agent Swarm Research (Task #588)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| quoroom-ai/room | <https://github.com/quoroom-ai/room> | MIT | Queen/Worker/Quorum swarm architecture, agent-loop.ts (adaptive cycle gap, quiet hours, rate-limit recovery, stuck detection), queen-tools.ts (role-based tool partitioning: QUEEN_TOOLS vs WORKER_TOOLS, delegate_task, control-plane policy), WIP continuity (save_wip/CONTINUE FORWARD pattern), session compression, skills context-activation, self-mod safety guards, process-supervisor.ts (managed child PID tree cleanup) | `docs/research/quoroom-room.md` | 2026-03-06 |
| microsoft/autogen | <https://github.com/microsoft/autogen> | MIT/CC-BY-4.0 | AgentTool pattern (wrap agent as callable tool for delegation), multi-agent orchestration via tool composition, AgentChat API group chat patterns | `docs/research/quoroom-room.md` (comparison reference) | 2026-03-06 |
| Python `pathlib.PurePath.is_relative_to()` | <https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to> | PSF | String-based comparison; must call `.resolve()` first to eliminate `..` segments | `docs/research/terminal-cwd-confinement.md` | 2026-03-06 |
| OWASP A01:2021 Broken Access Control | <https://owasp.org/Top10/A01_2021-Broken_Access_Control/> | CC BY-SA 4.0 | Path traversal as canonical broken-access-control vulnerability | `docs/research/terminal-cwd-confinement.md` | 2026-03-06 |
| PEP 8 Â§Designing for Inheritance | <https://peps.python.org/pep-0008/#designing-for-inheritance> | PSF | "use properties to hide functional implementation behind simple data attribute access syntax" | `docs/research/slf001-public-api.md` | 2026-03-06 |
| Real Python â€” property() | <https://realpython.com/python-property/> | â€” | Property/setter patterns for replacing private attribute access | `docs/research/slf001-public-api.md` | 2026-03-06 |
| OWASP Error Handling Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html> | CC BY-SA 4.0 | Never expose implementation details to users; return generic messages; log details server-side | `docs/research/error-message-sanitization.md` | 2026-03-06 |
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC BY-SA 4.0 | Data to exclude from user-visible output: access tokens, session IDs, passwords, connection strings, file paths | `docs/research/error-message-sanitization.md` | 2026-03-06 |
| Django SafeExceptionReporterFilter | <https://github.com/django/django/blob/main/django/views/debug.py> | BSD-3 | HIDDEN_SETTINGS regex for API/TOKEN/KEY/SECRET/PASS; cleansed_substitute pattern; type-based cleansing | `docs/research/error-message-sanitization.md` | 2026-03-06 |
| Sentry Python SDK filtering | <https://docs.sentry.io/platforms/python/configuration/filtering/> | BSL-1.1 | before_send hook pattern â€” classify exception then modify/drop before external delivery | `docs/research/error-message-sanitization.md` | 2026-03-06 |
| jsonlines library | <https://jsonlines.readthedocs.io/en/latest/> | BSD-3 | JSONL append/read patterns, custom serializer hooks, line-oriented persistence | `docs/research/jsonl-store-base-class.md` (design validation) | 2026-03-06 |
| Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | MIT | `TypeAdapter.dump_json`/`validate_json` for arbitrary types, create-once-reuse pattern | `docs/research/jsonl-store-base-class.md` (serialization approach) | 2026-03-06 |
| tenacity docs | <https://tenacity.readthedocs.io/> | Apache-2.0 | `retry_if_exception_type`, `stop_after_attempt`, `wait_exponential` composable retry primitives | `src/owlbear/providers/copilot.py` (`_build_retry_transport`), `src/owlbear/core/errors.py` (classification categories aligned to retry policies) | 2026-03-01 |
| PydanticAI ModelRetry docs | <https://ai.pydantic.dev/agents/#reflection-and-self-correction> | MIT | `ModelRetry` exception pattern â€” tool tells LLM "try again" with hint; informed TOOL_SEMANTIC error category design | `src/owlbear/core/errors.py` (`ErrorCategory.TOOL_SEMANTIC`) | 2026-03-01 |

## Knowledge Toolset Research (Task #291)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI RAG example | <https://ai.pydantic.dev/examples/rag/> | MIT | Official RAG pattern: `@agent.tool` â†’ embed query â†’ vector search â†’ format results; adapted for KnowledgeToolset query_knowledge flow | `src/owlbear/tools/knowledge.py` (`_query_knowledge` tool), `docs/research/knowledge-toolset.md` | 2026-03-01 |
| PydanticAI FunctionToolset docs | <https://ai.pydantic.dev/toolsets/> | MIT | `FunctionToolset` subclass API, `add_function()` registration, toolset composition pattern | `src/owlbear/tools/knowledge.py` (`KnowledgeToolset` class), `docs/research/knowledge-toolset.md` | 2026-03-01 |

## Hybrid Search Benchmark Harness (Tasks #377, #379)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BEIR (beir-cellar) | <https://github.com/beir-cellar/beir> | Apache-2.0 | Standard IR benchmark library: `GenericDataLoader` for dataset download + loading, NFCorpus qrels (multi-level relevance 0/1/2), corpus/queries/qrels 3-tuple format | `tests/benchmarks/corpus.py` (`load_nfcorpus`), `tests/benchmarks/conftest.py` (session fixtures) | 2026-03-02 |
| ranx (Bassani) | <https://github.com/AmenRa/ranx> | MIT | IR evaluation library: `Qrels.from_dict()` for ground-truth construction, `Run.from_dict()` for result sets, `evaluate()` for nDCG@10 scoring, `compare()` for multi-run comparison with paired t-test statistical significance | `tests/benchmarks/harness.py` (`build_qrels`, `build_run`), `tests/benchmarks/search.py` (run construction), `tests/benchmarks/evaluate.py` (`evaluate_runs`, `format_results`, `write_results_doc`) | 2026-03-02 |
| workshop-ultimate-hybrid-search | <https://github.com/qdrant/workshop-ultimate-hybrid-search> | N/A | Qdrant `query_points` API patterns: sparse-only `SparseVector` query, dense+sparse `Prefetch` with `FusionQuery(Fusion.RRF)` fusion | `tests/benchmarks/search.py` (`_sparse_search`, `_hybrid_rrf_search`) | 2026-03-02 |

## Programmatic Agent Registration Research (Task #559)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agents docs | <https://ai.pydantic.dev/agents/> | MIT | Agent creation patterns â€” agents are plain objects with no registry, fully programmatic | `docs/research/programmatic-agent-registration.md` | 2026-03-07 |

## Poll-Dispatch-Reconcile Research (Task #614)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| openai/symphony SPEC.md | <https://github.com/openai/symphony/blob/main/SPEC.md> | MIT | Poll-dispatch-reconcile tick sequence, orchestrator state machine, retry/backoff formulas, reconciliation pattern, reference algorithms | `docs/research/poll-dispatch-reconcile.md` | 2026-03-07 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | PSF | TaskGroup for dual-coroutine daemon architecture | `docs/research/poll-dispatch-reconcile.md` | 2026-03-07 |

## OwlBearError Exception Hierarchy Research (Task #576)

## Context Condenser Research (Task #619)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Session-Memory Hook Research (Task #622)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Checkpointer | <https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint> | MIT | Checkpoint persistence pattern: thread-scoped state save/restore, BaseCheckpointSaver interface | `docs/research/session-memory-hook.md` (comparison target) | 2026-03-07 |

## Stale Execution Detector Research (Task #623)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave StaleExecutionDetector | docs/research/nwave.md Â§3.3 P4 | MIT | Wall-clock stale scan pattern: configurable threshold on IN_PROGRESS tasks | `docs/research/stale-execution-detector.md` | 2026-03-07 |
| Quoroom Room stuck detection | docs/research/quoroom-room.md Â§3.4 | MIT | Progress-based detection: productiveToolCalls counter, STUCK directive injection | `docs/research/stale-execution-detector.md` | 2026-03-07 |
| Symphony reconciliation | docs/research/symphony.md Â§3.2 | MIT | Per-tick reconcile pattern: stall detection + state refresh for running tasks | `docs/research/stale-execution-detector.md` | 2026-03-07 |

## Enhanced bearclaw status with rich.Panel (Task #631) — Supplemental

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| rich.Panel API reference | <https://rich.readthedocs.io/en/stable/reference/panel.html> | MIT | Panel constructor params, fit(), nesting renderables, border_style | `docs/research/enhanced-bearclaw-status.md` | 2026-03-07 |
| rich-cli Panel + Table composition | <https://github.com/Textualize/rich-cli/blob/main/src/rich_cli/__main__.py> | MIT | Panel wrapping Table pattern: `Panel(table, border_style="dim", title=...)` | `docs/research/enhanced-bearclaw-status.md` | 2026-03-07 |
| Prefect server CLI _server_utils.py | <https://github.com/PrefectHQ/prefect/blob/main/src/prefect/cli/_server_utils.py> | Apache-2.0 | PID file management, _is_process_running(), generate_welcome_blurb text pattern | `docs/research/enhanced-bearclaw-status.md` | 2026-03-07 |
| Temporal Activity Heartbeats | <https://docs.temporal.io/develop/go/failure-detection> | MIT | Heartbeat timeout pattern: periodic progress pings, timeout-based failure detection | `docs/research/stale-execution-detector.md` | 2026-03-07 |

## pytest-cov + pydantic RootModel MRO Crash (Task #646)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic #6584 â€” ImportError with coverage | <https://github.com/pydantic/pydantic/issues/6584> | MIT | Same `sys_modules_saved` root cause; dotted `--cov` sub-package triggers pydantic re-import crash | `docs/research/pytest-cov-pydantic-mro-crash.md` | 2026-03-07 |
| coverage.py `SysModuleSaver` (misc.py) | local venv `coverage/misc.py` | Apache-2.0 | Module cleanup after `find_spec` probing breaks `@functools.cache` identity | `docs/research/pytest-cov-pydantic-mro-crash.md` | 2026-03-07 |
| coverage.py `InOrOut` (inorout.py) | local venv `coverage/inorout.py` | Apache-2.0 | `source_pkgs` vs `source_dirs` classification via `os.path.isdir()` | `docs/research/pytest-cov-pydantic-mro-crash.md` | 2026-03-07 |
| pydantic `import_cached_base_model` | local venv `pydantic/_internal/_import_utils.py` | MIT | `@functools.cache` on `from pydantic import BaseModel` â€” fragile identity assumption | `docs/research/pytest-cov-pydantic-mro-crash.md` | 2026-03-07 |
| Celery task_time_limit | <https://docs.celeryq.dev/en/stable/userguide/configuration.html> | BSD-3-Clause | Hard/soft dual timeout pattern: task_time_limit (SIGKILL) + task_soft_time_limit (catchable) | `docs/research/stale-execution-detector.md` | 2026-03-07 |
| OpenHands Condenser | <https://github.com/OpenHands/OpenHands/tree/main/openhands/memory/condenser> | MIT | RollingCondenser pattern: should_condense/condense contract, condensation events, LLM summarization for context reduction | `docs/research/session-memory-hook.md` (prior art for LLM summary approach) | 2026-03-07 |
| OpenClaw session-memory hook | <https://docs.openclaw.ai/gateway/hooks> | N/A | Hook-based session context persistence on session reset, structured summary generation | `docs/research/session-memory-hook.md` (primary inspiration) | 2026-03-07 |
| PydanticAI Agent API docs | <https://ai.pydantic.dev/api/agent/> | MIT | HistoryProcessor type alias definition, `_process_message_history` validation logic, processor execution point | `docs/research/context-condenser.md` | 2026-03-07 |
| PydanticAI Messages API docs | <https://ai.pydantic.dev/api/messages/> | MIT | ModelMessage/ModelRequest/ModelResponse structure, part types, tool-call pairing | `docs/research/context-condenser.md` | 2026-03-07 |
| OpenHands LLMSummarizingCondenser | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/impl/llm_summarizing_condenser.py> | MIT | Rolling-window LLM summarization pattern: max_size, keep_first, target_size, head+summary+tail | `docs/research/context-condenser.md` | 2026-03-07 |
| OpenHands Condenser base classes | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/condenser.py> | MIT | RollingCondenser ABC, condense() contract | `docs/research/context-condenser.md` | 2026-03-07 |

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx exceptions | <https://github.com/encode/httpx/blob/master/httpx/_exceptions.py> | BSD-3 | Exception hierarchy pattern: `HTTPError` base â†’ `RequestError` â†’ `TransportError` â†’ leaf types; centralized `__all__` exports; no-import base classes | `docs/research/owlbear-error-hierarchy.md` | 2026-03-07 |
| PydanticAI exceptions | <https://ai.pydantic.dev/api/exceptions/> | MIT | Flat hierarchy pattern: `AgentRunError(RuntimeError)` base with leaf subclasses; separate trees for different concerns; no single root | `docs/research/owlbear-error-hierarchy.md` | 2026-03-07 |
| CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | Apache-2.0 | Dual registration: YAML config (recommended) + direct `Agent()` code definition; both first-class | `docs/research/programmatic-agent-registration.md` | 2026-03-07 |

## Mission Control Research (Task #598)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MeisnerDan/mission-control | <https://github.com/MeisnerDan/mission-control> | MIT | Daemon architecture (dispatcher, runner, scheduler, health monitor), loop detection (`LoopDetectionState` with per-task attempt counters + error history, escalation after 3 failures), session resilience (auto-continuation on timeout/max-turns, configurable `maxTaskContinuations`), cost/token tracking (per-session input/output/cache_read/cache_creation capture), credential scrubbing (15+ regex patterns), safe subprocess env (`buildSafeEnv` strips all vars except PATH/HOME/APPDATA/TEMP), token-optimized context snapshot (`generate-context.ts` â†’ ~650 token `ai-context.md`), retry queue with exponential backoff, Eisenhower matrix prioritization, Zod + async-mutex concurrent write safety | `docs/research/mission-control.md` | 2026-03-06 |

## Context-Aware Knowledge Injection Research (Tasks #305, #408)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI runtime `instructions=` param | <https://ai.pydantic.dev/agents/#instructions> | MIT | Dynamic instructions via `.run(instructions="...")` â€” reevaluated per-run, caller-provided; chosen over `@agent.instructions` decorator (which lacks prompt access) | `src/owlbear/core/agent.py` (`turn()` knowledge injection via `run_kwargs["instructions"]`), `docs/research/context-aware-knowledge-injection.md` | 2026-03-02 |
| MemGPT (Packer et al., 2023) | <https://arxiv.org/abs/2310.08560> | N/A | OS-inspired hierarchical memory: auto-retrieve from archival â†’ inject into working context per turn; inspired per-turn auto-inject approach over tool-based RAG | `docs/research/context-aware-knowledge-injection.md` (architecture comparison), `src/owlbear/memory/knowledge/query_service.py` (per-turn injection pattern) | 2026-03-02 |
| LlamaIndex ContextChatEngine | <https://docs.llamaindex.ai> | MIT | Auto-retrieves relevant nodes pre-query; prepends to system prompt with top-k + token budget; informed token-budgeted injection design | `docs/research/context-aware-knowledge-injection.md` (architecture comparison), `src/owlbear/memory/knowledge/query_service.py` (token-budget pattern) | 2026-03-02 |

## CLI Split Research (Task #481)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer docs: Add Typer | <https://typer.tiangolo.com/tutorial/subcommands/add-typer/> | MIT | `app.add_typer()` pattern for composing sub-apps; named vs unnamed (top-level promotion) | `docs/research/cli-split.md` | 2026-03-06 |

## Shell Injection Mitigation Research (Task #493)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Codex CLI â€” Security model & permissions | <https://github.com/openai/codex/blob/main/codex-cli/README.md> | Apache-2.0 | 3-tier approval model (Suggest/Auto Edit/Full Auto), OS-level sandboxing (macOS Seatbelt `sandbox-exec`, Docker on Linux), network disabled in Full Auto, writes limited to workdir | `docs/research/shell-injection-mitigation.md` | 2026-03-06 |
| Claude Code â€” Security docs | <https://code.claude.com/docs/en/security> | N/A (docs) | Permission-based architecture, bash sandbox mode with filesystem/network isolation, command blocklist (curl/wget by default), allowlisting safe commands per-user/per-codebase, write restriction to project folder, command injection detection classifier | `docs/research/shell-injection-mitigation.md` | 2026-03-06 |

## Orchestrator Rewrite: Pure Sequencer Research (Task #682)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Plan-and-Execute | <https://blog.langchain.com/planning-agents/> | N/A (blog) | Plannerâ†’executorâ†’re-planner loop; sequencer architecture for multi-step agents | `docs/research/orchestrator-rewrite-sequencer.md`, `.github/agents/orchestrator.agent.md` (8-step sequencer) | 2026-03-08 |
| Plan-and-Solve Prompting (Wang et al., 2023) | <https://arxiv.org/abs/2305.04091> | arXiv | Divide task into subtasks per plan, execute per plan; theoretical basis for planning agents | `docs/research/orchestrator-rewrite-sequencer.md` | 2026-03-08 |
| LLMCompiler (Kim et al., 2023) | <https://arxiv.org/abs/2312.04511> | arXiv | Planner streams DAG, Task Fetching Unit dispatches when deps met, Joiner decides replan/finish | `docs/research/orchestrator-rewrite-sequencer.md`, `.github/agents/orchestrator.agent.md` (wave dispatch pattern) | 2026-03-08 |

## Typed Hook Payloads Research (Task #483)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python TypedDict spec (PEP 589 + 655 + 728) | <https://typing.python.org/en/latest/spec/typeddict.html> | PSF | TypedDict inheritance, NotRequired, structural subtyping for event payloads | `docs/research/typed-hook-payloads.md` | 2026-03-08 |
| Pluggy hook system (_hooks.py) | <https://github.com/pytest-dev/pluggy/blob/main/src/pluggy/_hooks.py> | MIT | TypedDict usage for HookspecOpts/HookimplOpts, hook calling convention | `docs/research/typed-hook-payloads.md` | 2026-03-08 |
| Python NotRequired (PEP 655) | <https://docs.python.org/3/library/typing.html#typing.NotRequired> | PSF | NotRequired qualifier for optional TypedDict fields, stdlib since 3.11 | `docs/research/typed-hook-payloads.md` | 2026-03-08 |
| CrewAI Flows | <https://docs.crewai.com/concepts/flows> | N/A (docs) | Event-driven @startâ†’@listen pipeline; Flow class is a code state machine, not an LLM | `docs/research/orchestrator-rewrite-sequencer.md`, `.github/agents/orchestrator.agent.md` (step-based state machine) | 2026-03-08 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT | PlanningAgent produces agent:task assignments; team infrastructure dispatches mechanically | `docs/research/orchestrator-rewrite-sequencer.md`, `.github/agents/orchestrator.agent.md` (planner dispatch pattern) | 2026-03-08 |

## Evaluator Agent Final Disposition (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK v0.11.1 — Orchestration | <https://openai.github.io/openai-agents-python/multi_agent/> | MIT | Eval pattern is code-level while-loop, not separate agent; agents-as-tools + handoffs | `docs/research/evaluator-agent-final-disposition.md` | 2026-03-09 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Guided retry via verbal self-reflection — evaluator's unique value prop | `docs/research/evaluator-agent-final-disposition.md` | 2026-03-09 |
| CrewAI Collaboration docs | <https://docs.crewai.com/concepts/collaboration> | Apache-2.0 | No evaluator agent type; uses delegation tools + hierarchical processes; evaluation not a separate concern | `docs/research/evaluator-agent-final-disposition.md` | 2026-03-10 |

## Evaluator Agent Revisited Research (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK | <https://github.com/openai/openai-agents-python> | MIT | No evaluator agent; uses Guardrails + Handoffs; evaluation implicit in framework Runner | `docs/research/evaluator-agent-revisited.md` | 2026-03-09 |
| Anthropic Bash Tool â€” Security section | <https://platform.claude.com/docs/en/docs/agents-and-tools/tool-use/bash-tool> | N/A (docs) | Recommended Docker/VM isolation, command filtering/allowlists, resource limits (ulimit), logging all commands; example blocklist pattern in docs | `docs/research/shell-injection-mitigation.md` | 2026-03-06 |
| Anthropic Computer Use â€” Security considerations | <https://platform.claude.com/docs/en/docs/agents-and-tools/computer-use> | N/A (docs) | VM/container with minimal privileges, domain allowlisting, human confirmation for real-world consequences, prompt injection classifier defense layer | `docs/research/shell-injection-mitigation.md` | 2026-03-06 |
| Typer docs: One File Per Command | <https://typer.tiangolo.com/tutorial/one-file-per-command/> | MIT | Multi-file CLI structure with package layout; callback behavior with sub-apps | `docs/research/cli-split.md` | 2026-03-06 |
| Prefect CLI (prefecthq/prefect) | <https://github.com/prefecthq/prefect/tree/main/src/prefect/cli> | Apache-2.0 | Real-world example of 25+ command files in cli/ package, wired in `__init__.py` | `docs/research/cli-split.md` | 2026-03-06 |

## Daemon Retry Reconciliation Research (Task #512)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AWS Builders' Library â€” Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | N/A | Single-point-in-stack retry principle, multiplicative retry anti-pattern, jitter strategy | `docs/research/daemon-retry-reconciliation.md` | 2026-03-06 |
| Microsoft Azure â€” Retry Pattern | <https://learn.microsoft.com/en-us/azure/architecture/patterns/retry> | N/A (docs) | Layered retry guidance: lower-level should fail fast, higher-level owns policy; idempotency considerations | `docs/research/daemon-retry-reconciliation.md` | 2026-03-06 |

## Cooperative Pipeline Cancellation Research (Task #733)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio `Event` docs | <https://docs.python.org/3/library/asyncio-sync.html#event> | PSF | `Event` is a lightweight cooperative signal with `set()`, `wait()`, and `is_set()`; good fit for polling loop boundaries | `docs/research/cooperative-cancellation.md` | 2026-03-20 |
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | PSF | `Task.cancel()` raises `CancelledError` at the next await; hard interruption is distinct from event polling | `docs/research/cooperative-cancellation.md` | 2026-03-20 |
| AnyIO cancellation docs | <https://anyio.readthedocs.io/en/stable/cancellation.html> | MIT | Cancel scopes provide stronger blocking-await cancellation but change semantics; eliminated in favour of asyncio-native `Event` | `docs/research/cooperative-cancellation.md` | 2026-03-20 |
| .NET cancellation token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | N/A (docs) | One token per cancelable operation and linked parent/child cancellation as prior art for per-operation composition | `docs/research/cooperative-cancellation.md` | 2026-03-20 |

## Hook-Triggered Background Worker Pilot Research (Task #949)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ruvnet/ruflo README | <https://github.com/ruvnet/ruflo> | N/A | Worker catalog (`audit`, `map`, `testgaps`, `document`) and hook-driven daemon framing; used to evaluate candidate pilot types | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |
| Python asyncio task docs | <https://docs.python.org/3/library/asyncio-task.html> | PSF | `create_task()` lifecycle, strong-reference requirement for background tasks, cancellation and timeout guidance | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |
| Python asyncio sync primitives docs | <https://docs.python.org/3/library/asyncio-sync.html> | PSF | `Semaphore` for bounded concurrency and `Event` for cooperative shutdown in background worker design | `docs/research/hook-triggered-background-worker-pilot.md` | 2026-03-23 |

## BearClaw CLI Subprocess Result Helper (Task #926)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `subprocess` docs | <https://docs.python.org/3/library/subprocess.html> | PSF | `CompletedProcess` return contract and the missing-binary `OSError` behavior from `subprocess.run()` | `docs/research/bearclaw-cli-subprocess-result-helper.md` | 2026-03-21 |
| pytest fixtures docs | <https://docs.pytest.org/en/stable/how-to/fixtures.html> | MIT | Shared helper and factory-fixture patterns for `conftest.py`-hosted test utilities | `docs/research/bearclaw-cli-subprocess-result-helper.md` | 2026-03-21 |
| Python `unittest.mock` docs | <https://docs.python.org/3/library/unittest.mock.html> | PSF | `spec` and `side_effect` trade-offs plus lookup-site patching guidance for subprocess seams | `docs/research/bearclaw-cli-subprocess-result-helper.md` | 2026-03-21 |
| Typer testing docs | <https://typer.tiangolo.com/tutorial/testing/> | MIT | CLI-boundary testing with `CliRunner` so helper extraction does not bypass public command behavior | `docs/research/bearclaw-cli-subprocess-result-helper.md` | 2026-03-21 |
| `pytest-subprocess` docs | <https://pytest-subprocess.readthedocs.io/en/latest/> | MIT | Plugin alternative evaluation for subprocess fakes versus a smaller local helper | `docs/research/bearclaw-cli-subprocess-result-helper.md` | 2026-03-21 |

## Claude Code Tips Research (Task #596)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ykdojo/claude-code-tips | <https://github.com/ykdojo/claude-code-tips> | All Rights Reserved | 45 workflow tips, 6 skills (handoff, clone, half-clone, review-claudemd, gha, reddit-fetch), GLOBAL-CLAUDE.md patterns, command decomposition for approval gates, context token management strategies, structured handoff documents, instruction review from session history, agentic coding spectrum (4 levels) | `docs/research/claude-code-tips.md` | 2026-03-06 |

## Prompt vs Skill vs Agent Rules (Task #942)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code prompt files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | Prompt file mechanics: slash-command invocation, tools/agent/model frontmatter, single-task framing, tool-list priority | `docs/research/prompt-vs-skill-vs-agent-rules.md` | 2026-03-24 |
| VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Agent mechanics: persistent persona, tool restrictions, handoffs, model preferences, subagent orchestration | `docs/research/prompt-vs-skill-vs-agent-rules.md` | 2026-03-24 |
| VS Code agent skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Skill mechanics: progressive loading, co-located scripts/resources, open standard, auto-load by relevance | `docs/research/prompt-vs-skill-vs-agent-rules.md` | 2026-03-24 |
| VS Code customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Official taxonomy: instructions for standards, prompts for tasks, skills for capabilities, agents for personas | `docs/research/prompt-vs-skill-vs-agent-rules.md` | 2026-03-24 |

## Global vs Scoped Instructions Audit (Task #705)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Stripe Minions Part 2 — Rule files | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | N/A (blog) | Directory-scoped rule strategy, avoid global rules for context window savings | `docs/research/global-vs-scoped-instructions-audit.md` | 2026-03-10 |
| VS Code — Custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | `applyTo` glob behavior, always-on vs file-based instruction loading, scoping best practices | `docs/research/global-vs-scoped-instructions-audit.md` | 2026-03-10 |

## Screenshot Visual Feedback Research (Task #302)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Computer Use docs | <https://docs.anthropic.com/en/docs/build-with-claude/computer-use> | N/A | Screenshot-after-every-action pattern; base64 in tool_result; coordinate scaling; informed ScreenshotService capture/deliver architecture | `docs/research/screenshot-visual-feedback.md` (architecture analysis), `src/owlbear/tools/screenshot.py` (service pattern) | 2026-03-03 |
| Anthropic quickstart (computer-use-demo) | <https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo> | MIT | Agent loop: action â†’ screenshot â†’ send to LLM; screenshot quality/resize tradeoffs; informed auto-capture-on-error hook design | `docs/research/screenshot-visual-feedback.md` (prior art), `src/owlbear/tools/screenshot_hook.py` (hook pattern) | 2026-03-03 |

## Project Workspace Research (Task #303)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| cookiecutter | <https://github.com/cookiecutter/cookiecutter> | BSD-3 | Jinja2 project templates from repos, `cookiecutter.json` config; informed hardcoded-template approach (simpler, YAGNI) | `docs/research/project-workspace.md` (comparison), `src/owlbear/projects/workspace.py` (template dispatch pattern) | 2026-03-03 |

## Non-Blocking Retrospective Hook Handoff (Task #964)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `asyncio.to_thread` docs | <https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread> | PSF | Official guidance for offloading blocking I/O to thread pool without blocking the event loop | `docs/research/non-blocking-retrospective-hook-handoff.md` | 2026-03-24 |
| Python `asyncio.create_subprocess_exec` docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | PSF | Async subprocess API; precedent for non-blocking subprocess in asyncio | `docs/research/non-blocking-retrospective-hook-handoff.md` | 2026-03-24 |
| aiohttp background tasks docs | <https://docs.aiohttp.org/en/stable/web_advanced.html#background-tasks> | Apache-2.0 | Tracked background task + cleanup context pattern; confirms handler-to-task handoff as standard | `docs/research/non-blocking-retrospective-hook-handoff.md` | 2026-03-24 |
| copier | <https://github.com/copier-org/copier> | MIT | Template lifecycle (scaffold + update), `copier.yml` questions; evaluated but not adopted (YAGNI â€” update lifecycle not needed) | `docs/research/project-workspace.md` (comparison) | 2026-03-03 |

## Frontend Normalize Prompt Design (Task #945)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable `/normalize` SKILL.md | <https://github.com/pbakaus/impeccable/blob/main/source/skills/normalize/SKILL.md> | Apache-2.0 | Plan → Execute → Clean Up structure, 8-dimension checklist, guardrails (never-list), adapted into 4-step workflow with 6 dimensions for `.github/prompts/frontend-normalize.prompt.md` | `docs/research/frontend-normalize-prompt.md` | 2026-03-25 |
| pbakaus/impeccable README | <https://github.com/pbakaus/impeccable> | Apache-2.0 | `audit → normalize → polish` pipeline, optional scope argument (`/normalize blog`), command UX precedent | `docs/research/frontend-normalize-prompt.md` | 2026-03-25 |
| VS Code prompt file docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | `${input:scope}` optional-input syntax, description-only frontmatter contract, `.prompt.md` file placement | `.github/prompts/frontend-normalize.prompt.md` | 2026-03-25 |

## .agent.md Format Validation (Task #4)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Complete .agent.md YAML frontmatter spec: tools, agents, model, handoffs, hooks, user-invocable, disable-model-invocation | `docs/research/agent-md-format.md` | 2026-03-26 |
| VS Code Chat Tools Reference | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Full built-in tool name list for mapping v1 PydanticAI tool references to VS Code equivalents | `docs/research/agent-md-format.md` | 2026-03-26 |
| VS Code Agent Tools docs | <https://code.visualstudio.com/docs/copilot/agents/agent-tools> | CC-BY-4.0 | Tool sets, tool approval, terminal sandbox, MCP tool integration patterns | `docs/research/agent-md-format.md` | 2026-03-26 |
| VS Code Hooks docs | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | Hook lifecycle events, agent-scoped hooks format, PreToolUse/PostToolUse patterns | `docs/research/agent-md-format.md` | 2026-03-26 |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Orchestration patterns, agents field semantics, nested subagent settings, coordinator-worker pattern | `docs/research/agent-md-format.md` | 2026-03-26 |

## Skills-Ref CI Validation Research (Task #44)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| agentskills.io specification | <https://agentskills.io/specification> | N/A | Authoritative frontmatter rules, 6 allowed fields, progressive disclosure tiers | `docs/research/skills-ref-ci-validation.md` | 2026-03-27 |
| skills-ref PyPI package (v0.1.1) | <https://pypi.org/project/skills-ref/> | Apache-2.0 | Published CLI (`agentskills` entry point), dependencies (click, strictyaml), Python ≥3.11 | `docs/research/skills-ref-ci-validation.md` | 2026-03-27 |
| skills-ref validator.py source | <https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/validator.py> | Apache-2.0 | Strict `ALLOWED_FIELDS` set (6 fields), `validate()` and `validate_metadata()` API | `docs/research/skills-ref-ci-validation.md` | 2026-03-27 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | VS Code vendor extensions (`user-invocable`, `argument-hint`, `disable-model-invocation`) read at top level | `docs/research/skills-ref-ci-validation.md` | 2026-03-27 |
| skills-ref CLI source | <https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/cli.py> | Apache-2.0 | CLI entry point structure, validate command, no config/flag for extra fields | `docs/research/skills-ref-ci-validation.md` | 2026-03-27 |

## Voice Protocol Pydantic Models Research (Task #61)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic v2 Unions docs | <https://docs.pydantic.dev/latest/concepts/unions/> | MIT | Literal discriminator + Field(discriminator=...) pattern for tagged message unions | `docs/research/voice-protocol-models.md` | 2026-03-27 |
| Pydantic v2 TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | MIT | validate_json/dump_json API, create-once performance recommendation | `docs/research/voice-protocol-models.md` | 2026-03-27 |

## Extract Knowledge Engine from v1 (Task #15)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG v3 | <https://github.com/microsoft/graphrag> | MIT | Multi-package monorepo structure (packages/), foundation-vs-layer separation pattern, uv workspace usage | `docs/research/extract-knowledge-engine-v1.md` | 2026-03-28 |
| PrivateGPT (Zylon) | <https://github.com/zylon-ai/private-gpt> | Apache-2.0 | Component-based DI, abstraction-first storage, LlamaIndex base abstraction usage | `docs/research/extract-knowledge-engine-v1.md` | 2026-03-28 |
| MCP Python SDK types | <https://github.com/modelcontextprotocol/python-sdk> | MIT | type: Literal[...] on content models, module-level TypeAdapter union instances | `docs/research/voice-protocol-models.md` | 2026-03-27 |

## Build mcp-kanban Server Research (Task #14)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK (v1.26.0) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP v1 decorator patterns, lifespan context, `mcp.run()` stdio transport, `create_connected_server_and_client_session` testing | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |

## AST-based Package Boundary Enforcement (Task #510)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| deer-flow test_harness_boundary.py (MIT) | github.com/bytedance/deer-flow | AST-based import boundary scan pattern (~50 LOC, zero deps) | docs/research/ast-package-boundary-enforcement.md | 2026-04-01 |
| import-linter v2.11 (BSD-2) | github.com/seddonym/import-linter | Mature Python architecture linter with forbidden/independence/layers contracts | docs/research/ast-package-boundary-enforcement.md | 2026-04-01 |
| VS Code MCP Config Reference (CC-BY-4.0) | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | `.vscode/mcp.json` stdio server registration format, `uv run` command pattern | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |
| MCP Tools Spec (2025-06-18) (CC-BY-4.0) | <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | Tool definition schema, `isError` field semantics, input schema annotations | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |

## mcp-kanban Unit Test Strategy (Task #89)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| v1 KanbanToolset tests | `v1/tests/test_kanban_tools.py` | N/A (internal) | Mock subprocess pattern for 7 kanban tools, CLI arg verification, error string testing | `docs/research/mcp-kanban-unit-test-strategy.md` | 2026-03-28 |

## Quality-Runner Wiring into Pipeline Agents (Task #264)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | `agents:` array, nesting depth (max 5), override of `disable-model-invocation`, coordinator/worker pattern | `docs/research/quality-runner-wiring.md` | 2026-03-30 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `agents` field spec, tool inheritance, assign mode, `user-invocable` and `disable-model-invocation` flags | `docs/research/quality-runner-wiring.md` | 2026-03-30 |

## Architect DR Verification Gate (Task #461)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|

## Challenger Subagent Design (Task #465)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | One-shot subagent model, coordinator/worker pattern, multi-perspective review, nesting depth max 5 | `docs/research/challenger-subagent-design.md` | 2026-03-31 |
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agents array override for disable-model-invocation, assign vs inherit tool modes | `docs/research/challenger-subagent-design.md` | 2026-03-31 |
| Du et al. — Improving Factuality through Multiagent Debate (2023) | <https://arxiv.org/abs/2305.14325> | CC-BY-4.0 | Multi-agent debate improves factuality and reasoning; single-round debate effective | `docs/research/challenger-subagent-design.md` | 2026-03-31 |
| Liang et al. — MAD: Multi-Agent Debate (EMNLP 2024) | <https://arxiv.org/abs/2305.19118> | arxiv nonexclusive | Degeneration-of-Thought in self-reflection; external adversarial challenge breaks DoT | `docs/research/challenger-subagent-design.md` | 2026-03-31 |
| Chan et al. — ChatEval multi-agent debate (2023) | <https://arxiv.org/abs/2308.07201> | arxiv nonexclusive | Multi-annotator collaboration outperforms single-agent evaluation | `docs/research/challenger-subagent-design.md` | 2026-03-31 |
| CrewAI Task Guardrails | <https://docs.crewai.com/concepts/tasks> | N/A | Sequential guardrail validation pattern — prerequisite check before task proceeds | `docs/research/architect-dr-verification-gate.md` | 2026-03-31 |
| AutoGen Human-in-the-Loop | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | N/A | HandoffTermination early termination when prerequisite unmet | `docs/research/architect-dr-verification-gate.md` | 2026-03-31 |
| GitHub Actions Environment Protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | N/A | Required-reviewer gate blocks before any work runs | `docs/research/architect-dr-verification-gate.md` | 2026-03-31 |

## Challenger Arch-Review Integration (Task #468)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | agents array overrides disable-model-invocation, one-shot return model | `docs/research/challenger-arch-review-integration.md` | 2026-03-31 |
| OwlBear #465 Challenger design | docs/research/challenger-subagent-design.md | Integration protocol S3e-f, trigger points, error handling | `docs/research/challenger-arch-review-integration.md` | 2026-03-31 |
| OwlBear #228 nesting research | docs/research/subagent-nesting-architecture.md | L2 nesting confirmed, assign mode validation | `docs/research/challenger-arch-review-integration.md` | 2026-03-31 |

## Agent Port to v2 Research (Task #8)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `.agent.md` frontmatter spec, tool/agents fields, handoffs, hooks | `docs/research/agent-port-v2.md` | 2026-03-28 |

## Fresh-Context Retry for Builder Agent (Task #266)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Subagents Guide | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Context isolation, coordinator/worker pattern, nesting depth 5 | `docs/research/fresh-context-retry-builder.md` | 2026-03-30 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Verbal reinforcement learning: evaluator + self-reflection for retry feedback | `docs/research/fresh-context-retry-builder.md` | 2026-03-30 |
| SupaConductor Evaluate-Loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Execute-Evaluate-Fix cycle (max 3), separate evaluator from executor | `docs/research/fresh-context-retry-builder.md` | 2026-03-30 |
| VS Code Chat Tools Reference | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | Complete built-in tool list including tool sets, `todos` naming | `docs/research/agent-port-v2.md` | 2026-03-28 |

## Setup & Sharing Documentation Research (Task #169)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Copilot customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Parent repository discovery, Chat Customizations editor, troubleshooting via Diagnostics/Debug Logs | `docs/research/setup-and-sharing-docs.md` | 2026-03-29 |
| VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | agentFilesLocations, org-level agent sharing, agent name collision behavior | `docs/research/setup-and-sharing-docs.md` | 2026-03-29 |
| VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio server config structure, MCP:List Servers command, server naming conventions | `docs/research/setup-and-sharing-docs.md` | 2026-03-29 |
| Claude Code README | <https://github.com/anthropics/claude-code> | Proprietary | Ultra-minimal README + separate detailed setup docs pattern | `docs/research/setup-and-sharing-docs.md` | 2026-03-29 |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | `agents:` field semantics, restriction patterns, nested subagent config | `docs/research/agent-port-v2.md` | 2026-03-28 |
| mcp-knowledge unit tests | `packages/mcp-knowledge/tests/test_search_knowledge.py` | N/A (internal) | Sister MCP package test pattern: direct function call with mocked AppContext | `docs/research/mcp-kanban-unit-test-strategy.md` | 2026-03-28 |
| MCP Python SDK README (v1) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | `@mcp.tool()` context injection, lifespan pattern, typed `Context[ServerSession, AppContext]` | `docs/research/mcp-kanban-unit-test-strategy.md` | 2026-03-28 |
| kanban-md CLI v0.33.0 | Local binary (`kanban/kanban-md.exe --help`) | N/A | Full subcommand surface (list/show/create/edit/move/board), `--json` flag support, filter flags | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |
| v1 KanbanToolset | `v1/src/owlbear/tools/kanban.py` | N/A | Subprocess wrapper pattern (`_run_kanban`), `--no-color`/`--dir` conventions, error handling approach | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |
| OwlBear MCP SDK deep-dive | `docs/research/mcp-python-sdk.md` | N/A | 3 MCP primitives, transport trade-offs, lifecycle, recommended 3-server architecture | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |
| OwlBear scaffold research | `docs/research/scaffold-mcp-kanban.md` | N/A | Package layout, lifespan pattern, binary path resolution, VS Code registration, minimal tool surface | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |
| OwlBear integration test research | `docs/research/mcp-kanban-integration-tests.md` | N/A | In-memory MCP testing, board isolation via tmp_path, binary availability strategy, test scenarios | `docs/research/build-mcp-kanban-server.md` | 2026-03-28 |

## Knowledge Package Integration + Hybrid Search (Task #34)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MS GraphRAG v3 | <https://github.com/microsoft/graphrag> | MIT | Multi-package monorepo, retrieval as separate concern, graph-augmented search | `docs/research/knowledge-package-integration-hybrid-search.md` | 2026-03-29 |
| LightRAG (HKUDS, EMNLP 2025) | <https://github.com/HKUDS/LightRAG> | MIT | "mix" mode: KG + vector search with token budgets (`max_entity_tokens`, `max_relation_tokens`), reranker integration | `docs/research/knowledge-package-integration-hybrid-search.md` | 2026-03-29 |

## Knowledge Engine Extraction Research — Module Audit (Task #15, update)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| v1 knowledge module inventory | `v1/src/owlbear/memory/knowledge/` (24 modules) | N/A (internal) | Complete module audit: 8 orphaned modules not covered by #15/#32/#33/#34 decomposition | `docs/research/extract-knowledge-engine-v1.md` §3.7 | 2026-03-29 |

## Source Discovery & Bookmarking Research (Task #304)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Rename todo to todos (Task #36)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Cheat Sheet — Chat Tools | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | CC-BY-4.0 | `#todos` is the canonical built-in tool name; `chat.tools.todos.showWidget` setting confirms plural | `docs/research/rename-todo-to-todos.md` | 2026-03-27 |

## Expose reaction_executors via HookRegistry Attribute (Task #991)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Flask `app.extensions` docs | <https://flask.palletsprojects.com/en/stable/api/#flask.Flask.extensions> | BSD-3-Clause | Central app-object dict attribute for storing extension state; validated optional-attribute-on-registry pattern | `src/owlbear/core/hooks.py` (`HookRegistry.reaction_executors`), `docs/research/expose-reaction-executors.md` | 2026-03-24 |
| Celery application docs | <https://docs.celeryq.dev/en/stable/userguide/application.html> | BSD-3-Clause | `app.tasks` dict attribute for late-binding task registry; confirmed assembly-layer assignment without core-layer import | `src/owlbear/core/hooks.py` (`HookRegistry.reaction_executors`), `docs/research/expose-reaction-executors.md` | 2026-03-24 |
| Karakeep (fka Hoarder) | <https://github.com/karakeep-app/karakeep> | AGPL-3.0 | AI-based auto-tagging via LLM prompt; bookmark â†’ extract â†’ tag pipeline; inspired `SourceEvaluator` LLM scoring pattern | `docs/research/source-discovery-bookmarking.md` (prior art), `src/owlbear/memory/knowledge/evaluator.py` (LLM eval pattern) | 2026-03-03 |
| Pinboard API v1 | <https://pinboard.in/api/> | N/A | Minimal bookmark model: url, title, description, tags, datetime, toread flag; `posts/suggest` for tag recommendations; informed `BookmarkStore` field design | `docs/research/source-discovery-bookmarking.md` (data model comparison) | 2026-03-03 |

## HookReaction Notify and Escalate Executor Wiring (Task #957)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Trigger-action model and `send-notification` action delegation pattern used to justify backend-chain factory approach for notify executor | `docs/research/hookreaction-notify-escalate-executors.md` | 2026-03-24 |
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | Signal handler separation from retry engine state used to justify non-blocking escalation executor | `docs/research/hookreaction-notify-escalate-executors.md` | 2026-03-24 |
| Omnivore digest-score | <https://github.com/omnivore-app/omnivore/tree/main/ml/digest-score> | N/A | ML-based relevance scoring (random forest); evaluated but not adopted (too complex for LLM-scored approach) | `docs/research/source-discovery-bookmarking.md` (comparison) | 2026-03-03 |

## Slack Structured Proposals Research (Task #307)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode â€” interactive features | <https://docs.slack.dev/apis/events-api/using-socket-mode/#interactivity> | N/A | `type: "interactive"` envelope, `block_actions` payload, `envelope_id` acknowledgment | `src/owlbear/channels/slack.py` (`_handle_socket_event` interactive branch), `docs/research/slack-structured-proposals.md` | 2026-03-03 |
| Slack Button element reference | <https://docs.slack.dev/reference/block-kit/block-elements/button-element> | N/A | `action_id`, `value`, `style` (primary/danger), `confirm` dialog; informed approval/interactive proposal button design | `src/owlbear/channels/slack_templates.py` (`format_approval_blocks`, `format_interactive_proposal_blocks`) | 2026-03-03 |
| Bolt for Python â€” action listener | <https://docs.slack.dev/tools/bolt-python/concepts/actions> | N/A | `@app.action("action_id")` pattern, `ack()` + `say()` response; informed handler acknowledgment pattern | `docs/research/slack-structured-proposals.md` (architecture comparison) | 2026-03-03 |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | MIT | Thread-based AI assistant pattern, message-per-thread model; informed thread registry design | `src/owlbear/channels/slack.py` (`_thread_registry`, `get_or_create_thread`), `docs/research/slack-structured-proposals.md` | 2026-03-03 |

## BGE-M3 Evaluation Research (Task #375)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | N/A | MIRACL/MLDR benchmarks for dense/sparse/ColBERT quality comparison; self-knowledge distillation training methodology | `docs/bge-m3-evaluation.md` | 2026-03-03 |
| Yannael â€” OpenAI vs open-source embeddings (TDS) | <https://towardsdatascience.com/openai-vs-open-source-multilingual-embedding-models-e5ccb7c90f05> | N/A | Independent MRR evaluation of bge-m3 vs OpenAI embeddings on multilingual retrieval tasks | `docs/bge-m3-evaluation.md` | 2026-03-03 |
| FastEmbed issue #107 (bge-m3 support) | <https://github.com/qdrant/fastembed/issues/107> | N/A | 2+ year open issue tracking bge-m3 3-output support status (dense+sparse+ColBERT via ONNX) | `docs/bge-m3-evaluation.md` | 2026-03-03 |

## Voice Channel Import Research (Task #458)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rasa `core/channels/` | <https://github.com/RasaHQ/rasa/tree/main/rasa/core/channels> | MIT | Channel adapter organization: all channels (incl. `twilio_voice.py`) co-located in `channels/` dir; thin wrapper pattern | `docs/research/voice-channel-import.md` (prior art comparison for relocate-vs-fix decision) | 2026-03-06 |

## SQLite Connection Lifecycle Research (Task #459)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `sqlite3.Connection.close()` | <https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.close> | PSF | `close()` is sync, rolls back pending txn, Python 3.13 emits `ResourceWarning` on unclosed connections | `docs/research/sqlite-connection-lifecycle.md` | 2026-03-06 |
| Datasette `database.py` | <https://github.com/simonw/datasette/blob/main/datasette/database.py> | Apache 2.0 | Long-running daemon SQLite lifecycle: `_all_file_connections` tracking list, explicit `close()` iterates all | `docs/research/sqlite-connection-lifecycle.md` | 2026-03-06 |
| Flask `ctx.py` teardown | <https://github.com/pallets/flask/blob/main/src/flask/ctx.py> | BSD-3 | Cleanup-list pattern: `pop()` iterates teardown callbacks with error suppression | `docs/research/sqlite-connection-lifecycle.md` | 2026-03-06 |

## httpx Timeout Configuration Research (Task #460)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx official docs â€” Timeouts | <https://www.python-httpx.org/advanced/timeouts/> | BSD-3 | `httpx.Timeout` fine-grained config (connect/read/write/pool), default 5s, per-client vs per-request | `docs/research/httpx-timeout.md` | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/models/__init__.py> | MIT | `DEFAULT_HTTP_TIMEOUT=600`, `connect=5`, `httpx.Timeout(timeout=timeout, connect=connect)` pattern for LLM clients | `docs/research/httpx-timeout.md` | 2026-03-06 |

## Ingest DRY Refactor Research (Task #464)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Refactoring.Guru â€” Extract Method | <https://refactoring.guru/extract-method> | N/A | Canonical Extract Method refactoring pattern: replace duplicated code fragment with call to extracted method | `docs/research/ingest-dry-refactor.md` | 2026-03-06 |
| SourceMaking â€” Extract Method | <https://sourcemaking.com/refactoring/extract-method> | N/A | Independent reference for Extract Method: "Less code duplication. Replace duplicates with calls to your new method." | `docs/research/ingest-dry-refactor.md` | 2026-03-06 |

## Shutdown Event Research (Task #509)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `loop.add_signal_handler` | <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler> | PSF-2.0 | Unix-only limitation; idiomatic asyncio signal pattern | `docs/research/shutdown-event.md` | 2026-03-06 |
| Python docs â€” `signal.signal` | <https://docs.python.org/3/library/signal.html#signal.signal> | PSF-2.0 | Signal handler execution semantics; Windows signal limitations | `docs/research/shutdown-event.md` | 2026-03-06 |
| Python docs â€” `loop.call_soon_threadsafe` | <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_soon_threadsafe> | PSF-2.0 | "safe to be called from a reentrant context or signal handler"; thread-safe scheduling | `docs/research/shutdown-event.md` | 2026-03-06 |
| Python docs â€” `asyncio.Event` | <https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event> | PSF-2.0 | "Not thread-safe" caveat; `set()`/`is_set()`/`wait()` API | `docs/research/shutdown-event.md` | 2026-03-06 |

## Agent Orchestrator Research (Task #585)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ComposioHQ/agent-orchestrator | <https://github.com/ComposioHQ/agent-orchestrator> | MIT | 8-slot plugin architecture (Runtime, Agent, Workspace, Tracker, SCM, Notifier, Terminal, Lifecycle); config-driven reaction engine (eventâ†’action with retry/escalation); priority-routed notifications; 3-layer prompt builder (base + config + user rules); session lifecycle state machine (15 statuses); flat-file metadata | `docs/research/agent-orchestrator.md` (analysis) | 2026-03-06 |

## Axon Code Intelligence Research (Task #586)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| harshkedia177/axon v0.2.4 | <https://github.com/harshkedia177/axon> | MIT | Code knowledge graph engine: 12-phase ingestion pipeline, KuzuDB storage with StorageBackend Protocol, hybrid search (BM25+vector+fuzzy via RRF), MCP server with next-step hint pattern, watch mode with tiered re-indexing, community detection (Leiden), execution flow tracing, impact analysis, dead code detection, change coupling | `docs/research/axon-code-intelligence.md` (analysis) | 2026-03-06 |
| Aider RepoMap | <https://aider.chat/docs/repomap.html> | Apache-2.0 | tree-sitter code structure graphs, token-budgeted context selection for LLMs, graph ranking for relevance optimization | `docs/research/axon-code-intelligence.md` (comparison) | 2026-03-06 |

## nWave Multi-Agent Research (Task #589)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave-ai/nWave | <https://github.com/nWave-ai/nWave> | MIT | Wave-based multi-agent pipeline (23 agents), DES enforcement hooks (PreToolUse/PostToolUse/SubagentStop), rigor profiles (lean/standard/thorough/exhaustive), reviewer pairing pattern, stale execution detection, turn limits per task type, hexagonal architecture in enforcement layer, skill-loading-per-phase pattern | `docs/research/nwave.md` (analysis) | 2026-03-06 |
| CrewAI Crews docs | <https://docs.crewai.com/concepts/crews> | N/A | Hierarchical process (manager agent), sequential/async execution, step_callback/task_callback hooks, planning LLM, knowledge sources at crew level | `docs/research/nwave.md` (comparison) | 2026-03-06 |

## OpenClaw Skills Ecosystem Research (Task #590)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw main repo | <https://github.com/openclaw/openclaw> | MIT | Heartbeat proactive agent loop (30m timer, `HEARTBEAT.md` self-updating checklist, `HEARTBEAT_OK` suppression), hooks system (13 event types, bundled session-memory/boot-md hooks), cron scheduler (isolated sessions, retry policy), skills framework (SKILL.md format, gating, ClawHub registry), AGENTS.md repo guidelines, coding-agent delegation pattern | `docs/research/openclaw-skills.md` (analysis) | 2026-03-06 |
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | N/A | Periodic agent self-initiation: configurable interval, active hours, per-agent config, lightweight bootstrap context, manual wake via system events | `docs/research/openclaw-skills.md` (heartbeat pattern) | 2026-03-06 |
| OpenClaw Hooks docs | <https://docs.openclaw.ai/gateway/hooks> | N/A | Event-driven hook system: 13 event types, directory-based discovery, bundled hooks (session-memory saves context on reset, boot-md runs startup instructions) | `docs/research/openclaw-skills.md` (hook comparison) | 2026-03-06 |
| OpenClaw Cron docs | <https://docs.openclaw.ai/gateway/cron-jobs> | N/A | Built-in scheduler: main vs isolated sessions, persistent job store, delivery modes, retry with transient/permanent error classification | `docs/research/openclaw-skills.md` (cron analysis) | 2026-03-06 |
| OpenClaw Browser docs | <https://docs.openclaw.ai/tools/browser-use> | N/A | CDP + Playwright browser control: managed profile isolation, AI/role snapshot system with numeric refs, SSRF guards, multi-profile support | `docs/research/openclaw-skills.md` (browser comparison) | 2026-03-06 |
| OpenClaw Skills docs | <https://docs.openclaw.ai/tools/skills> | N/A | AgentSkills-compatible SKILL.md format: YAML frontmatter gating (bins, env, config, OS), bundled/managed/workspace discovery, ClawHub registry | `docs/research/openclaw-skills.md` (skills framework) | 2026-03-06 |
| OpenClaw Lobster workflow shell | <https://github.com/openclaw/lobster> | MIT | Typed JSON-first pipelines, approval gates, step dependencies (`stdin: $stepId.stdout`), `openclaw.invoke` tool shim â€” evaluated and rejected (YAGNI) | `docs/research/openclaw-skills.md` (workflow comparison) | 2026-03-06 |

## Excalidraw MCP App Server Research (Task #594)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | MIT | MCP Apps architecture (toolâ†’resourceâ†’iframe), tool visibility scoping (`_meta.ui.visibility`), cheat-sheet companion tool pattern (`read_me`), checkpoint store with ID validation + path-traversal guard, dual-transport factory (`createServer()` for stateless HTTP and stdio) | `docs/research/excalidraw-mcp.md` | 2026-03-06 |
| MCP Apps extension spec | <https://modelcontextprotocol.io/docs/extensions/apps> | N/A | MCP Apps protocol: tool declares `_meta.ui.resourceUri`, host renders sandboxed iframe, bidirectional postMessage communication, CSP policy, supported clients (Claude, VS Code, ChatGPT, Goose) | `docs/research/excalidraw-mcp.md` | 2026-03-06 |
| ext-apps SDK repo | <https://github.com/modelcontextprotocol/ext-apps> | Apache-2.0 | SDK packages (`/server`, `/react`, `/app-bridge`), 20+ example servers, Python example servers (`qr-server`, `say-server`), agent skills for scaffolding MCP Apps | `docs/research/excalidraw-mcp.md` | 2026-03-06 |

## EdgeQuake Graph-RAG Research (Task #597)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| raphaelmansuy/edgequake | <https://github.com/raphaelmansuy/edgequake> | Apache-2.0 | Rust LightRAG implementation: tuple-based entity extraction, cooperative pipeline cancellation (CancellationToken), resilient partial-failure processing, per-operation LLM cost tracking (ModelPricing/OperationCost), entity normalization (UPPERCASE_UNDERSCORE, 36-40% dedup), gleaning multi-pass extraction (+18-25% recall), document lineage, 6 query modes, MCP agent integration server, MCP tool-registration pattern, MCP prompt templates, models.toml config, auto-discovery client bootstrap, orphaned task recovery on startup, smart mock provider convention, doc-traceability validator | `docs/research/edgequake.md` | 2026-03-06 |
| LightRAG paper (Guo et al. 2024) | <https://arxiv.org/abs/2410.05779> | N/A | Original LightRAG algorithm: entity extraction â†’ knowledge graph â†’ dual-level retrieval (local entity + global community). EdgeQuake implements this in Rust. | `docs/research/edgequake.md` (algorithm reference) | 2026-03-06 |

## PinchTab Browser Control Research (Task #595)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pinchtab/pinchtab | <https://github.com/pinchtab/pinchtab> | MIT | Accessibility-tree snapshot approach (stable element refs, token-efficient extraction), semantic element matching (combined lexical + hashing embedder), intent cache + stale-ref self-healing recovery, tiered token-cost model (text ~800, interactive ~3600, full ~10500), single-tool MCP plugin design, SKILL.md + TRUST.md security model pattern, pluggable strategy registry with factory + OrchestratorAware injection, auto-restart with exponential backoff | `docs/research/pinchtab.md` | 2026-03-06 |

## ChannelPlugin Protocol Extension Research (Task #482)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 544 â€” Protocols: Structural subtyping | <https://peps.python.org/pep-0544/> | N/A | Protocol default method bodies, Protocol inheritance, `runtime_checkable` semantics, structural vs nominal subtyping interaction | `docs/research/channel-protocol-extension.md` | 2026-03-06 |
| mypy Protocol documentation | <https://mypy.readthedocs.io/en/stable/protocols.html> | N/A | Default implementations in Protocols, mixin usage with Protocols, explicit vs structural conformance | `docs/research/channel-protocol-extension.md` | 2026-03-06 |

## Typed Hook Payloads Research (Task #483) — Supplemental

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python TypedDict spec | <https://typing.python.org/en/latest/spec/typeddict.html> | N/A | TypedDict inheritance, Required/NotRequired, ReadOnly, structural subtyping rules for event payload typing | `docs/research/typed-hook-payloads.md` | 2026-03-06 |
| Python typing docs (TypedDict) | <https://docs.python.org/3/library/typing.html#typing.TypedDict> | PSF | Class-based and functional syntax, runtime behavior, optional fields | `docs/research/typed-hook-payloads.md` | 2026-03-06 |
| Pluggy (pytest hook system) | <https://github.com/pytest-dev/pluggy> | MIT | TypedDict for hook options (HookspecOpts, HookimplOpts), Protocol-based typed hookspecs, `**kwargs: object` calling convention | `docs/research/typed-hook-payloads.md` | 2026-03-06 |

## ReDoS Protection Research (Task #496)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP ReDoS | <https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS> | CC BY-SA 4.0 | Evil regex patterns (nested quantifiers, overlapping alternation), NFA backtracking attack mechanics | `docs/research/redos-protection.md` | 2026-03-06 |
| Google RE2 | <https://github.com/google/re2> | BSD-3 | Linear-time regex engine, safety-first design, no backtracking by construction | `docs/research/redos-protection.md` (comparison) | 2026-03-06 |
| `google-re2` PyPI | <https://pypi.org/project/google-re2/> | BSD-3 | Python bindings for RE2, API compatibility notes, PCRE feature gaps | `docs/research/redos-protection.md` (comparison) | 2026-03-06 |
| `regex` PyPI (mrab-regex) | <https://pypi.org/project/regex/> | Apache-2.0 | Drop-in `re` replacement with native `timeout` parameter on match/search/sub, C-level timeout checking | `docs/research/redos-protection.md` (recommended approach) | 2026-03-06 |

## Qdrant Batch Retrieve Research (Task #506)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Qdrant Points docs | <https://qdrant.tech/documentation/concepts/points/#retrieve-points> | Apache-2.0 | Batch retrieve by IDs: `POST /collections/{name}/points` with `"ids": [0, 3, 100]` | Task #506 body (feasibility validation) | 2026-03-06 |

## Circuit Breaker Research (Task #515)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pybreaker | <https://github.com/danielfm/pybreaker> | BSD-3 | Circuit breaker pattern implementation: `fail_max`, `reset_timeout`, `success_threshold`, `exclude` list, `CircuitBreakerListener`, Redis backing, state management API | `docs/research/circuit-breaker.md` | 2026-03-06 |
| aiobreaker | <https://github.com/arlyon/aiobreaker> | BSD-3 | Asyncio fork of pybreaker: native async decorator, `timedelta`-based timeout | `docs/research/circuit-breaker.md` | 2026-03-06 |
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | Apache-2.0 | Custom stop/retry/wait callbacks; `RetryCallState` for state inspection; `AsyncRetrying` for async retry blocks | `docs/research/circuit-breaker.md` | 2026-03-06 |
| Circuit Breaker pattern (Nygard) | <https://microservices.io/patterns/reliability/circuit-breaker.html> | â€” | Canonical pattern: closed â†’ open (after N failures) â†’ half-open (after timeout) â†’ closed (on success) / open (on failure) | `docs/research/circuit-breaker.md` | 2026-03-06 |
| qdrant-client Python API | <https://python-client.qdrant.tech/qdrant_client.qdrant_client> | Apache-2.0 | `retrieve(collection_name, ids=Sequence[int\|str\|UUID], with_payload=True)` accepts list of IDs natively | Task #506 body (API confirmation) | 2026-03-06 |

## httpx AsyncClient Reuse Research (Task #507)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx docs â€” Clients | <https://www.python-httpx.org/advanced/clients/> | BSD-3 | Connection pooling benefits, client reuse pattern, `base_url` config, `.close()` explicit cleanup | `docs/research/httpx-client-reuse.md` | 2026-03-06 |
| httpx docs â€” Async Support | <https://www.python-httpx.org/async/#opening-and-closing-clients> | BSD-3 | `AsyncClient` lifecycle: `async with` vs `await client.aclose()`, warning against instantiating multiple clients in hot loops | `docs/research/httpx-client-reuse.md` | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai> (models/__init__.py) | MIT | `@cache`-based client singleton per provider, `is_closed` guard, `Timeout(600, connect=5)` defaults | `docs/research/httpx-client-reuse.md` | 2026-03-06 |

## OpenClaw Ecosystem & Skills Epic Synthesis (Task #581)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenHands SDK | <https://github.com/OpenHands/OpenHands> | MIT | Skill system (3 types: repo/keyword/task trigger), condenser architecture (rolling-window LLM summarization with threshold detection), microagent concept, AGENTS.md conventions | `docs/research/openclaw-ecosystem.md` (cross-system comparison) | 2026-03-07 |
| OpenHands Skill docs | <https://docs.openhands.dev/sdk/arch/skill> | N/A | Trigger-based skill activation (always/keyword/task), MCP tool embedding in skills, markdown+frontmatter format, `.cursorrules` compat | `docs/research/openclaw-ecosystem.md` (skill comparison) | 2026-03-07 |
| OpenHands Condenser docs | <https://docs.openhands.dev/sdk/arch/condenser> | N/A | LLMSummarizingCondenser: rolling window (keep head+tail, summarize middle), threshold detection, pipeline chaining, condensation events with forgotten_event_ids | `docs/research/openclaw-ecosystem.md` (condenser pattern) | 2026-03-07 |
| SWE-agent | <https://github.com/SWE-agent/SWE-agent> | MIT | RetryAgentConfig (meta-agent with multiple configs), max_requeries=3 for format/block/syntax errors, YAML tool bundles, history processors | `docs/research/openclaw-ecosystem.md` (retry comparison) | 2026-03-07 |
| SWE-agent config docs | <https://swe-agent.com/latest/reference/agent_config/> | N/A | Agent config Pydantic models (DefaultAgentConfig, RetryAgentConfig, ShellAgentConfig), tool config, history processors, action samplers | `docs/research/openclaw-ecosystem.md` (self-correction patterns) | 2026-03-07 |

## Hook Protocol Research (Task #564)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pluggy docs (v1.6) | <https://pluggy.readthedocs.io/en/stable/> | MIT | Marker-based hook detection, PluginManager.register() auto-discovery, hookspec/hookimpl decorators; designed for external plugin ecosystems (1400+ pytest plugins), not internal wiring | `docs/research/hook-protocol.md` | 2026-03-07 |
| blinker docs (v1.9) | <https://blinker.readthedocs.io/en/stable/> | MIT | Named signal pattern, signal.connect() explicit registration, no auto-discovery; anonymous signals as class attributes | `docs/research/hook-protocol.md` | 2026-03-07 |
| Django signals docs (v5.1) | <https://docs.djangoproject.com/en/5.1/topics/signals/> | BSD-3 | Signal.connect() explicit registration; warning: "signals give the appearance of loose coupling, but they can quickly lead to code that is hard to understand" â€” prefer direct calls for internal code | `docs/research/hook-protocol.md` | 2026-03-07 |

## pyttsx3 Maintenance & TTS Alternatives Research (Task #570)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pyttsx3 PyPI (release history) | <https://pypi.org/project/pyttsx3/#history> | MIT | Release cadence: v2.92-2.99 (Sep 2024 - Jul 2025); project no longer dormant | `docs/research/pyttsx3-tts-alternatives.md` | 2026-03-07 |
| pyttsx3 GitHub issues | <https://github.com/nateshmbhat/pyttsx3/issues> | MIT | 74 open issues; macOS NSSpeechSynthesizer deprecated (#347); run-loop bugs | `docs/research/pyttsx3-tts-alternatives.md` | 2026-03-07 |
| edge-tts PyPI & GitHub | <https://pypi.org/project/edge-tts/> | GPL-3.0 | v7.2.7 (Dec 2025); 10.2k stars; online neural TTS; async-native; requires network | `docs/research/pyttsx3-tts-alternatives.md` | 2026-03-07 |
| pyttsx4 PyPI | <https://pypi.org/project/pyttsx4/> | MIT | v3.0.15 (Jun 2023); stale fork of pyttsx3; not viable | `docs/research/pyttsx3-tts-alternatives.md` | 2026-03-07 |
| Coqui TTS PyPI | <https://pypi.org/project/TTS/> | MPL-2.0 | v0.22.0 (Dec 2023); heavy ML framework; Python <3.12 only; overkill | `docs/research/pyttsx3-tts-alternatives.md` | 2026-03-07 |

## DiagramService Kroki HTTP API Research (Task #617)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kroki docs â€” Usage | <https://docs.kroki.io/kroki/setup/usage/> | MIT | POST API contract: text/JSON formats, no encoding needed for POST | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| Kroki docs â€” HTTP Clients | <https://docs.kroki.io/kroki/setup/http-clients/> | MIT | cURL/HTTPie request examples, Content-Type patterns | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| yuzutech/kroki DiagramHandler.java | <https://github.com/yuzutech/kroki> | MIT | Error handling: BadRequestException codes, empty body/source validation, UnsupportedFormatException | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| Kroki docs â€” Install | <https://docs.kroki.io/kroki/setup/install/> | MIT | Core vs companion container diagram type availability | `docs/research/diagram-service-kroki.md` | 2026-03-07 |

## HeartbeatRunner Test Coverage Research (Task #638)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python unittest.mock docs | <https://docs.python.org/3/library/unittest.mock.html> | PSF | AsyncMock, side_effect, assert_awaited patterns for async test prior art | `docs/research/heartbeat-tests.md` | 2026-03-09 |
| PydanticAI test_agent.py | <https://github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py> | MIT | Agent test patterns: AsyncMock, behavior-based assertions | `docs/research/heartbeat-tests.md` | 2026-03-09 |

## Task-Level Retry Research (Task #625)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Symphony SPEC.md (via prior research) | `docs/research/symphony.md` S3.2 | N/A | Task-level exponential backoff formula `min(10s * 2^(n-1), max)`, continuation turns after success, retry scheduling in poll-dispatch loop | `docs/research/task-level-retry.md` | 2026-03-07 |
| AWS Builders' Library â€” Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | N/A | Single retry layer per stack level, multiplicative retry anti-pattern (3^5 = 243x), full jitter recommendation for distributed backoff | `docs/research/task-level-retry.md` | 2026-03-07 |
| Celery task retry docs | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | BSD-3 | `autoretry_for`, `retry_backoff=True` (1s base, 2x growth), `retry_backoff_max=600s`, `retry_jitter=True`, `max_retries=3` default, `MaxRetriesExceededError` on exhaustion | `docs/research/task-level-retry.md` | 2026-03-07 |

## Planner Agent: Board Reading + Wave Planning (Task #680)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen SelectorGroupChat + PlanningAgent | <https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | Dedicated PlanningAgent pattern: breaks tasks, assigns to specialists, checks progress; separation of planning from execution | `docs/research/planner-agent.md` | 2026-03-08 |
| CrewAI AgentPlanner | <https://docs.crewai.com/concepts/planning> | Apache-2.0 | Separate LLM planning call before crew execution; `planning=True` injects step-by-step plan into task descriptions | `docs/research/planner-agent.md` | 2026-03-08 |
| Conductor DAG + topological dispatch | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | DAG construction â†’ topological sort â†’ wave dispatch pattern (re-examined for planner output contract design) | `docs/research/planner-agent.md` | 2026-03-08 |

## Test-Writer Agent Research (Task #683)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AgentCoder (Huang et al., 2024) | <https://arxiv.org/abs/2312.13010> | CC-BY-4.0 | 3-agent framework (programmer, test designer, test executor); independent test generation achieves 87.8% accuracy vs 61% single-agent; RQ6 empirical evidence for separation | `docs/research/test-writer-agent.md` | 2026-03-08 |
| ChatDev (Qian et al., 2024) | <https://arxiv.org/abs/2307.07924> | arXiv | 7-agent pipeline with tester role; tests-after-coding approach (less adversarial) | `docs/research/test-writer-agent.md` | 2026-03-08 |
| MetaGPT (Hong et al., 2024) | <https://arxiv.org/abs/2308.00352> | CC-BY-4.0 | Assembly-line with QA engineer; 79% test accuracy baseline for comparison | `docs/research/test-writer-agent.md` | 2026-03-08 |
| Uncle Bob â€” The Cycles of TDD | <https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html> | Blog | Red/Green/Refactor theory; Three Laws of TDD; natural agent-role mapping | `docs/research/test-writer-agent.md` | 2026-03-08 |
| Self-Collaboration (Dong et al., 2023) | <https://arxiv.org/abs/2304.07590> | arXiv | analyst-coder-tester multi-role pattern; LLM prediction vs execution distinction | `docs/research/test-writer-agent.md` | 2026-03-08 |

## Evaluator Agent Research (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Explicit Evaluator (M_e) scoring Actor output; separate Self-Reflection (M_sr) generating verbal feedback; binary reward signal triggering retry | `docs/research/evaluator-agent.md` | 2026-03-08 |
| LATS (Zhou et al., 2023) | <https://arxiv.org/abs/2310.04406> | CC-BY-4.0 | LM-powered value function evaluating node quality; routing search decisions (expand/backtrack/select); reasoned scores | `docs/research/evaluator-agent.md` | 2026-03-08 |
| Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Planâ†’EvalPlanâ†’Executeâ†’EvalExecâ†’Fix cycle (max 3); structured eval-then-fix pattern | `docs/research/evaluator-agent.md` | 2026-03-08 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | Model-based routing with custom selector/candidate functions; next-speaker selection pattern | `docs/research/evaluator-agent.md` | 2026-03-08 |

## Inter-Agent Communication Protocol (Task #684)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Agent Supervisor blog | <https://blog.langchain.com/langgraph-multi-agent-workflows/> | CC-BY-4.0 | Independent scratchpads per agent; only final responses to supervisor; shared vs independent scratchpad trade-offs | `docs/research/inter-agent-communication-protocol.md` | 2026-03-08 |
| OpenAI Swarm | <https://github.com/openai/swarm> | MIT | `Result(value, agent, context_variables)` â€” explicit separation of routing return value vs shared state | `docs/research/inter-agent-communication-protocol.md` | 2026-03-08 |
| Blackboard design pattern (Wikipedia) | <https://en.wikipedia.org/wiki/Blackboard_(design_pattern)> | CC-BY-SA-4.0 | Structured global memory + selective reading by control component; knowledge source independence | `docs/research/inter-agent-communication-protocol.md` | 2026-03-08 |
| CrewAI Collaboration docs | <https://docs.crewai.com/concepts/collaboration> | Apache-2.0 | Task `context=[previous_task]` chain; lead agent sees delegation results only; hierarchical collaboration pattern | `docs/research/inter-agent-communication-protocol.md` | 2026-03-08 |

## Task Decomposition Rules (Task #685)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ChatDev (Qian et al., ACL 2024) | <https://arxiv.org/abs/2307.07924> | arXiv non-exclusive | Chat chain phase-scoped subtask decomposition; single-concern per subtask pair | `docs/research/task-decomposition-rules.md` | 2026-03-08 |
| MetaGPT (Hong et al., ICLR 2024) | <https://arxiv.org/abs/2308.00352> | MIT | SOP-driven decomposition; assembly-line paradigm with intermediate verification | `docs/research/task-decomposition-rules.md` | 2026-03-08 |
| OpenHands agent delegation | <https://github.com/All-Hands-AI/OpenHands> | MIT | Subtask/delegation hierarchy; bounded scope per agent conversation | `docs/research/task-decomposition-rules.md` | 2026-03-08 |
| Fowler â€” Bounded Context (DDD) | <https://martinfowler.com/bliki/BoundedContext.html> | Blog | Domain boundaries by model/language differences; explicit integration points | `docs/research/task-decomposition-rules.md` | 2026-03-08 |

## Instruction Token Audit (Task #686)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Liu et al. "Lost in the Middle" (2023) | <https://arxiv.org/abs/2307.03172> | arXiv | Performance degrades with context length; middle-positioned info systematically missed | `docs/research/instruction-token-audit.md` | 2026-03-08 |
| Li et al. "Long-context LLMs Struggle" (2024) | <https://arxiv.org/abs/2404.02060> | arXiv | Classification accuracy drops as in-context examples/instructions grow | `docs/research/instruction-token-audit.md` | 2026-03-08 |
| Anthropic Prompt Engineering Best Practices | <https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct> | N/A | Conciseness, long-context structuring, queries-at-end boosts quality 30% | `docs/research/instruction-token-audit.md` | 2026-03-08 |
| OpenAI Prompt Engineering Guide | <https://developers.openai.com/api/docs/guides/prompt-engineering> | N/A | Clear sections, minimal context, prompt caching for repeated prefixes | `docs/research/instruction-token-audit.md` | 2026-03-08 |

## Stripe Minions Agentic Toolchain (Task #647)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Stripe Minions Part 1 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents> | N/A (blog) | Unattended one-shot agent UX, Slack/CLI entry points, shift-left feedback, max 2 CI rounds | `docs/research/stripe-minions.md` | 2026-03-08 |
| Stripe Minions Part 2 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | N/A (blog) | Blueprints (hybrid workflow+agent), devboxes, Toolshed MCP registry, scoped rule files, context pre-hydration | `docs/research/stripe-minions.md` | 2026-03-08 |
| Anthropic â€” Building Effective Agents | <https://www.anthropic.com/engineering/building-effective-agents> | N/A (blog) | Workflows vs agents taxonomy, orchestrator-workers pattern, tool prompt engineering | `docs/research/stripe-minions.md` | 2026-03-08 |

## GCP Always-On Memory Agent (Task #700)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP always-on-memory-agent | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent> | MIT | Always-on memory pattern, consolidation loop, importance scoring, ADK agent orchestration | `docs/research/gcp-always-on-memory-agent.md` | 2026-03-09 |
| Mem0 (mem0ai/mem0) | <https://github.com/mem0ai/mem0> | Apache-2.0 | Persistent agent memory layer, LLM-extracted facts, multi-level memory (user/session/agent) | `docs/research/gcp-always-on-memory-agent.md` | 2026-03-09 |

## Always-On Memory Integration (Task #701)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP always-on-memory-agent research (#700) | `docs/research/gcp-always-on-memory-agent.md` | N/A (internal) | Consolidation pattern, importance scoring, component mapping | `docs/research/always-on-memory-integration.md` | 2026-03-09 |
| Mem0 architecture | <https://github.com/mem0ai/mem0> | Apache-2.0 | Multi-level memory, LLM-extracted structured facts, hybrid search | `docs/research/always-on-memory-integration.md` | 2026-03-09 |
| OwlBear context-aware injection research | `docs/research/context-aware-knowledge-injection.md` | N/A (internal) | Hybrid auto-inject + tool-based RAG pattern | `docs/research/always-on-memory-integration.md` | 2026-03-09 |
| OwlBear MemoryConsolidator research (#485) | `docs/research/memory-consolidator.md` | N/A (internal) | Session consolidation YAGNI precedent | `docs/research/always-on-memory-integration.md` | 2026-03-09 |
| Generative Agents (Park et al.) | <https://arxiv.org/abs/2304.03442> | N/A (paper) | Recency × relevance × importance retrieval scoring | `docs/research/always-on-memory-integration.md` | 2026-03-09 |

## GCP generative-ai Repo Audit (Task #702)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP agents/genai-experience-concierge | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/genai-experience-concierge> | Apache-2.0 | Guardrail classifier, semantic router, task planner design patterns (LangGraph) | `docs/research/gcp-generative-ai-audit.md` | 2026-03-09 |
| GCP evaluation/evaluating_adk_agent | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/evaluation> | Apache-2.0 | ADK agent evaluation, trajectory_single_tool_use metric, behavioral eval dataset design | `docs/research/gcp-generative-ai-audit.md`, `tests/benchmarks/tool_eval.py` | 2026-03-09 |
| GCP use-cases/graphrag | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/use-cases/graphrag> | Apache-2.0 | Agentic GraphRAG with Neo4j + ADK, multi-hop graph traversal | `docs/research/gcp-generative-ai-audit.md` | 2026-03-09 |

## Cheat-Sheet Tool Pattern Research (Task #718)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | Evolved `read_diagram_guide` tool pattern (26 tools), skill with cheatsheet.md, design quality guidance for AI-generated diagrams | `docs/research/cheat-sheet-tool-pattern.md` | 2026-07-27 |
| PMCP (ViperJuice/pmcp) | <https://github.com/ViperJuice/pmcp> | MIT | L0-L3 progressive disclosure layers, 80% token reduction, 14 meta-tools instead of 50+, meta-gateway pattern | `docs/research/cheat-sheet-tool-pattern.md` | 2026-07-27 |

## Untrusted Content Wrapping Research (Task #725)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/content.go> | MIT | Content wrapping implementation: `<untrusted_web_content>` delimiters + advisory text | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |
| Simon Willison, "Delimiters won't save you" | <https://simonwillison.net/2023/May/11/delimiters-wont-save-you/> | CC-BY | Limits of delimiter-based prompt injection defense | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |
| Simon Willison, "Limit the blast radius" | <https://simonwillison.net/2023/Dec/20/mitigate-prompt-injection/> | CC-BY | Defense-in-depth framing for IDPI mitigation | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |
| Greshake et al., "Indirect Prompt Injection" | <https://arxiv.org/abs/2302.12173> | arXiv | IDPI threat taxonomy: data theft, worming, ecosystem contamination | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |

## IDPI Content Scanning Research (Task #724)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/content.go> | MIT | 26 builtin injection patterns, ScanContent function, CheckResult struct, strict/warn modes | `docs/research/idpi-content-scanning.md` | 2026-03-10 |
| PinchTab `internal/idpi/idpi_test.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/idpi_test.go> | MIT | Test patterns for content scanning, edge cases, case-insensitivity | `docs/research/idpi-content-scanning.md` | 2026-03-10 |
| ProtectAI/llm-guard | <https://github.com/protectai/llm-guard> | MIT | BanSubstrings scanner (pattern-based), PromptInjection scanner (ML-based DeBERTa) | `docs/research/idpi-content-scanning.md` | 2026-03-10 |
| ProtectAI/rebuff (archived) | <https://github.com/protectai/rebuff> | Apache-2.0 | Multi-layer PI defense: heuristics + LLM + VectorDB + canary tokens | `docs/research/idpi-content-scanning.md` | 2026-03-10 |
| OWASP LLM01:2025 Prompt Injection | <https://genai.owasp.org/llmrisk/llm01-prompt-injection/> | CC-BY-SA-4.0 | Prevention strategies #3 (string-checking content scanning) and #6 (segregate external content) | `docs/research/idpi-content-scanning.md` | 2026-03-10 |

## Accessibility-Tree Snapshot Research (Task #726)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Playwright ARIA Snapshots docs | <https://playwright.dev/python/docs/aria-snapshots> | Apache-2.0 | Modern `locator.aria_snapshot()` API (YAML output), replacement for deprecated `page.accessibility.snapshot()` | `docs/research/a11y-snapshot.md` | 2026-07-08 |
| CDP Accessibility domain spec | <https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/> | BSD-3 | `getFullAXTree` method, `AXNode` type (backendDOMNodeId, role, name, properties), filter properties | `docs/research/a11y-snapshot.md` | 2026-07-08 |
| browser-use `DomService` | <https://github.com/browser-use/browser-use> (`browser_use/dom/service.py`) | MIT | CDP-based AX tree extraction pattern, `_get_ax_tree_for_all_frames()`, `EnhancedAXNode` model, backendDOMNodeId lookup | `docs/research/a11y-snapshot.md` | 2026-07-08 |

## IDPI Content Scanning Implementation (Task #724)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/content.go> | MIT | Injection pattern list and `ScanContent` function ported to Python (`ContentInjectionGuard`, `CheckResult`, strict/warn/off modes) | `src/owlbear/tools/browser/content_guard.py` | 2026-03-11 |

## Untrusted Content Wrapping (Tasks #725/#730/#735)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/content.go> | MIT | Content wrapping pattern with sentinel tags and advisory preamble | `src/owlbear/core/content_safety.py`, `serve/knowledge/src/owlbear_knowledge/content_safety.py` | 2026-03-10 |
| Willison, "Delimiters won't save you" (2023) | <https://simonwillison.net/2023/May/11/delimiters-wont-save-you/> | Blog | Established limits of delimiter approach — informed defense-in-depth framing | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |
| Greshake et al., "Indirect Prompt Injection" (2023) | <https://arxiv.org/abs/2302.12173> | CC-BY-4.0 | Threat model taxonomy for LLM-integrated apps, IDPI attack vectors | `docs/research/untrusted-content-wrapping.md` | 2026-03-10 |

## IDPI ContentInjectionGuard at Graph Entry (Task #834)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PinchTab idpishield `patterns/builtin.go` | <https://github.com/pinchtab/idpishield/blob/main/patterns/builtin.go> | Apache-2.0 | 100+ regex patterns across 12 categories — adapted to ~40 substring patterns for knowledge guard | `.owlbear/research/834-contentinjectionguard-green-impl.md` | 2026-04-12 |
| OWASP LLM01:2025 Prompt Injection | <https://genai.owasp.org/llmrisk/llm01-prompt-injection/> | CC-BY-SA-4.0 | Strategy #3 (string-checking) and #6 (segregate content) as authoritative mitigation guidance | `.owlbear/research/834-contentinjectionguard-green-impl.md` | 2026-04-12 |

## claude-context-mode Evaluation (Task #745)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| mksglu/claude-context-mode v1.0.18 | <https://github.com/mksglu/claude-context-mode> | Elastic-2.0 | Sandbox execution, FTS5 knowledge base, smart truncation (line-boundary snapping), session event capture/snapshot, exit classification, progressive throttling | `docs/research/claude-context-mode.md` | 2026-03-12 |

## owlbear.tools Lazy-Export RED Coverage (Task #878)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python import system docs | <https://docs.python.org/3/reference/import.html> | PSF | Package `__init__.py` execution model; explains why bare `import owlbear.tools` runs all package-root imports and why a clean subprocess is needed to verify side effects | `docs/research/tools-root-lazy-exports-red-coverage.md`, `tests/test_tools_init_reexports.py` | 2026-03-20 |
| Python data model docs | <https://docs.python.org/3/reference/datamodel.html> | PSF | Module-level `__getattr__` and `__dir__` hooks — the supported extension points for lazy package-root attribute access | `docs/research/tools-root-lazy-exports-red-coverage.md` | 2026-03-20 |
| PEP 562 — Module `__getattr__` and `__dir__` | <https://peps.python.org/pep-0562/> | PSF | Established that `from pkg import Name` is compatible with module-level `__getattr__`; informed the decision to keep API-preservation tests behaviour-focused rather than implementation-focused | `docs/research/tools-root-lazy-exports-red-coverage.md` | 2026-03-20 |
| Scientific Python SPEC 1 — Lazy Loading of Submodules | <https://scientific-python.org/specs/spec-0001/> | BSD | Lazy-export pattern reference; informed the decision to keep the RED task narrowly scoped without over-specifying non-essential ergonomics | `docs/research/tools-root-lazy-exports-red-coverage.md` | 2026-03-20 |

## owlbear.tools Lazy-Export GREEN Implementation (Task #879)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| `lazy-loader` project docs | <https://github.com/scientific-python/lazy_loader> | BSD | Helper-based lazy loading is viable but introduces a runtime dependency and optional type-stub packaging concerns; confirmed that an inline `__getattr__` map is the right fit for a 10-name surface with no new dependencies | `docs/research/tools-root-lazy-exports-implementation.md` | 2026-03-20 |

## Package-Root Lazy-Export Architecture Note (Task #882)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python data model docs | <https://docs.python.org/3/reference/datamodel.html#customizing-module-attribute-access> | PSF | Canonical module-level `__getattr__` and `__dir__` semantics for package-root lazy exports | `docs/research/package-root-lazy-export-pattern.md` | 2026-03-21 |
| PEP 562 - Module `__getattr__` and `__dir__` | <https://peps.python.org/pep-0562/> | PSF | Standard lazy module-attribute pattern; supports cached access after first lookup and compatibility with `from pkg import Name` | `docs/research/package-root-lazy-export-pattern.md` | 2026-03-21 |
| PEP 8 - Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | PSF | `__all__` defines the supported public API surface and imported names remain implementation details | `docs/research/package-root-lazy-export-pattern.md` | 2026-03-21 |
| Scientific Python SPEC 1 - Lazy Loading of Submodules | <https://scientific-python.org/specs/spec-0001/> | BSD | Lazy loading is valid but should not be applied indiscriminately; small package roots should avoid extra machinery | `docs/research/package-root-lazy-export-pattern.md` | 2026-03-21 |
| `lazy-loader` project docs | <https://github.com/scientific-python/lazy_loader> | BSD | Helper-based lazy loading adds dependency and stub-management overhead; informed the decision to keep OwlBear's small package-root surfaces inline | `docs/research/package-root-lazy-export-pattern.md` | 2026-03-21 |

## owlbear.tools `dir()` Parity Follow-up (Task #883)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python data model docs | <https://docs.python.org/3/reference/datamodel.html#customizing-module-attribute-access> | PSF | Canonical module-level `__dir__` semantics for dynamic package-root attributes | `docs/research/tools-root-lazy-exports-dir-parity.md` | 2026-03-21 |
| PEP 562 - Module `__getattr__` and `__dir__` | <https://peps.python.org/pep-0562/> | PSF | Standard lazy module-attribute pattern; PEP example uses a curated `__dir__` export list | `docs/research/tools-root-lazy-exports-dir-parity.md` | 2026-03-21 |
| Scientific Python SPEC 1 - Lazy Loading of Submodules | <https://scientific-python.org/specs/spec-0001/> | BSD | Lazy loading should preserve interactive exploration as well as import performance | `docs/research/tools-root-lazy-exports-dir-parity.md` | 2026-03-21 |
| `lazy-loader` implementation/docs | <https://github.com/scientific-python/lazy-loader/blob/main/src/lazy_loader/__init__.py> | BSD | Helper returns the curated `__all__` surface from `__dir__`, supporting a minimal export-only `__dir__` design | `docs/research/tools-root-lazy-exports-dir-parity.md` | 2026-03-21 |

## content_extractor Delegation RED Coverage (Task #881)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `unittest.mock` docs | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | PSF | Canonical "patch where the object is looked up" rule for delegation-focused tests | `docs/research/content-extractor-extract-markdown-delegation-red-task.md` | 2026-03-21 |
| pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | MIT | Fixture-scoped patching semantics and narrow consumer-site replacement patterns | `docs/research/content-extractor-extract-markdown-delegation-red-task.md` | 2026-03-21 |
| trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | Apache-2.0 | Public raw extract contract for markdown output, link inclusion, URL forwarding, and metadata extraction | `docs/research/content-extractor-extract-markdown-delegation-red-task.md` | 2026-03-21 |
| trafilatura GitHub repo | <https://github.com/adbar/trafilatura> | Apache-2.0 | Confirmed project license and the helper-boundary API surface already covered in `tests/test_web_extract.py` | `docs/research/content-extractor-extract-markdown-delegation-red-task.md` | 2026-03-21 |

## Context Hydration Extract Markdown Seam RED Coverage (Task #869)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `unittest.mock` docs | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | PSF | Canonical "patch where the object is looked up" rule — confirms module-local `extract_markdown` is the correct seam after helper migration | `docs/research/context-hydration-extract-markdown-red-task.md` | 2026-03-20 |
| pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | MIT | Fixture-scoped patching semantics for narrow consumer-site helper seam replacement | `docs/research/context-hydration-extract-markdown-red-task.md` | 2026-03-20 |

## Context Hydration URL Forwarding RED Coverage (Task #876)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python `unittest.mock` docs | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | PSF | Canonical "patch where the object is looked up" rule for caller-level helper forwarding tests | `docs/research/context-hydration-url-forwarding-red-task.md` | 2026-03-21 |
| pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | MIT | Fixture-scoped consumer-site patching guidance for narrow helper seams | `docs/research/context-hydration-url-forwarding-red-task.md` | 2026-03-21 |
| trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | Apache-2.0 | Public reason for forwarding `url=` alongside HTML input at the caller boundary | `docs/research/context-hydration-url-forwarding-red-task.md` | 2026-03-21 |

## Planner Placeholder-Task Rejection Rules (Task #903)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | CC BY 4.0 | Structured intake uses required fields and validation; hard rejection rules belong at input time rather than as soft prose | `.github/agents/kanban-planner.agent.md` | 2026-03-21 |
| GitHub Docs - Configuring issue templates | <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | CC BY 4.0 | `blank_issues_enabled: false` is prior art for disabling blank intake paths instead of letting placeholders through | `.github/agents/kanban-planner.agent.md` | 2026-03-21 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/ee/user/project/description_templates.html> | CC BY-SA 4.0 | Mature work trackers standardize scoped descriptions with templates or defaults rather than accepting empty work-item bodies | `.github/agents/kanban-planner.agent.md` | 2026-03-21 |

## Planner Skill Placeholder Validation (Task #904)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GitHub Docs - Syntax for issue forms | <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms> | CC BY 4.0 | Required fields and validation as intake-time controls; prior art for fail-fast placeholder checks in the decomposition workflow | `.github/skills/task-decomposition/SKILL.md` | 2026-03-22 |
| GitHub Docs - Configuring issue templates | <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository> | CC BY 4.0 | `blank_issues_enabled: false` as prior art for refusing blank intake paths instead of letting placeholder tasks reach the board | `.github/skills/task-decomposition/SKILL.md` | 2026-03-22 |
| Atlassian Support - Configure advanced work item workflows | <https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/> | N/A (docs) | Validators check transition input before the transition is performed and block invalid work-item progress | `.github/skills/task-decomposition/SKILL.md` | 2026-03-22 |
| GitLab Docs - Description templates | <https://docs.gitlab.com/ee/user/project/description_templates.html> | CC BY-SA 4.0 | Structured templates and defaults as prior art for requiring scoped task bodies instead of empty placeholders | `.github/skills/task-decomposition/SKILL.md` | 2026-03-22 |

## Operation-Scoped Cancellation Signal for Knowledge Pipelines (Task #880 / #870)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio task-cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | PSF | `Task.cancel()` injects `CancelledError`; caught cancellation must be re-raised — informs the `_run_extract` re-raise pattern | `src/owlbear/memory/knowledge/ingest.py` (`_ingest_from_intake`) | 2026-03-20 |
| AnyIO cancellation docs | <https://anyio.readthedocs.io/en/stable/cancellation.html> | MIT | Level-cancellation and cancel-scope model studied and rejected; OwlBear uses asyncio cooperative polling instead | `docs/research/operation-scoped-cancellation-signal.md` | 2026-03-20 |
| .NET cancellation-token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC BY 4.0 | One token per cancelable operation, poll at work boundaries, linked parent/child cancellation — direct prior art for the `cancel: asyncio.Event` seam | `src/owlbear/memory/knowledge/refresh.py`, `ingest.py`, `bookmark_pipeline.py`, `src/owlbear/tools/browser/integration.py`, `src/owlbear/core/retrospective_hook.py` | 2026-03-20 |

## QUESTION_PENDING Emit Implementation (Task #967)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | `before_task_publish` / `task_prerun` emit-once-per-boundary pattern used to justify single emit before human-wait | `docs/research/question-pending-emit-implementation.md` | 2026-03-23 |
| Prefect event-driven docs | <https://docs.prefect.io/v3/get-started> | N/A (docs) | Event-driven state transitions (Paused, Pending) fire once at boundary, not on every poll/retry | `docs/research/question-pending-emit-implementation.md` | 2026-03-23 |

## Frontend Instructions Skill Handoff (Task #937)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code — Custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | Always-on vs file-based instruction scoping; instructions for project standards, skills for specialized capabilities | `docs/research/frontend-instructions-skill-handoff.md` | 2026-03-24 |
| VS Code — Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Progressive loading model (discovery → instructions → resources); skills vs instructions separation rationale | `docs/research/frontend-instructions-skill-handoff.md` | 2026-03-24 |

## Frontend Anti-Pattern Taxonomy (Task #938)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pbakaus/impeccable | <https://github.com/pbakaus/impeccable> | Apache-2.0 | DO/DON'T anti-pattern catalog across 7 design categories and "AI Slop Test" framing for taste-specific heuristic classification | `docs/research/frontend-anti-pattern-taxonomy.md` | 2026-03-24 |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Baseline anti-pattern warnings and design-thinking skill framing used to distinguish universal blockers from taste heuristics | `docs/research/frontend-anti-pattern-taxonomy.md` | 2026-03-24 |
| WCAG 2.1/2.2 Understanding Docs | <https://www.w3.org/WAI/WCAG21/Understanding/> | W3C Document License | Formal success criteria backing universal blockers: SC 2.4.7 (Focus Visible), 2.4.13 (Focus Appearance), 1.4.3 (Contrast Minimum), 1.4.11 (Non-text Contrast), 2.5.5 (Target Size), 3.3.2 (Labels or Instructions) | `docs/research/frontend-anti-pattern-taxonomy.md` | 2026-03-24 |
| NNGroup "Placeholders in Form Fields Are Harmful" | <https://www.nngroup.com/articles/form-design-placeholders/> | N/A (article) | 7 documented usability harms of placeholder-as-label pattern, a11y failures for screen readers and cognitive impairments | `docs/research/frontend-anti-pattern-taxonomy.md` | 2026-03-24 |

## Council Debate System Research (Task #145)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Du et al. "Improving Factuality through Multiagent Debate" | <https://arxiv.org/abs/2305.14325> | CC-BY-4.0 | Convergent debate protocol: N agents propose, see each other's responses, K rounds, arrive at common answer (ICML 2024) | `docs/research/council-debate-system.md` | 2026-03-24 |
| Liang et al. "MAD: Multi-Agent Debate" | <https://arxiv.org/abs/2305.19118> | arXiv non-exclusive | Adversarial debate with judge; Degeneration-of-Thought problem; adaptive round termination (EMNLP 2024) | `docs/research/council-debate-system.md` | 2026-03-24 |
| Chan et al. "ChatEval" | <https://arxiv.org/abs/2308.07201> | arXiv non-exclusive | Multi-agent referee team for evaluation via debate; parallel-then-synthesize protocol variant | `docs/research/council-debate-system.md` | 2026-03-24 |
| Irving et al. "AI Safety via Debate" | <https://arxiv.org/abs/1805.00899> | arXiv non-exclusive | Foundational two-player zero-sum debate game theory; PSPACE complexity results for debate with polynomial-time judges | `docs/research/council-debate-system.md` | 2026-03-24 |
| composable-models/llm_multiagent_debate | <https://github.com/composable-models/llm_multiagent_debate> | N/A | Reference implementation of Du et al. convergent debate (516 stars, Python) | `docs/research/council-debate-system.md` | 2026-03-24 |
| Skytliang/Multi-Agents-Debate | <https://github.com/Skytliang/Multi-Agents-Debate> | GPL-3.0 | Reference implementation of Liang et al. MAD adversarial debate (539 stars, Python) | `docs/research/council-debate-system.md` | 2026-03-24 |

## Priority-Routed Notifications (Task #952)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Grafana notification policies docs | <https://grafana.com/docs/grafana/latest/alerting/configure-notifications/create-notification-policy/> | AGPL-3.0 (docs: CC-BY-SA-4.0) | Label-based routing tree with severity matching to contact points, child policy inheritance, and mute timings as prior art for priority-based notification routing | `docs/research/priority-routed-notifications.md` | 2026-03-24 |
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Trigger plus action model with notification blocks (Slack, Teams, Email) and template-driven messages as prior art for event-to-notification routing | `docs/research/priority-routed-notifications.md` | 2026-03-24 |

## SlackNotificationBackend Research (Task #978)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack SDK Web API docs | <https://docs.slack.dev/tools/python-slack-sdk/web/index.html> | N/A (docs) | `AsyncWebClient.chat_postMessage()` async pattern, `RateLimitErrorRetryHandler`, and error handling via `SlackApiError` for one-way notification delivery | `docs/research/slack-notification-backend.md` | 2026-03-24 |
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Template-driven Slack notification blocks with event context as prior art for message formatting | `docs/research/slack-notification-backend.md` | 2026-03-24 |

## Notify Dedup: NotificationHook vs HookReactionRouter (Task #963)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Prometheus AlertManager docs | <https://prometheus.io/docs/alerting/latest/alertmanager/> | Apache-2.0 (docs: CC-BY-4.0) | Routing trees, inhibition rules, grouping � single notification path per alert as prior art for assembly-time event exclusion | `docs/research/notify-dedup-notificationhook-vs-router.md` | 2026-03-24 |
| Prefect automations docs | <https://docs.prefect.io/v3/concepts/automations> | N/A (docs) | Independent trigger/action automations; no built-in dedup between automations, used as counterexample for OwlBear's single-user UX | `docs/research/notify-dedup-notificationhook-vs-router.md` | 2026-03-24 |
| Celery signals guide | <https://docs.celeryq.dev/en/stable/userguide/signals.html> | BSD-3-Clause | Independent signal handlers with no built-in dedup, used to justify explicit assembly-time exclusion over runtime tracking | `docs/research/notify-dedup-notificationhook-vs-router.md` | 2026-03-24 |

## Two-Tier Priority Notification Config (Task #977)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Grafana notification policies docs | <https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/notification-policies/> | AGPL-3.0 (docs: CC-BY-SA-4.0) | Label-based routing with contact-point inheritance and child policy override semantics as prior art for tier-based notification config | `docs/research/two-tier-notification-config.md` | 2026-03-24 |
| Pydantic deprecated fields docs | <https://docs.pydantic.dev/latest/concepts/fields/#deprecated-fields> | MIT | `Field(deprecated=...)` native deprecation mechanism emitting `DeprecationWarning` on access for backward-compatible field migration | `docs/research/two-tier-notification-config.md` | 2026-03-24 |
| Pydantic validators docs | <https://docs.pydantic.dev/latest/concepts/validators/> | MIT | `model_validator(mode='after')` for cross-field migration logic and `warnings.catch_warnings()` pattern for suppressing internal access | `docs/research/two-tier-notification-config.md` | 2026-03-24 |

## Two-Tier NotificationHook Wiring (Task #979)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Grafana notification policies docs | <https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/notification-policies/> | AGPL-3.0 (docs: CC-BY-SA-4.0) | Routing tree maps severity labels to contact points; each policy has its own receiver chain — validates two-tier wiring pattern | `docs/research/two-tier-hook-wiring.md` | 2026-03-26 |
| Python logging HOWTO — Handlers | <https://docs.python.org/3/howto/logging.html> | PSF | Different handlers per severity level: "send error+ to stdout, critical to email" — canonical two-handler-tier pattern in Python stdlib | `docs/research/two-tier-hook-wiring.md` | 2026-03-26 |

## Frontend-Polish Prompt Research (Task #946)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Impeccable `/polish` skill | <https://github.com/pbakaus/impeccable> | Apache-2.0 | 11-category polish checklist, pre-polish assessment, final verification steps, and polish-is-the-last-step constraint | `docs/research/frontend-polish-prompt.md` | 2026-03-24 |
| VS Code Prompt Files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | Frontmatter format, input syntax, file references, and prompt invocation behavior | `docs/research/frontend-polish-prompt.md` | 2026-03-24 |

## GraphEnricher Cancellation and Draining Research (Task #871)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | PSF | `Task.cancel()` + `asyncio.gather(return_exceptions=True)` as the shutdown drain pattern for background task sets | `docs/research/graphenricher-cancellation-draining.md` | 2026-03-25 |
| Python asyncio `create_task` strong-ref pattern | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | PSF | `background_tasks.add(task)` + `task.add_done_callback(background_tasks.discard)` — validates existing GraphEnricher bookkeeping | `docs/research/graphenricher-cancellation-draining.md` | 2026-03-25 |
| .NET CancellationToken docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | CC BY 4.0 | One token per cancelable operation; check before starting new work — model for per-schedule CancelSignal param | `docs/research/graphenricher-cancellation-draining.md` | 2026-03-25 |

## MCP Python SDK Deep-Dive (Task #2)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK (v1 README) | <https://github.com/modelcontextprotocol/python-sdk> | MIT | FastMCP API, decorator patterns, transport options, lifespan pattern, structured output, Context injection | `docs/research/mcp-python-sdk.md` | 2026-03-26 |
| MCP Python SDK (v2 README) | <https://github.com/modelcontextprotocol/python-sdk/blob/main/README.v2.md> | MIT | MCPServer rename, simplified Context type params, transport options moved to run() | `docs/research/mcp-python-sdk.md` | 2026-03-26 |
| MCP Architecture Overview | <https://modelcontextprotocol.io/docs/concepts/architecture> | LF Projects | Protocol layers, client-server architecture, three primitives, capability negotiation, notifications | `docs/research/mcp-python-sdk.md` | 2026-03-26 |
| MCP Lifecycle Specification | <https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle> | LF Projects | Initialization handshake, capability negotiation, shutdown sequences (stdio/HTTP), timeout handling, error cases | `docs/research/mcp-python-sdk.md` | 2026-03-26 |
| VS Code MCP Configuration Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | Microsoft | mcp.json schema, stdio/HTTP server config, input variables, dev mode, sandbox config | `docs/research/mcp-python-sdk.md` | 2026-03-26 |

## agentskills.io Spec Validation (Task #3)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| agentskills.io specification | <https://agentskills.io/specification> | Apache-2.0 | Complete skill format spec: frontmatter fields, naming constraints, directory structure, progressive disclosure, validation tooling | `docs/research/agentskills-io.md` | 2026-03-26 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | VS Code-specific extensions (user-invocable, argument-hint, disable-model-invocation), discovery paths, slash-command integration | `docs/research/agentskills-io.md` | 2026-03-26 |
| agentskills/agentskills repo | <https://github.com/agentskills/agentskills> | Apache-2.0 | Reference SDK, skills-ref validation library, spec source of truth | `docs/research/agentskills-io.md` | 2026-03-26 |
| anthropics/skills repo | <https://github.com/anthropics/skills> | Apache-2.0 | Example skills collection (100k+ stars), real-world skill patterns and directory structures | `docs/research/agentskills-io.md` | 2026-03-26 |
| Client implementation guide | <https://agentskills.io/client-implementation/adding-skills-support> | Apache-2.0 | Progressive disclosure lifecycle, discovery scanning rules, activation patterns, context management | `docs/research/agentskills-io.md` | 2026-03-26 |

## Port Skills to agentskills.io Format (Task #9)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| agentskills.io specification | <https://agentskills.io/specification> | Apache-2.0 | Validated spec unchanged since #3 research: required fields (name, description), directory structure, progressive disclosure tiers | `docs/research/port-skills-to-v2.md` | 2026-03-29 |
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Discovery paths, `chat.agentSkillsLocations` custom path config, empirical auto-loading confirmation | `docs/research/port-skills-to-v2.md` | 2026-03-29 |

## Disable Copilot Memory Research Validation (Task #48)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code settings reference — Memory settings | <https://code.visualstudio.com/docs/copilot/reference/copilot-settings> | CC-BY-4.0 | Confirmed `github.copilot.chat.copilotMemory.enabled` setting exists, default false (Preview), workspace-level supported | Task #48 body | 2026-03-26 |
| GitHub Blog — Copilot Memory now on by default | <https://github.blog/changelog/2026-03-04-copilot-memory-now-on-by-default-for-pro-and-pro-users-in-public-preview> | N/A | Copilot Memory enabled by default for Pro/Pro+ as of March 4, 2026; opt-out via settings | Task #48 body | 2026-03-26 |
| GitHub Docs — About agentic memory for Copilot | <https://docs.github.com/en/copilot/concepts/agents/copilot-memory> | CC-BY-4.0 | Memory is GitHub-hosted, repository-scoped, 28-day auto-expiry, cross-surface (coding agent, code review, CLI) | Task #48 body | 2026-03-26 |

## Voice TTS Kokoro + pyttsx3 Research (Task #51)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kokoro TTS GitHub | <https://github.com/hexgrad/kokoro> | Apache-2.0 | KPipeline generator API, Result.audio tensor @ 24kHz, voice loading, speed control, espeak-ng dependency | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |
| Kokoro PyPI | <https://pypi.org/project/kokoro/> | Apache-2.0 | v0.9.4 install, usage examples, Windows espeak-ng installation instructions | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |
| Kokoro pipeline.py source | <https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py> | Apache-2.0 | Result dataclass with .audio property, chunked generation, voice mixing, language code routing | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |
| pyttsx3 PyPI | <https://pypi.org/project/pyttsx3/> | MIT | v2.99, init/say/runAndWait API, SAPI5+espeak+nsss backends, rate/volume/voice properties | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |
| sounddevice docs | <https://python-sounddevice.readthedocs.io/en/latest/usage.html> | MIT | sd.play(array, rate) non-blocking playback, sd.wait() blocking, numpy array interface | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |
| v1 TTSEngine | `v1/src/owlbear/voice/tts.py` | N/A (internal) | Lazy pyttsx3 init, asyncio.to_thread wrapper, rate/volume config pattern | `docs/research/voice-tts-kokoro-pyttsx3.md` | 2026-03-26 |

## Owlbear-Voice Package Scaffolding Research (Task #52)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| uv workspace docs | <https://docs.astral.sh/uv/concepts/projects/workspaces/> | MIT | Workspace member config, requires-python intersection rules, member pyproject.toml patterns | `docs/research/bearclaw-voice-workspace-package.md` | 2026-03-26 |
| moonshine-voice 0.0.51 PyPI | <https://pypi.org/project/moonshine-voice/> | MIT | Runtime deps (numpy, sounddevice, requests, tqdm, filelock, platformdirs), requires-python >=3.8, platform wheels | `docs/research/bearclaw-voice-workspace-package.md` | 2026-03-26 |
| kokoro 0.9.4 PyPI | <https://pypi.org/project/kokoro/> | Apache-2.0 | Runtime deps (huggingface-hub, loguru, misaki[en], numpy, torch, transformers), requires-python <3.13,>=3.10 | `docs/research/bearclaw-voice-workspace-package.md` | 2026-03-26 |
| pydantic-ai monorepo | <https://github.com/pydantic/pydantic-ai> | MIT | Workspace extras pattern, optional-dependencies in member packages | `docs/research/bearclaw-voice-workspace-package.md` | 2026-03-26 |

## OwlbearProjectFile Test Research (Task #74)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic v2 AwareDatetime docs | <https://docs.pydantic.dev/latest/api/standard_library_types/#datetime-types> | MIT | AwareDatetime "requires the input to have a timezone" — validates test scenario for naive datetime rejection | `docs/research/owlbear-project-file-tests.md` | 2026-03-26 |
| Pydantic v2 Literal validation | <https://docs.pydantic.dev/latest/api/standard_library_types/#literals> | MIT | Literal uses strict mode; invalid values raise clear error messages — confirms type enum test pattern | `docs/research/owlbear-project-file-tests.md` | 2026-03-26 |

## disable-model-invocation Pipeline Agents Research (Task #38)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | `disable-model-invocation` field definition: prevents subagent invocation (default false) | `docs/research/disable-model-invocation-pipeline-agents.md` | 2026-03-27 |
| VS Code Subagents docs | <https://code.visualstudio.com/docs/copilot/agents/subagents> | CC-BY-4.0 | Override behavior: explicit `agents` array overrides `disable-model-invocation: true` | `docs/research/disable-model-invocation-pipeline-agents.md` | 2026-03-27 |

## Build Setup Script Research (Task #12) — Supplemental

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| v1 ProjectWorkspace | `v1/src/owlbear/projects/workspace.py` | N/A (internal) | Project scaffolding pattern: template dispatch, directory creation, git init, kanban-md init | `docs/research/setup-script.md` | 2026-03-28 |
| VS Code Copilot customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | CC-BY-4.0 | Parent repository discovery, chat.agentFilesLocations/agentSkillsLocations/instructionsFilesLocations formats | `docs/research/setup-script.md` | 2026-03-28 |
| VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | mcp.json schema: stdio server config (type, command, args, env), camelCase naming conventions | `docs/research/setup-script.md` | 2026-03-28 |
| Copier project scaffolder | <https://github.com/copier-org/copier> | MIT | Template-based project scaffolding with Jinja2, update support, questionnaires (evaluated, not adopted) | `docs/research/setup-script.md` | 2026-03-28 |
| Cookiecutter docs | <https://cookiecutter.readthedocs.io/en/stable/overview.html> | BSD-3 | Template directory structure with JSON config, pre/post hooks (evaluated, not adopted) | `docs/research/setup-script.md` | 2026-03-28 |

## Test Setup Script Core Functions Research (Task #92)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest tmp_path fixture docs | <https://docs.pytest.org/en/stable/how-to/tmp_path.html> | MIT | Filesystem isolation for scaffold tests, sibling directory layout pattern | `docs/research/test-setup-script-core.md` | 2026-03-28 |
| pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | MIT | monkeypatch.chdir for auto-detection tests, monkeypatch.setattr for path resolution | `docs/research/test-setup-script-core.md` | 2026-03-28 |
| v1 test_project_workspace.py | `v1/tests/test_project_workspace.py` | N/A (internal) | Scaffold test pattern: tmp_path fixtures, MagicMock for subprocess, direct filesystem assertions | `docs/research/test-setup-script-core.md` | 2026-03-28 |

## v2 Test Infrastructure Research (Task #35) — Supplemental

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest Good Integration Practices | <https://docs.pytest.org/en/stable/explanation/goodpractices.html> | MIT | testpaths, import-mode=importlib recommendation for src layout | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |
| ruff Configuration docs | <https://docs.astral.sh/ruff/configuration/> | MIT | select=ALL with targeted ignores, src for isort first-party detection, per-file-ignores patterns | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |
| hynek � Testing in a Python Project | <https://hynek.me/articles/testing-packaging/> | CC-BY-4.0 | source_pkgs over source paths for installed-package coverage in monorepos | `docs/research/v2-test-infrastructure.md`, `pyproject.toml` | 2026-03-28 |
| pydantic-ai pyproject.toml | <https://github.com/pydantic/pydantic-ai> | MIT | asyncio_mode=strict convention, per-package test layout in a uv monorepo | `docs/research/v2-test-infrastructure.md` | 2026-03-28 |

## README Trim Assessment (Task #93)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Code README | <https://github.com/anthropics/claude-code> | Unknown | Minimal README structure: title, get-started, plugins, bugs, data policy | `docs/research/readme-trim-assessment.md` | 2026-03-29 |
| Aider README | <https://github.com/Aider-AI/aider> | Apache-2.0 | Feature-focused README, setup details kept external to main README | `docs/research/readme-trim-assessment.md` | 2026-03-29 |

## MCP Server Documentation Research (Task #122)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio/http server config format, `${input:var-id}` secret handling, `"inputs"` array, IntelliSense autocomplete, naming conventions | `README.md` (Adding MCP Servers section), `docs/research/mcp-server-docs.md` | 2026-03-29 |
| VS Code MCP Server Guide | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> | CC-BY-4.0 | HTTP Stream vs SSE transport fallback, server lifecycle management | `docs/research/mcp-server-docs.md` | 2026-03-29 |

## Skills Path Migration Cleanup (Task #117)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Agent Skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | CC-BY-4.0 | Native auto-discovery paths (`.github/skills/`), `chat.agentSkillsLocations` for custom paths, deduplication behavior when both paths active | `docs/research/delete-github-skills-117.md` | 2026-03-29 |
| agentskills.io specification | <https://agentskills.io/specification> | Apache-2.0 | Skill location not mandated by spec; any directory works if properly configured | `docs/research/delete-github-skills-117.md` | 2026-03-29 |

## Memory Boundary Instructions Research (Task #11)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Custom Instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | .instructions.md format, applyTo glob patterns, instruction priority model, file locations | `docs/research/memory-boundary-instructions.md` | 2026-03-29 |
| VS Code Settings Reference — Memory | <https://code.visualstudio.com/docs/copilot/reference/copilot-settings> | CC-BY-4.0 | Built-in memory tool setting, GitHub-hosted memory setting, memory settings section | `docs/research/memory-boundary-instructions.md` | 2026-03-29 |
| GitHub Copilot Memory docs | <https://docs.github.com/en/copilot/concepts/agents/copilot-memory> | CC-BY-4.0 | Repo-scoped memory, citation validation, 28-day auto-expiry, enabling model | `docs/research/memory-boundary-instructions.md` | 2026-03-29 |

## MCP Server Customization Docs (Task #128)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | CC-BY-4.0 | stdio vs http server types, env vars, input variables (`${input:}`), IntelliSense in mcp.json | `README.md` — Adding MCP Servers section | 2026-03-29 |
| VS Code MCP Server Guide | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> | CC-BY-4.0 | Remote server config format, http type semantics, user-facing setup guidance | `docs/research/mcp-server-customization-docs.md` | 2026-03-29 |

## Memory Boundary Instructions Research Validation (Task #137)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| awesome-copilot memory-bank.instructions.md | <https://github.com/github/awesome-copilot/blob/main/instructions/memory-bank.instructions.md> | MIT | Community pattern using .instructions.md for memory management; different scope (full project memory bank) but validates the file-based approach | Task #137 research validation | 2026-03-29 |

## Pre-commit Agent Tool Guard (Tasks #132, #134)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pre-commit docs — local hooks | <https://pre-commit.com/#repository-local-hooks> | MIT | `repo: local` hook config, `language: system` (now `unsupported`), `pass_filenames`, `files` filter | `docs/research/pre-commit-agent-tool-guard.md`, `.pre-commit-config.yaml` | 2026-03-29 |

## Planner Data Models & Board Reader Research (Task #144)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | `model_validate_json()`, `TypeAdapter`, frozen models, `Field(alias=...)` | `docs/research/planner-data-models-board-reader.md` | 2026-03-29 |
| Python 3.12 asyncio-subprocess docs | <https://docs.python.org/3.12/library/asyncio-subprocess.html> | PSF-2.0 | `create_subprocess_exec` with PIPE, `communicate()` pattern | `docs/research/planner-data-models-board-reader.md` | 2026-03-29 |
| Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | MIT | Frozen models with `ConfigDict(frozen=True, populate_by_name=True)`, `TypeAdapter(list[Task])`, `Field(alias=...)` for keyword conflict | `packages/orchestrator/src/owlbear/planner/models.py` | 2026-03-30 |
| Python 3.12 asyncio-subprocess docs | <https://docs.python.org/3.12/library/asyncio-subprocess.html> | PSF-2.0 | `create_subprocess_exec` with PIPE, `communicate()` — board reader subprocess pattern | `packages/orchestrator/src/owlbear/planner/board.py` | 2026-03-30 |

## .github/ v1 Cleanup Research (Task #29)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code prompt file docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | `.github/prompts/` as canonical workspace prompt location; relative path resolution for file references | `docs/research/github-v1-cleanup.md` | 2026-03-29 |

## Intake + Ingest Pipeline Modules Research (Task #158)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex IngestionPipeline | <https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/> | MIT | Docstore delta detection, async pipeline, composable transformations, vector store integration | `docs/research/intake-ingest-pipeline-modules.md` | 2026-03-29 |
| nano-graphrag _op.py | <https://github.com/gusye1234/nano-graphrag/blob/main/nano_graphrag/_op.py> | MIT | asyncio.gather for parallel chunk extraction, injectable LLM callables, content hashing | `docs/research/intake-ingest-pipeline-modules.md` | 2026-03-29 |

## ErrorJournal-AcpClient Wiring Research (Task #148)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Tenacity `after` callback pattern | <https://tenacity.readthedocs.io/en/latest/api.html> | Apache-2.0 | after/before callback hooks for error logging in retry wrappers | `docs/research/errorjournal-acpclient-wiring.md` | 2026-03-29 |
| Python logging.Logger.exception | <https://docs.python.org/3/library/logging.html> | PSF | Standard logging exception handler pattern as alternative to structured journal | `docs/research/errorjournal-acpclient-wiring.md` | 2026-03-29 |
| PydanticAI exceptions hierarchy | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/exceptions.py> | MIT | Classified exception hierarchy with typed error categories | `docs/research/errorjournal-acpclient-wiring.md` | 2026-03-29 |

## Auditor Confidence Deduction Rubric (Task #197)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Popham 1997 — What's Wrong and What's Right with Rubrics | <https://eric.ed.gov/?id=EJ552014> | N/A | Analytic rubric structure: separate dimension evaluation, deduction-from-max pattern | `docs/research/auditor-confidence-deduction-rubric.md` | 2026-03-30 |
| Wikipedia — Inter-rater reliability (Cohen 1960, Fleiss 1971) | <https://en.wikipedia.org/wiki/Inter-rater_reliability> | CC-BY-SA-3.0 | Rater drift without explicit guidelines, scoring consistency requires rubrics | `docs/research/auditor-confidence-deduction-rubric.md` | 2026-03-30 |
| Du et al. 2023 — Multi-agent Debate | <https://arxiv.org/abs/2305.14325> | CC-BY-4.0 | Anchoring in sequential pipelines: agents inherit upstream assumptions | `docs/research/auditor-confidence-deduction-rubric.md` | 2026-03-30 |
| Wang et al. 2024 — Rethinking Bounds of LLM Reasoning | <https://arxiv.org/abs/2402.18272> | N/A | Better prompts outperform more agents; structured scoring > more review stages | `docs/research/auditor-confidence-deduction-rubric.md` | 2026-03-30 |

## Integration Test: Ingest-to-Search Cycle (Task #162)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MS GraphRAG test layout | <https://github.com/microsoft/graphrag/tree/main/tests> | MIT | unit/integration/smoke test separation pattern for RAG pipelines | `docs/research/integration-test-ingest-to-search-cycle.md` | 2026-03-30 |
| LightRAG test layout | <https://github.com/HKUDS/LightRAG/tree/main/tests> | MIT | conftest markers for offline/integration tests, Qdrant integration tests | `docs/research/integration-test-ingest-to-search-cycle.md` | 2026-03-30 |

## Stop Commit Guard Hooks Phase 1 (Task #209)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | Command-execution hook model, Stop hook contract (stop_hook_active, decision: block), exit codes, JSON I/O | `docs/research/stop-commit-guard-hooks-phase1.md` | 2026-03-30 |
| VS Code Custom Agents docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Agent-scoped hooks frontmatter format, chat.useCustomAgentHooks setting requirement | `docs/research/stop-commit-guard-hooks-phase1.md` | 2026-03-30 |

## Update #86 Research Doc — Command-Execution Hook Model (Task #212)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | 8 hook event types (PascalCase), type: command format, exit code 2 blocking, PreToolUse permissionDecision, Stop decision: block, JSON I/O contract | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` (revision) | 2026-03-30 |
| VS Code Custom Agents docs (3/25/2026) | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Agent-scoped hooks frontmatter example with type: command | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` (revision) | 2026-03-30 |

## PostToolUse Lint Guard Feasibility (Task #210)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | PostToolUse I/O schema, hookSpecificOutput.additionalContext, exit code 2 model-facing semantics, agent-scoped hook subagent behavior | `docs/research/posttooluse-lint-guard-feasibility.md` | 2026-04-01 |

## Non-Impl Tag Cross-References (Task #218)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kubernetes contributor guide | <https://github.com/kubernetes/community/blob/master/contributors/guide/README.md> | Apache-2.0 | "Single source of truth" declaration pattern in multi-file documentation | `docs/research/non-impl-tag-cross-references.md` | 2026-03-30 |
| GitLab CTRT documentation topic types | <https://docs.gitlab.com/development/documentation/topic_types/> | CC-BY-SA-4.0 | Cross-reference "Related topics" sections as standard docs practice | `docs/research/non-impl-tag-cross-references.md` | 2026-03-30 |

## Slack Notification Integration v2 (Task #26)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Incoming Webhooks docs | <https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks> | N/A | Webhook URL POST pattern, error codes, message formatting for send-only notifications | `docs/research/slack-notification-v2.md` | 2026-03-30 |
| slack_sdk v3.41.0 (PyPI) | <https://pypi.org/project/slack-sdk/> | MIT | WebhookClient, AsyncWebhookClient, AsyncWebClient; aiohttp requirement for async | `docs/research/slack-notification-v2.md` | 2026-03-30 |
| Slack chat.postMessage docs | <https://docs.slack.dev/messaging/sending-and-scheduling-messages> | N/A | Bot token approach: `xoxb-` token + channel ID, `chat:write` scope, mrkdwn formatting | `docs/research/slack-notification-v2.md` | 2026-03-30 |

## Mandatory User-Decision Gate (Task #385)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Anthropic "Building Effective Agents" | <https://www.anthropic.com/engineering/building-effective-agents> | N/A | Agent checkpoint patterns, human feedback gates, programmatic checks on intermediate steps | `docs/research/mandatory-user-decision-gate.md` | 2026-03-30 |
| AutoGen Human-in-the-Loop docs | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html> | MIT | UserProxyAgent blocking approval, HandoffTermination typed control transfer | `docs/research/mandatory-user-decision-gate.md` | 2026-03-30 |
| CrewAI Tasks docs | <https://docs.crewai.com/concepts/tasks> | N/A | `human_input` mandatory review flag, `guardrail` validation functions on task outputs | `docs/research/mandatory-user-decision-gate.md` | 2026-03-30 |
| GitHub Actions Environment Protection | <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment> | N/A | Required-reviewer gate per environment, structured file-based approval state | `docs/research/mandatory-user-decision-gate.md` | 2026-03-30 |

## CLI Entrypoint for Analysis Pipeline (Task #180)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs — `__main__` module | <https://docs.python.org/3/library/__main__.html> | PSF | Idiomatic `__main__.py` pattern: minimal file importing `main()`, `sys.exit(main())` convention | `docs/research/cli-entrypoint-analysis-pipeline.md` | 2026-03-31 |
| Typer docs — Building a Package | <https://typer.tiangolo.com/tutorial/package/> | MIT | `__main__.py` pattern for Typer apps, `app()` invocation, `[project.scripts]` wiring | `docs/research/cli-entrypoint-analysis-pipeline.md` | 2026-03-31 |

## PreToolUse Read-Only Guard Feasibility (Task #211)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| VS Code Hooks docs (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/hooks> | CC-BY-4.0 | PreToolUse I/O schema, permissionDecision deny/allow/ask, hookSpecificOutput format, priority rules | `docs/research/pretooluse-read-only-guard-feasibility.md` | 2026-04-01 |
| VS Code Custom Agents docs (4/1/2026) | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | CC-BY-4.0 | Agent-scoped hooks `hooks:` YAML key, subagent behavior note | `docs/research/pretooluse-read-only-guard-feasibility.md` | 2026-04-01 |

## Migrate Dispatcher to pick_tasks MCP Tool (Task #619)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Spec — Tools (2025-06-18) | <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | MIT | readOnlyHint, outputSchema, ToolAnnotations for computed tools, error handling conventions | `.owlbear/research/migrate-dispatcher-to-pick-tasks.md` | 2026-04-05 |

## Implement Voice Process Manager (Task #62)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MCP Python SDK stdio client | <https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/stdio.py> | MIT | Background asyncio.Task read loop + asyncio.Queue message buffer pattern (MemoryObjectReceiveStream equivalent); subprocess spawn and NDJSON read/write architecture | `.owlbear/research/voice-process-manager.md` | 2026-03-27 |
| ACP Python SDK `spawn_stdio_transport` | `v1/.venv/Lib/site-packages/acp/transports.py` | Apache-2.0 | asyncio subprocess lifecycle, graceful terminate+kill shutdown pattern | `.owlbear/research/voice-process-manager.md` | 2026-03-27 |

## SharePoint Normalization + Idempotent Output (Task #829)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| sp-dev-docs#6380 — CSS class instability | <https://github.com/SharePoint/sp-dev-docs/issues/6380> | SharePoint replacing semantic CSS classes (`CanvasZone`, `ControlZone`) with hashed names; confirms `ms-` prefix classes from Fluent UI more stable | .owlbear/research/829-sharepoint-normalization-cleaner.md | 2026-04-12 |
| Fluent UI v8 CSS class catalog | <https://github.com/Zerg00s/sp-modern-classes> | Community-maintained list of reusable SharePoint Online CSS classes — `ms-Breadcrumb`, `ms-Persona`, `ms-DateTimeField` patterns identified | .owlbear/research/829-sharepoint-normalization-cleaner.md | 2026-04-12 |
| trafilatura core functions docs | <https://trafilatura.readthedocs.io/en/latest/corefunctions.html> | `prune_xpath` parameter — supports custom XPath for pre-extraction element removal (evaluated as alternative approach, not adopted) | .owlbear/research/829-sharepoint-normalization-cleaner.md | 2026-04-12 |

## Azure AD App Registration Request (Task #878)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Graph API `sitePage.Get` permissions | <https://learn.microsoft.com/en-us/graph/api/sitepage-get> | Confirmed `Sites.Read.All` (delegated) as least privileged permission for sitePage read; verified `$expand=canvasLayout` query parameter | .owlbear/research/878-azure-ad-app-registration-request.md | 2026-04-14 |
| Entra ID app registration quickstart | <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app> | App registration steps, supported account types, admin consent process | .owlbear/research/878-azure-ad-app-registration-request.md | 2026-04-14 |
| OAuth 2.0 device authorization grant | <https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code> | Device-code flow protocol: `/devicecode` endpoint, polling, token response format, Conditional Access considerations | .owlbear/research/878-azure-ad-app-registration-request.md | 2026-04-14 |

## PreToolUse Guard Hooks Test Approach (Task #891) — Supplement

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| VS Code Hooks docs — PreToolUse I/O | <https://code.visualstudio.com/docs/copilot/customization/hooks> | PreToolUse stdin/stdout JSON contract, permissionDecision output format, exit codes, editFiles tool_input schema | .owlbear/research/891-pretooluse-hooks-test-approach.md | 2026-04-17 |
| VS Code Hooks docs — PostToolUse I/O | <https://code.visualstudio.com/docs/copilot/customization/hooks> | PostToolUse stdin/stdout JSON contract, additionalContext output, decision: block, exit codes, tool_input formats | .owlbear/research/892-lint-changed-hook-test-approach.md | 2026-04-17 |
| VS Code Hooks docs — SessionStart I/O | <https://code.visualstudio.com/docs/copilot/customization/hooks> | SessionStart I/O contract: stdin `{source: "new"}`, stdout `{hookSpecificOutput: {hookEventName, additionalContext}}`, fail-open exit 0 semantics | .owlbear/research/session-context-py-test-strategy.md | 2026-04-17 |

## App Shell Test Strategy (Task #927)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Router v7 API reference | <https://api.reactrouter.com/v7/modules/react-router.html> | MemoryRouter, Routes, Route, Outlet — unified `react-router` package in v7 | .owlbear/research/927-app-shell-tests.md | 2026-04-18 |
| React Router v7 library install + routing docs | <https://reactrouter.com/start/library/installation> | Declarative routing: BrowserRouter, nested Routes, layout routes, Outlet pattern | .owlbear/research/927-app-shell-tests.md | 2026-04-18 |
| PDS v3.34 Tabs examples | <https://designsystem.porsche.com/v3/components/tabs/examples/> | PTabs + PTabsItem API: `label` prop, `activeTabIndex`, tab content pattern | .owlbear/research/927-app-shell-tests.md | 2026-04-18 |

## Playwright E2E Infrastructure (Task #956)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Playwright webServer docs | <https://playwright.dev/docs/test-webserver> | webServer config: command, url, reuseExistingServer, timeout, auto-start dev server | .owlbear/research/956-playwright-e2e-infrastructure.md | 2026-04-18 |
| Playwright config reference | <https://playwright.dev/docs/test-configuration> | testDir, projects, reporters, fullyParallel, forbidOnly, workers | .owlbear/research/956-playwright-e2e-infrastructure.md | 2026-04-18 |
| Vite preview options | <https://vite.dev/config/preview-options.html> | Default port 4173, strictPort, host options for vite preview | .owlbear/research/956-playwright-e2e-infrastructure.md | 2026-04-18 |

> **TODO:** stale — duplicate section heading for Task #969 (MD024); merge with first occurrence above [#1495]

## React Compiler Evaluation (Task #969)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| React Compiler introduction | <https://react.dev/learn/react-compiler/introduction> | Stability status, what it does, useMemo/useCallback/React.memo guidance | .owlbear/research/969-react-compiler-evaluation.md | 2026-04-18 |
| React Compiler installation | <https://react.dev/learn/react-compiler/installation> | Vite integration guide, ESLint plugin, verification steps | .owlbear/research/969-react-compiler-evaluation.md | 2026-04-18 |
| babel-plugin-react-compiler npm | <https://www.npmjs.com/package/babel-plugin-react-compiler> | v1.0.0 stable, 7.6M weekly downloads, MIT license | .owlbear/research/969-react-compiler-evaluation.md | 2026-04-18 |
| react-compiler-runtime npm | <https://www.npmjs.com/package/react-compiler-runtime> | v1.0.0, 0 dependencies, React 19 compat shim | .owlbear/research/969-react-compiler-evaluation.md | 2026-04-18 |

## Arch Review Design-Diverge (Task #1149)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Ousterhout — Philosophy of Software Design (Pragmatic Engineer) | <https://newsletter.pragmaticengineer.com/p/the-philosophy-of-software-design> | "Design It Twice" concept — generate multiple radically different designs, compare | .owlbear/research/1149-arch-review-design-diverge.md | 2026-04-27 |
| mattpocock/design-an-interface (SkillsMP) | <https://skillsmp.com/skills/mattpocock-skills-design-an-interface-skill-md> | VS Code skill: 3+ parallel sub-agents with constraint-driven design prompts, 17.6K stars | .owlbear/research/1149-arch-review-design-diverge.md | 2026-04-27 |

## Init.py Consumer Scaffold (Task #1284)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GitHub Blog — 5 Tips for Custom Instructions | <https://github.blog/ai-and-ml/github-copilot/5-tips-for-writing-better-custom-instructions-for-copilot/> | Recommended sections: project overview, tech stack, guidelines, project structure, resources | .owlbear/research/init-scaffold-copilot-instructions.md | 2026-05-03 |
| VS Code Docs — Custom Instructions | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | File format, auto-detection, priority rules, `copilot-instructions.md` usage patterns | .owlbear/research/init-scaffold-copilot-instructions.md | 2026-05-03 |
| Graham Knapp — My Copilot Instructions File | <https://grahamknapp.com/blog/my-copilot-instructions-file/> | Real-world copilot-instructions.md as "project map, not rulebook"; contextual, project-specific | .owlbear/research/init-scaffold-copilot-instructions.md | 2026-05-03 |

## Reviewer Rewrite Research (Task #1407)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Google Eng Practices — Review Standard | <https://google.github.io/eng-practices/review/reviewer/standard.html> | "Nit:" prefix for non-blocking; approve when code health improves; batch feedback | .owlbear/research/1407-reviewer-rewrite.md | 2026-05-08 |
| Conventional Comments | <https://conventionalcomments.org/> | Formal label taxonomy: issue vs suggestion vs nitpick; blocking vs non-blocking | .owlbear/research/1407-reviewer-rewrite.md | 2026-05-08 |

## Sync-to-Main TODO Warning Research (Task #1426)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| GitHub Actions Workflow Commands | <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands> | `::warning title=TITLE::message` annotation syntax | .owlbear/research/sync-todo-marker-warning.md | 2026-05-09 |

## Modal PInlineNotification Research (Task #1499)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS Inline Notification API (v3) | <https://designsystem.porsche.com/v3/components/inline-notification/api/> | Full prop/event/slot reference for PInlineNotification | .owlbear/research/cockpit-inline-notification-modal.md | 2026-05-12 |
| PDS Inline Notification Examples (v3) | <https://designsystem.porsche.com/v3/components/inline-notification/examples/> | Event handling and action button patterns | .owlbear/research/cockpit-inline-notification-modal.md | 2026-05-12 |

## Column CSS Implementation Research (Task #1547)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| SO: Scrolling a flexbox with overflowing content | <https://stackoverflow.com/questions/21515042> | Fixed-header scrollable-body pattern: flex-direction column + min-height 0 + overflow-y auto | .owlbear/research/1547-column-css-impl.md | 2026-05-14 |
| PDS v4 SCSS Introduction | <https://designsystem.porsche.com/v4/scss/introduction/> | PDS design token naming conventions and usage patterns | .owlbear/research/1547-column-css-impl.md | 2026-05-14 |

## Sidecar Collapse Toggle Implementation Research (Task #1549)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| CSS-Tricks: Animating CSS Grid | <https://css-tricks.com/animating-css-grid-how-to-examples/> | Grid column animation technique, `0fr` collapse pattern, `:has()` parent selector | .owlbear/research/1549-sidecar-collapse-toggle-impl.md | 2026-05-14 |
| CanIUse: grid-template-columns animation | <https://caniuse.com/mdn-css_properties_grid-template-columns_animation> | Browser support: 93%+ global, all major browsers since Chrome 107, Firefox 66, Safari 16 | .owlbear/research/1549-sidecar-collapse-toggle-impl.md | 2026-05-14 |
| CodePen: CSS Grid sidebar expand | <https://codepen.io/mrdanielschwarz/pen/BaPjKrP> | Working demo of `transition: 300ms` on `grid-template-columns` for sidebar | .owlbear/research/1549-sidecar-collapse-toggle-impl.md | 2026-05-14 |
| Codidact: CSS grid with expanding cells | <https://software.codidact.com/posts/287970> | Animated grid cells via dynamic `grid-template-columns`/`rows` with transition | .owlbear/research/1549-sidecar-collapse-toggle-impl.md | 2026-05-14 |

## PDS Color-Scheme Bridge Research (Task #1555)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Theme docs | <https://designsystem.porsche.com/v4/must-know/theme/> | color-scheme classes on `<html>`, hierarchical scoping | `.owlbear/research/1555-pds-color-scheme-bridge.md` | 2026-05-14 |
| PDS v4 Color Scheme Stylesheet docs | <https://designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/> | Import path, lightningcss exclusion requirement, polyfill setup | `.owlbear/research/1555-pds-color-scheme-bridge.md` | 2026-05-14 |
| PDS GitHub Issue #4257 | <https://github.com/porsche-design-system/porsche-design-system/issues/4257> | lightningcss broken `light-dark()` polyfill in Vite 8 | `.owlbear/research/1555-pds-color-scheme-bridge.md` | 2026-05-14 |

## Modal → PModal Migration Research (Task #1618)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Modal source (GitHub) | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/components/modal/modal.tsx> | PModal props, slots, events, native dialog usage | `.owlbear/research/1618-modal-pmodal-migration.md` | 2026-05-16 |
| PDS v4 Modal examples page | <https://designsystem.porsche.com/v4/components/modal/examples/> | Alert dialog pattern with `disableBackdropClick` + `role: alertdialog` | `.owlbear/research/1618-modal-pmodal-migration.md` | 2026-05-16 |
| MDN `<dialog>` element reference | <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog> | Native focus trap, Escape dismiss, focus return on `close()`, top-layer rendering | `.owlbear/research/1618-modal-pmodal-migration.md` | 2026-05-16 |
| Stefan Judis — dialog element super powers | <https://www.stefanjudis.com/blog/a-look-at-the-dialog-elements-super-powers/> | Focus return confirmation: "focus will be moved back to the previously focused element" | `.owlbear/research/1618-modal-pmodal-migration.md` | 2026-05-16 |
| Sam Hermes — giving the dialog element a whirl | <https://samhermes.com/posts/giving-the-dialog-element-a-whirl/> | Focus return confirmation: "focus will be returned to the element used to open the dialog" | `.owlbear/research/1618-modal-pmodal-migration.md` | 2026-05-16 |

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 Tailwind Introduction | <https://designsystem.porsche.com/v4/tailwindcss/introduction/> | Tailwind v4 setup, PDS theme import, color-scheme utilities | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| PDS v4 Tailwind Color Examples | <https://designsystem.porsche.com/v4/tailwindcss/color/examples/> | PDS color utility classes (bg-canvas, text-contrast-high, etc.) | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| PDS v4 Tailwind Spacing Examples | <https://designsystem.porsche.com/v4/tailwindcss/spacing/examples/> | PDS spacing utilities (gap-fluid-md, gap-static-md), NOT gap-md | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| PDS v4 Migration Guide (Tailwind) | <https://designsystem.porsche.com/v4/news/migration-guide/tailwindcss/> | Breaking changes: scheme-* classes, --color-* reset | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| PDS tailwindcss theme source | <https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/styles/projects/tailwindcss/src/index.ts> | @theme variable definitions, @utility rules, light-dark() usage | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| Tailwind CSS v4 Vite Install | <https://tailwindcss.com/docs> | @tailwindcss/vite plugin setup, @import "tailwindcss" | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| stylelint-config-tailwindcss | <https://github.com/zhilidali/stylelint-config-tailwindcss> | Stylelint config extending at-rule-no-unknown for Tailwind | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |
| @tailwindcss/vite Vite 8 discussion | <https://github.com/tailwindlabs/tailwindcss/discussions/19624> | Vite 8 support timeline for @tailwindcss/vite | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 2026-05-16 |

## Component Complexity Inventory (Task #1608)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v4 React wrapper exports | (local: node_modules/@porsche-design-system/components-react/) | Available React wrappers: PTabs, PTabsItem, PSheet, PAccordion, PIcon, PRadioGroup, PRadioGroupOption, PLinkPure; absent: PList/PListItem | `.owlbear/research/1608-component-complexity-inventory.md` | 2026-05-17 |
| PDS v4 component overview | <https://designsystem.porsche.com/v4/components/overview/> | Component availability and API surface for migration classification | `.owlbear/research/1608-component-complexity-inventory.md` | 2026-05-17 |

## CleanupPanel/RepairPanel PModal Migration (Task #1635)

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| PDS v3 Modal configurator docs | <https://designsystem.porsche.com/v3/components/modal/configurator/> | PModal component behavior: native dialog, focus trap, top-layer, dismiss event, controlled open prop | `.owlbear/research/1635-cleanup-repair-pmodal-migration.md` | 2026-05-17 |
| PDS v3 Modal accessibility docs | <https://designsystem.porsche.com/v3/components/modal/accessibility/> | ARIA support: aria-label, role (dialog/alertdialog), keyboard behavior (Tab trap, Escape), focus return | `.owlbear/research/1635-cleanup-repair-pmodal-migration.md` | 2026-05-17 |
| RFC 9110 §8.8.2 Last-Modified | <https://httpwg.org/specs/rfc9110.html#field.last-modified> | Prior art for two-field timestamp model (Last-Modified vs Date semantics) | `.owlbear/research/refresh-honesty-two-field-timestamps.md` | 2026-05-18 |
