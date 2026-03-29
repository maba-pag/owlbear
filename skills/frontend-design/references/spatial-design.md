# Spatial Design Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Spatial design governs the use of space, density, and layout. Good spacing
creates visual groupings, guides the eye, and establishes hierarchy without
relying on borders or color alone.

---

## Spacing System

Use a **4pt base grid**. All margin, padding, gap, and size values should be
multiples of 4px (0.25rem). Common tokens:

```css
:root {
  --space-1:  0.25rem;   /* 4px  */
  --space-2:  0.5rem;    /* 8px  */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */
  --space-12: 3rem;      /* 48px */
  --space-16: 4rem;      /* 64px */
  --space-24: 6rem;      /* 96px */
}
```

Use the scale consistently; avoid one-off pixel values.

---

## Layout Grid

For page-level layout, define a grid early:

```css
.layout {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-6);
  max-width: 1280px;
  margin-inline: auto;
  padding-inline: var(--space-6);
}
```

Common column patterns:
- Content-heavy: 8 + 4 (main + sidebar)
- Article: 6–8 columns centred
- Dashboard: 12-column fluid

---

## Container Queries

Prefer container queries over viewport breakpoints for component-level
responsiveness:

```css
.card-container {
  container-type: inline-size;
}

@container (min-width: 480px) {
  .card {
    display: grid;
    grid-template-columns: 1fr 2fr;
  }
}
```

Container queries allow the same component to adapt to sidebar contexts, modal
contexts, and full-width contexts independently.

---

## Visual Hierarchy Through Spacing

The **Gestalt law of proximity** applies directly: elements closer together
appear related. Use spacing differentials to communicate grouping:

- **Tight** (4–8px): label+input, icon+text, status chip+text
- **Standard** (12–16px): list items, table rows
- **Loose** (24–32px): card padding, section separators
- **Section** (48–96px): page-level section separation

---

## Touch Targets

Minimum interactive target size: **44×44 px** (iOS HIG and WCAG 2.5.5). Apply
to all tappable/clickable elements, even if the visible element is smaller:

```css
.icon-button {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

---

## Z-Index Scale

Define a structured z-index scale to prevent stacking-context fights:

```css
:root {
  --z-below:   -1;
  --z-base:     0;
  --z-raised:  10;
  --z-overlay: 100;
  --z-modal:   200;
  --z-toast:   300;
  --z-tooltip: 400;
}
```

---

## Density Variants

Match density to context. Compact for data tables; comfortable for text-heavy
pages; cozy for mobile:

```css
[data-density="compact"]   { --space-base: 0.75rem; }
[data-density="default"]   { --space-base: 1rem; }
[data-density="comfortable"] { --space-base: 1.25rem; }
```

---

## Taste Heuristics (not hard rules)

- Full-width cards on all viewports: wastes horizontal space on large displays;
  consider max-width constraints.
- Centered-everything layouts: work for marketing, not for apps.
- Uniform padding everywhere: vary density by content type and context.
